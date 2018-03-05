#!/bin/env python
import argparse
import MySQLdb
import ConfigParser
import traceback
import sys
import os

def mycnf(f=os.environ['HOME'] + '/.my.cnf'):
    config = ConfigParser.ConfigParser()
    try:
        config.read(f)
        user = config.get('client','user')
        password = config.get('client','password')
    except:
        print '!! Unable to read mysql credentials from %s' % f
        sys.exit(1)
    try:
        host = config.get('client', 'host')
    except:
        host = 'localhost'
        
    return {'host':host, 'user':user, 'password':password}

def myquery(query, database):
    cred = mycnf()
    db = MySQLdb.connect(host=cred['host'], user=cred['user'], passwd=cred['password'], db=database)
    c = db.cursor()
    c.execute(query)
    results = c.fetchall()

    return results

def get_instances():
    i = myquery("SELECT uuid,hostname,image_ref FROM instances WHERE deleted=0", 'nova')
    instances = {}
    for z in i:
        uuid, hostname, image_ref = z
        instances[uuid] = {'hostname':hostname, 'image_ref': image_ref}

    return instances

def get_images():
    i = myquery("SELECT id,name, deleted FROM images", 'glance')
    images = {}
    for z in i:
        id, name, deleted = z
        deleted = int(deleted)
        images[id] = {'name':name, 'deleted':deleted}

    return images

def get_images_ondisk(path='/var/lib/glance/images'):
    file_list = []
    for dirpath, dirnames, files in os.walk(path):
        for name in files:
            file_list.append(name)

    file_list.sort()
    return (path, file_list)

instances = get_instances()
images = get_images()
images_ondisk = get_images_ondisk()

missing_images = []
unused_images = []
zombie_images = []

parser = argparse.ArgumentParser()
parser.add_argument('--all', help='Show all types of images', action="store_true")
parser.add_argument('--missing', help='Check for missing backing images', action="store_true")
parser.add_argument('--unused', help='Check unused images', action="store_true")
parser.add_argument('--zombie', help='Check images marked as deleted but on disk', action="store_true")
parser.add_argument('--ignore', help='Used with --zombie to ignore images still in use', action="store_true")
parser.add_argument('--verbose', help='Print detailed list of images', action="store_true")
parser.add_argument('--technical', help='Print only uuids', action="store_true")
args = parser.parse_args()

'''
Check for missing backing images
'''

for i in instances:
    try:
        if not images[ instances[i]['image_ref'] ]['deleted'] == 0:
            if args.verbose and args.missing or args.all:
                print "%s:%s does not have a backing image - %s" % (instances[i]['hostname'], i, instances[i]['image_ref'])
            missing_images.append(i)
    except:
        traceback.print_exc()

'''
Check for images marked as deleted in DB, but still on disk
'''

if args.zombie or args.all:
    for uuid in images_ondisk[1]:
        q = "SELECT name, status FROM images WHERE id='%s'" % uuid
        result = myquery(q, "glance")
        name, status = result[0]
        if status == 'deleted':
            if args.verbose:
                print "%s:%s is marked as deleted, but found on disk" % (name, uuid)
            if not args.ignore:
                q = "SELECT uuid from nova.instances as n join glance.images as g on \
                     g.id = n.image_ref where g.deleted='1' and n.deleted='0' and g.id='%s'" % uuid
                result = myquery(q, "nova")
                if not result:
                    zombie_images.append(uuid)
            else:
                    zombie_images.append(uuid)

'''
List of unused images
'''
if args.unused or args.all:
    for image in images:
        inuse = False
        try:
            for i in instances:
                if image == instances[i]['image_ref']:
                    inuse = True
        except:
            continue
     
        if not inuse and images[image]['deleted'] == 0:
            if args.verbose:
                print '%s:%s is NOT in use by instances' % (images[image]['name'], image)
            unused_images.append(image)

'''
Summary
'''
if args.verbose:
    print 'Summary:\n\t%i images\n\t%i instances\n\t%i instances missing backing image\
           \n\t%i unused images\n\t%i marked as deleted but on disk' \
           % (len(images), len(instances), len(missing_images), len(unused_images), len(zombie_images))
if args.technical:
    if args.missing:
        print '#missing'
        for i in missing_images:
            print i
    if args.unused:
        print '#unused'
        for i in unused_images:
            print i
    if args.zombie:
        print '#zombie'
        for i in zombie_images:
            print i
