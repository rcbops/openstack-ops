#!/usr/bin/env python2

'''
============================================================================================
Script used to fix the issue of having running instances whose glance image was deleted.
WARNING: Makes updates to the glance.images table! Consider taking backups prior to running.

Usage:
    cat uuids.txt | fix-backing-image.py -
    -OR-
    fix-backing-image.py <uuid>

Script should be run where it can hit the database, and SSH to the computes. 
If run from an utility container check /etc/hosts to ensure its populated.
'''
from __future__ import print_function
import os
import sys
import MySQLdb
import paramiko
from keystoneclient.auth.identity import v3
from keystoneclient.auth.identity.generic import password as v2
from keystoneclient import session
from keystoneclient import client as keystone
from keystoneclient.v3 import client as keystone3
from novaclient import client as nova
import ConfigParser
import logging

#Uncomment for debug logging
#streamformat = "%(levelname)s (%(module)s:%(lineno)d) %(message)s"
#logging.basicConfig(level=logging.DEBUG, format=streamformat)
#logging.getLogger('iso8601').setLevel(logging.DEBUG)

def warning(*objs):
    print("!! ", *objs, file=sys.stderr)

def keystone_auth():
    '''
    Authenticate with Keystone
    NOTE: user_domain_name and project_domain_name are required for auth to
    work properly. Not documented anywhere!
    '''
    try:
      rc = myrc()
      if int(rc['OS_IDENTITY_API_VERSION']) == 3:
        keystone_version = 3
        auth = v3.Password(auth_url=rc['OS_AUTH_URL'],
                           username=rc['OS_USERNAME'],
                           password=rc['OS_PASSWORD'],
                           project_name=rc['OS_TENANT_NAME'],
                           user_domain_name='default',
                           project_domain_name='default')
        s = session.Session(auth=auth)
        return s
    except KeyError:
        keystone_version = 2
        auth = v2.Password(auth_url=rc['OS_AUTH_URL'],
                           username=rc['OS_USERNAME'],
                           password=rc['OS_PASSWORD'],
                           project_name=rc['OS_TENANT_NAME'])
        s = session.Session(auth=auth)
        return s

    except Exception, e:
      warning('keystone_auth()', repr(e) )
      sys.exit()

def nova_connect():
    ''' Establish connection to nova '''
    try:
      rc = myrc()
      s = keystone_auth()
      n = nova.Client('2', session=s, endpoint_type='internal', insecure=True)
    except Exception, e:
      warning('nova_connect()', repr(e) )
      return None

    return n

def myrc():
  '''
  Read credentials/endpoint from env
  Return dict
  '''

  try:
    result = {'OS_USERNAME':os.environ['OS_USERNAME'],
              'OS_PASSWORD':os.environ['OS_PASSWORD'],
              'OS_TENANT_NAME':os.environ['OS_TENANT_NAME'],
              'OS_AUTH_URL':os.environ['OS_AUTH_URL']}
  except:
    warning('Source your openrc file first.')
    sys.exit(1)

  try:
    result['OS_IDENTITY_API_VERSION'] = os.environ['OS_IDENTITY_API_VERSION']
  except:
    if 'v3' in result['OS_AUTH_URL']:
      result['OS_IDENTITY_API_VERSION'] = 3
    else:
      result['OS_IDENTITY_API_VERSION'] = 2

  return result

def mycnf(f=os.environ['HOME'] + '/.my.cnf'):
    config = ConfigParser.ConfigParser()
    try:
        config.read(f)
        user = config.get('client','user')
        password = config.get('client','password')
    except:
        print('!! Unable to read mysql credentials from %s' % f)
        sys.exit(1)
    try:
        host = config.get('client', 'host')
    except:
        host = 'localhost'
        
    return {'host':host, 'user':user, 'password':password}


def myquery(query, database):
    '''
    Read in query, multiple seperated by semicolon
    Return  list of results
    '''
    cred = mycnf()
    db = MySQLdb.connect(host=cred['host'], user=cred['user'], passwd=cred['password'], db=database)
    results = []

    for q in query.split(';'):
        try:
            c = db.cursor()
            c.execute(q)
            r = c.fetchall()
            c.close()

            results.append(r)

        except Exception, e: print( repr(e) )

    db.commit()
    db.close()

    if len(results) == 1:
        return results[0]
    else:
        return results

def ssh(command, host):
    '''
    Execute command on host
    Return output as dict
    '''

    c = paramiko.SSHClient()
    c.set_missing_host_key_policy( paramiko.AutoAddPolicy() )
    c.connect(host)
    stdin, stdout, stderr = c.exec_command(command)

    result = {}
    result["stdin"] = stdin
    result["stdout"] = stdout.read()
    result["stderr"] = stderr.read()

    return result

def fix(uuid):
    
    try:
        n = nova_connect()
    except Exception, e:
        warning( repr(e) )
        return 1

    instance = n.servers.get(uuid)
    compute = str(instance.__getattribute__('OS-EXT-SRV-ATTR:hypervisor_hostname'))

    s = ssh("qemu-img info /var/lib/nova/instances/%s/disk | awk '/^backing/ {print $3}'" % uuid, compute)
    backing = s["stdout"].strip()

    if not backing == '':
        image_uuid = myquery("SELECT image_ref FROM instances WHERE uuid='%s'" % uuid, 'nova')[0][0]
        image_meta = myquery("SELECT name, checksum, deleted FROM images WHERE id='%s'" % image_uuid, 'glance')[0]

        if int(image_meta[2]) > 0:
            print('...modifying DB')

            if myquery("SET FOREIGN_KEY_CHECKS=0; UPDATE images SET id='xxx-%s' WHERE id='%s' LIMIT 1; SET FOREIGN_KEY_CHECKS=1" \
                    % (image_uuid, image_uuid), 'glance'):

                print('...uploading backing file')
                s = ssh("source ~/openrc; glance image-create --progress --disk-format qcow2 --container-format bare --name '%s' \
                        --file %s --visibility public --id %s" % (image_meta[0], backing, image_uuid), compute )
                if s['stderr']:
                    warning( s['stderr'] )
                    warning('Received error during upload. Rolling back DB change!')
                    myquery("SET FOREIGN_KEY_CHECKS=0; UPDATE images SET id='%s' WHERE id='xxx-%s' LIMIT 1; SET FOREIGN_KEY_CHECKS=1" \
                    % (image_uuid, image_uuid[:-4]), 'glance')
                    return 1
                else:
                    print( s['stdout'] )
                    return 0

        else:
            warning("instance image is not marked as deleted!")
            return 0
    else:
        warning("unable to find backing image or instance!")
        return 1

'''
Look for data being piped in via stdin
Otherwise accept single UUID
'''
try:
    if sys.argv[1] == '-':
        results = {}
        data = sys.stdin.readlines()

        for uuid in data:
            r = fix( uuid.strip() )
            results[uuid.strip()] = r
        for l in results:
            print( l, results[l] )
    else:
        uuid = sys.argv[1]
        r = fix(uuid)
        sys.exit(r)

except Exception, e:
    warning( repr(e) )
    print( __doc__ )
