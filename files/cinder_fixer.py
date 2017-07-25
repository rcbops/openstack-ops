#!/usr/bin/python

import os
import re
import sys
import time

from pprint import pprint
from keystoneauth1.identity import v3
from keystoneauth1 import session
from cinderclient.v2 import client as cinder
from novaclient.v2 import client as nova
from novaclient import exceptions as nova_ex

debug = False


def banner(message):
    width = 80
    print width*"*"
    if len(message) < width - 7:
        print 3*"*" + " " + message + (width-len(message)-7)*" " + 3*"*"
    else:
        print 3*"*" + " " + message
    print width*"*"


def log(message):
    width = 80
    print 3*"*" + " " + message


# Source credentials
ENDPOINT_TYPE = os.environ.get('OS_ENDPOINT_TYPE')
AUTH_URL = os.environ.get('OS_AUTH_URL')
USERNAME = os.environ.get('OS_USERNAME')
PASSWORD = os.environ.get('OS_PASSWORD')
PROJECT_NAME = os.environ.get('OS_PROJECT_NAME')
DOMAIN_ID = 'default'

auth = session.Password(auth_url=AUTH_URL,
                        username=USERNAME,
                        password=PASSWORD,
                        project_name=PROJECT_NAME,
                        user_domain_id=DOMAIN_ID,
                        project_domain_id=DOMAIN_ID)

auth_sess = keystone.Session(auth=auth) Past kilo

# Build cinder volume statistics
volumes_error = dict()
try:
    c_session = cinder.Client(session=auth_session,
                              endpoint_type=ENDPOINT_TYPE)
except Exception as e:
    print e

volumes = c_session.volumes.list(detailed=True,
                                 search_opts={'all_tenants': 1,
                                              'status': 'error'},
                                 limit=50000)

for volume in volumes:
    # attachments structure
    # [{u'server_id': u'3df88b7d-d508-4883-84ac-220b80552539',
    # u'attachment_id': u'6d1e363e-0f73-42e6-951e-44ac47dd7c88',
    #   u'attached_at': u'2017-03-25T20:33:29.000000',
    #   u'host_name': None,
    #   u'volume_id': u'de646522-2f5d-4c11-ac46-5662a6eee00a',
    #   u'device': u'/dev/vdb',
    #   u'id': u'de646522-2f5d-4c11-ac46-5662a6eee00a'}]
    if len(volume.attachments) > 0:
        vol_attachments = volume.attachments[0]
        vol_attachment_id = volume.attachments[0]['attachment_id']
        vol_instance_id = volume.attachments[0]['server_id']
        vol_instance_device = volume.attachments[0]['device']

        volumes_error[volume.id] = ({'attachment_id': vol_attachment_id,
                                     'state': volume.status,
                                     'instance_id': vol_instance_id,
                                     'instance_device': vol_instance_device})

# Dedupe instance ids for multi attached volumes per instance
instance_ids = set()
[volumes_error[id]['instance_id'] for id in volumes_error
 if volumes_error[id]['instance_id'] not in instance_ids and
 not instance_ids.add(volumes_error[id]['instance_id'])]

# Freeze internal nova server states
try:
    n_session = nova.Client(session=auth_session, endpoint_type=ENDPOINT_TYPE)
except Exception as e:
    print e

servers = n_session.servers.list(search_opts={'all_tenants': 1,
                                              'limit': 50000})

banner("Found %s volumes in error state attached to %s servers" %
       (len(volumes_error),
        len(instance_ids)))

if len(volumes_error) > 0:
    # Shutdown servers if up
    for server in servers:
        if server.id in instance_ids and server.status == 'ACTIVE':
            log("Stopping active instance %s" % server.id)
            try:
                server.stop()
            except:
                instance_ids.remove(instance_id)
                continue

    log("Waiting 60s for API to settle")
    time.sleep(60)

    # Reset volumes in error
    banner("Resetting volumes in error state")
    for volume in volumes:
        if len(volume.attachments) > 0:
            if volume.attachments[0]['server_id'] in instance_ids:
                log("Reset volume %s to in-use" % volume.id)
                volume.reset_state(state='in-use')

    log("Waiting for API to settle")
    time.sleep(5)

    # Detach volumes
    banner("Detaching bad volumes from instances")
    for volume in volumes:
        if volume.id in volumes_error:
            volume_id = volume.id
            instance_id = volumes_error[volume.id]['instance_id']
            attachment_id = volumes_error[volume.id]['attachment_id']

            if instance_id in instance_ids:
                log("Detach volume %s from %s (attachment:%s)" %
                    (volume_id, instance_id, attachment_id))
                try:
                    n_session.volumes.delete_server_volume(instance_id,
                                                           volume_id)
                except nova_ex.BadRequest as ex:
                    log("Removing %s from further steps due to error" %
                        instance_id)
                    if debug:
                        sys.stderr.write("%s" % ex)

                    instance_ids.remove(instance_id)
                    continue

    if len(instance_ids) > 0:
        log("Waiting for API to settle")
        time.sleep(5)

    # Attach volumes
    banner("Reattaching volumes to instances")
    for volume in volumes:
        if volume.id in volumes_error:
            volume_id = volume.id
            instance_id = volumes_error[volume_id]['instance_id']
            device = volumes_error[volume_id]['instance_device']

            if instance_id in instance_ids:
                log("Attaching volume %s to %s (%s)" % (volume_id,
                                                        instance_id,
                                                        device))
                try:
                    n_session.volumes.create_server_volume(instance_id,
                                                           volume_id,
                                                           device)
                except:
                    log("Removing %s from further steps due to error" %
                        instance_id)
                    instance_ids.remove(instance_id)
                    continue

    # Start all servers who did not error out
    if len(instance_ids) > 0:
        log("Waiting for API to settle")
        time.sleep(5)

        banner("Starting instances")
        for instance in instance_ids:
            log("Starting %s" % instance)
            try:
                n_session.servers.start(instance)
            except:
                continue
