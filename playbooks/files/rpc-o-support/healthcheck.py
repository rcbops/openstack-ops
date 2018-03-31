from __future__ import print_function
import os
import sys
import uuid
from novaclient import client as nova
from neutronclient.v2_0 import client as neutron
from keystoneclient.auth.identity import v3
from keystoneclient.auth.identity.generic import password as v2
from keystoneclient import session
from keystoneclient import client as keystone
from keystoneclient.v3 import client as keystone3
from cinderclient import client as cinder
import ConfigParser
import requests
import json
import logging
import time
import paramiko
import socket
import subprocess
import argparse
from prettytable import PrettyTable
try:
  import MySQLdb
except:
  print("!! Package missing. Install python-mysqldb.")
  sys.exit(1)

class QC:

  def __init__(self):
    """ Construct """
    self.main()

  def warning(self, *objs):
    print("!! ", *objs, file=sys.stderr)

  def log(self, *objs):
    print("** ", *objs, file=sys.stdout)

  def wait(self, delay=5):
    print('..')
    time.sleep(int(delay) * int(self.stall))

  def ssh(self, command, host):
    '''
    Execute command on host
    Return output as dict
    '''
    logger = paramiko.util.logging.getLogger()
    logger.setLevel(self.level)

    if self.private_key:
      k = paramiko.RSAKey.from_private_key_file(self.private_key)

    c = paramiko.SSHClient()
    c.set_missing_host_key_policy( paramiko.AutoAddPolicy() )
    c.connect(host, timeout=10)
    stdin, stdout, stderr = c.exec_command(command)
    result = {}
    result["stdin"] = stdin
    result["stdout"] = stdout.read()
    result["stderr"] = stderr.read()

    c.close()
    return result

  def findhost(self, host):
    '''
    Find and return IP address of a host
    '''
    with open('/etc/hosts', 'r') as f:
      for line in f:
        try:
          ip, h = line.split()[:2]
          if host.lower() in h.lower():
            return ip
        except ValueError:
          continue
    return None

  def droppatch():
    '''
    https://bugs.launchpad.net/python-cinderclient/+bug/1315606
    Drop a patch in tmp/ for patching
    '''

    f = open('/tmp/cinder-services.diff', 'w')
    patch = """--- /usr/local/lib/python2.7/dist-packages/cinderclient/v1/services.py	2016-02-22 00:58:43.135517363 -0600
@@ -22,7 +22,7 @@
 class Service(base.Resource):

     def __repr__(self):
-        return "<Service: %s>" % self.service
+        return "<Service: %s on %s>" % (self.binary, self.host)


 class ServiceManager(base.ManagerWithFind):"""
    f.write(patch)
    f.close()

  def maas_overview(self, account, token):
    ''' Retrieve recent alarms from MaaS '''
    url = 'https://monitoring.api.rackspacecloud.com/v1.0/hybrid:%s/views/overview' % account
    headers = {
        "Content-type": "application/json",
        "X-Auth-Token": token
    }
    req = requests.get(url, headers=headers, verify=False)
    return req.json()

  def maas_getcheck(self, account, token, entityID, checkID):
    ''' Retrieve check from MaaS '''
    url = 'https://monitoring.api.rackspacecloud.com/v1.0/hybrid:%s/entities/%s/checks/%s' % (account, entityID, checkID)
    headers = {
        "Content-type": "application/json",
        "X-Auth-Token": token
    }
    req = requests.get(url, headers=headers, verify=False)
    return req.json()

  def mycnf(self, f=os.environ['HOME'] + '/.my.cnf'):
    ''' Load my.cnf credentials '''
    config = ConfigParser.ConfigParser()
    try:
        config.read(f)
        user = config.get('client','user')
        password = config.get('client','password')
    except:
        self.warning('Unable to read mysql credentials from %s' % f)
        return False
    try:
        host = config.get('client', 'host')
    except:
        host = 'localhost'

    return {'host':host, 'user':user, 'password':password}

  def myrc(self):
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
      self.warning('Source your openrc file first.')
      sys.exit(1)

    try:
      result['OS_IDENTITY_API_VERSION'] = os.environ['OS_IDENTITY_API_VERSION']
    except:
      if 'v3' in result['OS_AUTH_URL']:
        result['OS_IDENTITY_API_VERSION'] = 3
      else:
        result['OS_IDENTITY_API_VERSION'] = 2

    return result

  def myquery(self, query, database, host=None):
    ''' Perform SQL query against database '''
    cred = self.mycnf()
    if not cred:
      return False
    if not host:
      host = cred['host']

    db = MySQLdb.connect(host=host, user=cred['user'], passwd=cred['password'], db=database)
    c = db.cursor()
    c.execute(query)
    results = c.fetchall()

    return results

  def mysql_check(self):
    ''' Check SQL replication status '''
    try:
      status = {}
      repl = self.myquery("SHOW status WHERE Variable_name LIKE 'wsrep_clu%' or Variable_name like 'wsrep_local_state%'", 'mysql')
      for r in repl:
        status[ r[0] ] = r[1]

      return status
    except:
      return False

  def keystone_auth(self):
    '''
    Authenticate with Keystone
    NOTE: user_domain_name and project_domain_name are required for auth to
    work properly. Not documented anywhere!
    '''
    try:
      rc = self.myrc()
      if int(rc['OS_IDENTITY_API_VERSION']) == 3:
        self.keystone_version = 3
        auth = v3.Password(auth_url=rc['OS_AUTH_URL'],
                           username=rc['OS_USERNAME'],
                           password=rc['OS_PASSWORD'],
                           project_name=rc['OS_TENANT_NAME'],
                           user_domain_name='default',
                           project_domain_name='default')
        s = session.Session(auth=auth)
        return s
    except KeyError:
        self.keystone_version = 2
        auth = v2.Password(auth_url=rc['OS_AUTH_URL'],
                           username=rc['OS_USERNAME'],
                           password=rc['OS_PASSWORD'],
                           project_name=rc['OS_TENANT_NAME'])
        s = session.Session(auth=auth)
        return s

    except Exception, e:
      self.warning('keystone_auth()', repr(e) )
      sys.exit()

  def keystone_gettenant(self, tenant):
    try:     
      rc = self.myrc()
      s = self.keystone_auth()

      if self.keystone_version == 3:
        k = keystone3.Client(session=s)
        tenants = k.projects.list()
      else:
        k = keystone.Client(session=s)
        tenants = k.tenants.list()

      for t in tenants:
        if t.name == tenant:
          return t

      return None

    except Exception, e:
     self.warning('keystone_gettenant()', repr(e) )
     return None

  def cinder_connect(self):
    ''' Establish connection to Cinder '''
    try:
      rc = self.myrc()
      s = self.keystone_auth()
      n = cinder.Client('1', session=s, endpoint_type='internal', insecure=True)
    except Exception, e:
      self.warning('cinder_connect()', repr(e) )
      return None

    return n

  def cinder_servicelist(self):
    ''' Retrieve list of Cinder services '''
    c = self.cinder_connect()
    if c:
      try:
        services = c.services.list()
      except AttributeError:
        self.warning('Bug in cinderclient API detected. Apply patch from /tmp/cinder-service.diff')
        sys.exit(1)
      return services
    else:
      return None

  def nova_connect(self):
    ''' Establish connection to nova '''
    try:
      rc = self.myrc()
      s = self.keystone_auth()
      n = nova.Client('2', session=s, endpoint_type='internal', insecure=True)
    except Exception, e:
      self.warning('nova_connect()', repr(e) )
      return None

    return n

  def nova_servicelist(self):
    n = self.nova_connect()
    if n:
      services = n.services.list()
      return services
    else:
      return None

  def neutron_connect(self):
    ''' Establish connection to Neutron '''
    try:
      rc = self.myrc()
      s = self.keystone_auth()
      n = neutron.Client(session=s, endpoint_type='internal', insecure=True)
    except Exception, e:
      self.warning('neutron_connect()', repr(e) )
      return None

    return n

  def neutron_agentlist(self):
    ''' Retrive list of Neutron agents '''
    n = self.neutron_connect()
    if n:
      agents = n.list_agents()
      return agents["agents"]
    else:
      return None

  def get_instance_net(self, instance):
    ''' Map networks and IPs of instance '''
    neutron = self.neutron_connect()
    networks = neutron.list_networks()['networks']
    instance_networks = None
    n = 0

    # This is required for "bad" environments
    while not instance_networks:
      if n > 0:
        self.warning('Investigate nova, lazy-loading is not performing properly') 
      if n > 3:
        return None
  
      instance_networks = instance.networks
      n += 1
      self.wait(1)

    res = []
    for net in instance_networks:
      ip = str( instance.networks[net][0] )
      for n in networks:
        if net == n['name']:
          net_id = n['id']
          res.append({'name':n['name'], 'net_id':net_id, 'ip':ip})

    if self.debug:
      self.warning('get_instance_net():', res)
    return res

  def verify_conn(self, instance):
    ''' SSH/Ping connectivity test against instance '''
    net_info = self.get_instance_net(instance)
    if not net_info:
      self.warning('Unable to get networking info for %s' % instance.name)
      return None
    res = {}

    if self.level == logging.DEBUG:
      verbose = '-vv'
    else:
      verbose = '-q'

    for n in net_info:
      net_id = n['net_id']
      ip = n['ip']
      command = 'ip net exe qdhcp-%s ssh %s -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
                 -i ~/.ssh/%s %s@%s ping -c 3 8.8.8.8 >/dev/null; echo $?' % (net_id, verbose, self.instance_key, self.instance_user, ip)
        
      if self.dhcp_agent:
        result = self.ssh(command,self.dhcp_agent)
        if result['stdout'] == '0\n':
          self.log('%s is accessible and has connectivity on %s!' % (instance.name, n['name']))
          res[n['net_id']] = True
        else:
          command = 'ip net exe qdhcp-%s ssh %s -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
                 -i ~/.ssh/%s %s@%s hostname >/dev/null; echo $?' % (net_id, verbose, self.instance_key, self.instance_user, ip)
          result = self.ssh(command,self.dhcp_agent)

          if result['stdout'] == '0\n':
             self.warning('%s is accessible, but has NO EXTERNAL CONNECTIVITY on %s!' % (instance.name, n['name']))
             res[n['net_id']] = True
          else:
            self.warning('%s is unreachable or not responding on %s! (code: %s)' % (instance.name, n['name'], result['stdout'].strip()))
            res[n['net_id']] = False

        if verbose == '-vv':
          print(host, command, result)
      else:
        self.warning('Unable to locate Neutron Agents container. Cannot proceed.')
    return res

  def resource_report(self, byCompute=False, byAZ=False):
    ''' Gather and print compute resources '''
    q = "select m.value AS AZ, c.hypervisor_hostname, c.vcpus, c.memory_mb, c.local_gb,\
         c.vcpus_used, c.memory_mb_used, c.local_gb_used, c.disk_available_least,\
         c.free_ram_mb, c.free_disk_gb from aggregate_hosts h join aggregate_metadata m\
         on m.aggregate_id=h.aggregate_id join compute_nodes c on c.hypervisor_hostname\
          = h.host WHERE h.deleted = 0 ORDER BY h.host"
    r = self.myquery(q, 'nova')

    host = self.findhost(socket.gethostname() + '_nova_api_os_compute_container')
    command = 'grep alloc /etc/nova/nova.conf'
    result = self.ssh(command, host)
    allocs = {'cpu_allocation_ratio':1,\
              'disk_allocation_ratio':1,\
              'ram_allocation_ratio':1}
    for s in result['stdout'].split('\n'):
      try:
        t, v = s.split(' = ')
        allocs[t] = int(v.strip())
      except ValueError:
        continue

    az = {}
    for l in r:
      compute = {'host':l[1], 'vcpus':int(l[2] * allocs['cpu_allocation_ratio']),\
                 'memory_mb':int(l[3] * allocs['ram_allocation_ratio']),\
                 'local_gb':int(l[4] * allocs['disk_allocation_ratio']), \
                 'vcpus_used':l[5], 'memory_mb_used':l[6], 'local_gb_used':l[7], \
                 'disk_avail_least':l[8], 'free_ram_mb':l[9], 'free_disk_gb':l[10]}
      try:
       az[ l[0] ].append(compute)
      except KeyError:
       az[ l[0] ] = [compute]

    tAZ = PrettyTable(['AZ', 'Total vCPUs', 'Used vCPUs', 'Memory Used (gb)', 'Memory Free (gb)', 'Disk Used' ,'Disk Free'])
    tCompute = PrettyTable(['Host', 'Total vCPUs', 'Used vCPUs', 'Memory Used (gb)', 'Memory Free (gb)', 'Disk Used' ,'Disk Free'])
    for a in az:

      if a == 'true' or a == 'false':
        continue

      vcpus_used = 0
      vcpus = 0
      memory_used = 0
      memory_free = 0
      disk_used = 0
      disk_free = 0

      for c in az[a]:
        vcpus_used += int(c['vcpus_used'])
        vcpus += int(c['vcpus'])
        memory_used += int(c['memory_mb_used'])
        memory_free += int(c['free_ram_mb'])
        disk_used += int(c['local_gb_used'])
        disk_free += int(c['free_disk_gb'])
        tCompute.add_row([c['host'], vcpus, vcpus_used, memory_used/1024, memory_free/1024, disk_used, disk_free])
      tAZ.add_row([a, vcpus, vcpus_used, memory_used/1024, memory_free/1024, disk_used, disk_free])

    if byAZ:
      print(tAZ)
    if byCompute:
      print(tCompute)

  def volume_check(self, instance):
    ''' Create Cinder volume, attach to instance and mkfs on it '''
    nova = self.nova_connect()
    cinder = self.cinder_connect()
    self.log('Testing cinder functionality against %s...' % instance.name)
    vol_name = 'rpc-qc-%s' % uuid.uuid1()
    try:
      volume = cinder.volumes.create(1, display_name=vol_name)
      self.log('Waiting for volume to be available...')
      status = None
      while not status == 'available':
        if status == 'error':
          self.warning('Cinder volume errored out.')
          return 1

        v = cinder.volumes.get(volume.id)
        status = v.status
        self.wait(10)

      self.log('Attaching and verifying volume access...')
      #nova.volumes.attach(volume.id, instance.id, '/dev/vdb')
      subprocess.call(['nova', 'volume-attach', instance.id, volume.id])
      time.sleep(5)

      net_info = self.get_instance_net(instance)
      net_id = net_info[0]['net_id']
      ip = net_info[0]['ip']
      result = []
      for command in ['sudo mkfs.ext3 /dev/vdb > /dev/null; echo $?',\
                      'sudo mkdir /root/test; sudo mount /dev/vdb /root/test; echo $?',\
                      'sudo touch /root/test/write > /dev/null; echo $?']:
        prefix = 'ip net exe qdhcp-%s ssh -q -o StrictHostKeyChecking=no -i %s %s@%s ' % (net_id, self.private_key, self.instance_user, ip)
        result.append(self.ssh(prefix + command, self.dhcp_agent))
      mkfs, mount, touch = result
      if mkfs['stdout'] == '0\n' and touch['stdout'] == '0\n':
        self.log('Volume accessible and writeable on %s!' % instance.name)
      else:
        self.warning('There was an issue with the volume. (Format: %s, Mount: %s, Write: %s)' % \
        (mkfs['stdout'].strip(), mount['stdout'].strip(), touch['stdout'].strip()))

    finally:
      self.log('Cleaning up cinder...')
      subprocess.call(['nova', 'volume-detach', instance.id, volume.id])
      time.sleep(10)
      #TODO: Can't delete a volume that doesn't exist
      cinder.volumes.delete(volume)

  def snapshot_check(self, instance):
    ''' Perform functional snapshot test '''
    nova = self.nova_connect()
    self.log('Starting snapshot against %s...' % instance.name)
    snap_name = 'rpc-qc-%s' % uuid.uuid1()

    try:
      snap_id = nova.servers.create_image(instance.id, snap_name)
      while True:
        res = nova.images.get(snap_id)
        if res.status == 'ACTIVE':
          self.log('Snapshot successful.')
          break
        elif res.status == 'SAVING':
          self.wait()
        else:
         self.warning('Snapshot in unknown state (%s), giving up.' % res.status)
         return None

      return snap_id
    except:
      return None

  def compute_check(self, climit=None, nlimit=None, cinder=True):
    ''' Perform function test against nova-compute '''
    nova = self.nova_connect()
    
    neutron = self.neutron_connect()
    self.log('Testing nova functionality...')

    tenant = self.keystone_gettenant(self.myrc()['OS_TENANT_NAME'])
    instances = []
    images = nova.images.list()
    networks = neutron.list_networks()['networks']
    computes = nova.services.list(binary='nova-compute')
    azs = nova.availability_zones.list()
    az_pair = {}
    snap_id = None
    keypairs = nova.keypairs.list()
    existing_nova_quota = nova.quotas.get(tenant.id)
    existing_neutron_quota = neutron.show_quota(tenant.id)
    new_neutron_quota = existing_neutron_quota
    new_neutron_quota['quota']['port'] = -1
    qc_flavor = None
    qc_image = None
    secgroup = None

    for c in computes:
      if not c.state == 'up':
        computes.remove(c)
        self.warning('%s is not up, will not test against!' % c.host)

    for a in azs[1:]:
      for z in a.hosts:
        az_pair[z] = a.zoneName

    if self.image:
      qc_image = self.image
    else:
      for i in images:
        if 'Ubuntu' in i.name:
          qc_image = i.id
          break

    if not qc_image:
      self.warning('Unable to locate Ubuntu image. Specify image UUID with --image')
      sys.exit(1)

    if self.instance_key:
      keypair_name = self.instance_key
    else:
      keypair_name = 'rpc_support'

    for k in keypairs:
      if k.name == keypair_name:
        rpc_keypair = True
    if not rpc_keypair:
      self.warning('Missing %s keypair. Check your tenant and keypair list to ensure it exists.' % keypair_name)
      sys.exit(1)

    if climit:
      limit_to = []
      limit_text = []
      for c in computes:
        if c.host in climit:
          limit_to.append(c)
          limit_text.append(c.host)

      if len(limit_to) > 0:
        computes = limit_to
        self.log('Limiting tests to: %s' % ' '.join(limit_text) )
      else:
        self.warning('Compute limits resulted in no computes! Exiting.')
        sys.exit(1)

    try:
      nova.quotas.update(tenant.id, cores=-1, instances=-1, ram=-1)
      neutron.update_quota(tenant.id, new_neutron_quota)
      qc_flavor_name = 'rpc-qc-%s' % uuid.uuid1()
      qc_flavor = nova.flavors.create(qc_flavor_name, 2048, 1, 15)
      self.log('Flavor created.')

      secgroup = nova.security_groups.create('rpc-qc-secgroup', 'Temporary secgroup for QC')
      secgroup_rule_icmp = nova.security_group_rules.create(secgroup.id, ip_protocol='icmp', from_port=0, to_port=0, cidr='0.0.0.0/0')
      secgroup_rule_ssh = nova.security_group_rules.create(secgroup.id, ip_protocol='tcp',from_port=22, to_port=22, cidr='0.0.0.0/0')
      secgroup_rule_dhcp = nova.security_group_rules.create(secgroup.id, ip_protocol='udp',from_port=67, to_port=68, cidr='0.0.0.0/0')
      self.log('Security group rules created.')

      nic = []
      if nlimit:
        for n in nlimit:
          nic.append({'net-id':n})  
      else:
        for n in networks:
          if n['router:external']:
            continue
          if len(n['subnets']) == 0:
            continue
          if n['name'] == 'INSIDE_NET':
            nic.insert(0,{'net-id':n['id']})
          else:
            nic.append({'net-id':n['id']})

      for c in computes:
        qc_name = 'rpc-qc-%s' % c.host
        az_name = '%s:%s' % (az_pair[c.host], c.host)
        instances.append( nova.servers.create(qc_name, qc_image, qc_flavor.id, security_groups=[secgroup.id,],
                                              key_name=keypair_name, availability_zone=az_name, nics=nic) )
        self.log('Instance, %s, created.' % qc_name)

      self.log('Waiting for instances to become available...')
      while True:
        is_active = []
        is_error = []
        for i in instances:
          instance = nova.servers.get(i.id)
          if instance.status == 'ACTIVE':
            is_active.append(i)
          if instance.status == 'ERROR':
            is_error.append(i)
        if (len(is_active) + len(is_error)) == len(instances):
          break
        else:
          self.wait()

      if is_error:
        self.warning('Some instances failed to build:')
        for i in is_error:
          self.warning('\t%s' % i.name)
          self.warning('%s\n' % i.fault)

      is_accessible = []
      self.log('Testing network connectivity of instances (%s)...' % self.dhcp_agent)
      self.wait(30)

      for i in instances:
        whats_up = self.verify_conn(i)
        if whats_up:
          for n in whats_up:
            if whats_up[n]:
              is_accessible.append((i,n))
      if len(is_accessible) > 0:
        if cinder:
          for i, n in is_accessible:
            self.volume_check(i)
        else:
          self.warning('cinder-volume service not found. Skipping Cinder functionality check.')

        snap_instance, snap_instance_net = is_accessible[-1]
        snap_id = self.snapshot_check(snap_instance)
        qc_snap_name = 'rpc-qc-snap-%s' % uuid.uuid1()
        nic = [{'net-id':snap_instance_net}]

        if snap_id:
          self.log('Creating instance from snapshot.')
          snap_i = nova.servers.create(qc_snap_name, snap_id, qc_flavor.id, security_groups=[secgroup.id,],
                                       key_name=keypair_name, nics=nic)
          instances.append(snap_i)

          self.log('Waiting for instance to become available...')
          while True:
            instance = nova.servers.get(snap_i.id)
            if instance.status == 'ACTIVE':
              self.wait(30)
              self.verify_conn(snap_i)
              break
            if instance.status == 'ERROR':
              self.warning('Instance failed to build from snapshot.')
              self.warning('\t%s' % instance.fault)
              break
            else:
              self.wait()
      else:
        self.warning('No instances accessible to perform additional checks on.')
        self.wait(30)

    except KeyboardInterrupt:
      self.warning('Caught keyboard interrupt, quitting!')

    finally:
      self.log('Cleaning up nova...')
      for i in instances:
        try:
          nova.servers.delete(i.id)
          self.wait()
        except:
         continue

      try:
        self.wait()
        if qc_flavor:
          nova.flavors.delete(qc_flavor.id)
      except:
        self.warning('Failed to delete flavor, %s' % qc_flavor.id)
        pass

      try:
        self.wait()
        if snap_id:
          nova.images.delete(snap_id)
      except:
        self.warning('Failed to delete image, %s' % snap_id)
        pass

      try:
        self.wait()
        if secgroup:
          nova.security_groups.delete(secgroup.id)
      except:
        self.warning('Failed to delete security group, %s' % secgroup.id)

      try:
        nova.quotas.update(tenant.id, cores=existing_nova_quota.cores, \
                                      instances=existing_nova_quota.instances, \
                                      ram=existing_nova_quota.ram)
        neutron.update_quota(tenant.id, existing_neutron_quota)
      except:
        self.warning('Failed to revert nova quotas (cores: %s, instances: %s, ram: %s, ports: %s)' % \
                                                    (existing_nova_quota.cores, \
                                                    existing_nova_quota.instances, \
                                                    existing_nova_quota.ram, \
                                                    existing_neutron_quota['quota']['port']))

  def main(self):
    parser = argparse.ArgumentParser()
    parser.add_argument('--account', help='Customer account number used by MaaS')
    parser.add_argument('--token', help='MaaS impersonation token')
    parser.add_argument('--limit', help='Limit functional tests to given hosts, comma delimited')
    parser.add_argument('--pin',   help='Limit functional tests to given networks, comma delimited')
    parser.add_argument('--image', help='Specify which image to use when creating instances.')
    parser.add_argument('--debug', help='Enable debug output from Openstack and modules', action='store_true')
    parser.add_argument('--stall', help='Multiplier on sleeps. Set/increase for slow environments.', default=1)
    parser.add_argument('--skip-cinder', help='Do not perform Cinder checks.', action='store_true')
    parser.add_argument('--compute-report', help='Print resource report', action='store_true')
    parser.add_argument('--az-report', help='Print resource report grouped by AZ', action='store_true')
    parser.add_argument('--private-key', help='Use provided key for host SSH commands', default=None)
    parser.add_argument('--instance-key', help='Use provided key for instance SSH commands. Default: rpc_support', default='rpc_support')
    parser.add_argument('--instance-user', help='Use provided user for instance SSH commands. Default: ubuntu', default='ubuntu')
    args = parser.parse_args()

    #logging
    streamformat = "%(levelname)s (%(module)s:%(lineno)d) %(message)s"
    if args.debug:
      self.debug = True
      self.level = logging.DEBUG
    else:
      self.debug = False
      self.level = logging.ERROR

    logging.basicConfig(level=self.level, format=streamformat)
    logging.getLogger('iso8601').setLevel(self.level)

    #defaults
    self.creport = args.compute_report
    self.areport = args.az_report
    self.stall = args.stall
    self.instance_user = args.instance_user
    self.instance_key = args.instance_key
    self.dhcp_agent = None
    healthy = {'nova':True, 'neutron':True, 'cinder':True, 'maas':True, 'database':True}

    if args.account and args.token:
      maas = self.maas_overview(args.account, args.token)
    else:
      self.warning('No account number or token provided. MaaS will not be checked.')
      maas = None
      healthy['maas'] = 'disabled'

    if args.limit:
      compute_limit = args.limit.split(',')
    else:
      compute_limit = None
      
    if args.pin:
      net_limit = args.pin.split(',')
    else:
      net_limit = None

    if args.image:
      self.image = args.image
    else:
      self.image = None

    if args.private_key:
      if os.path.exists(args.private_key):
        self.private_key = args.private_key
      else:
        self.warning( 'Provided private key does not exist. Check your path and try again.' )
        sys.exit()
    else:
      self.private_key = None                                                                                                                                              

    if args.instance_key:
      self.instance_key = args.instance_key
      
    self.log('Starting service checks...')
    nova_services = self.nova_servicelist()
    agents = self.neutron_agentlist()
    cinder_services = self.cinder_servicelist()
    do_cinder_check = False
    db = self.mysql_check()

    for s in nova_services:
      if not s.state == 'up':
        self.warning( '%s on %s is not checking in properly!' % (s.binary, s.host) )
        healthy['nova'] = False

    for a in agents:
      if a['agent_type'].lower() == 'dhcp agent' and not self.dhcp_agent:
        self.dhcp_agent = a['host']
      if not a['alive'] == True:
        self.warning( '%s on %s is not checking in properly!' % (a['agent_type'], a['host'] ) )
        healthy['neutron'] = False

    try:
      socket.gethostbyname(self.dhcp_agent)
    except:
      self.warning('%s is not resolveable. Please provide IP address of Neutron Agents host.' % self.dhcp_agent)
      self.dhcp_agent = raw_input('IP: ')

    if len(cinder_services) > 0:
      for s in cinder_services:
        if s.binary == 'cinder-volume':
          do_cinder_check = True
          self.log('Cinder volume service found. Will test functionality.')
          break
        if not s.state == 'up':
          self.warning( '%s on %s is not checking in properly!' % (s.binary, s.host) )
          healthy['cinder'] = False
    else:
      healthy['cinder'] = 'disabled'

    if db:
      if not db['wsrep_local_state_comment'] == 'Synced' and not db['wsrep_cluster_size'] >= '3':
        self.warning('Database replication appears to have issues.')
        healthy['database'] = False

    if maas:
      for e in maas['values']:
        for a in e['latest_alarm_states']:
          if not a['state'] == 'OK':
            healthy['maas'] = False
            checkLabel = self.maas_getcheck(args.account, args.token, a['entity_id'], a['check_id'])['label']
            print( checkLabel, a['check_id'], a['state'])

    for s in ['Database', 'Nova', 'Neutron', 'Cinder', 'MAAS']:
        if healthy[s.lower()] == 'disabled':
          self.warning('%s is not enabled/installed.' %s)
        elif healthy[s.lower()]:
          self.log('%s shows no issues. :)' % s)
        else:
          self.warning('%s is showing signs of possible issues. Investigate further! XXX' % s)

    print()
    if args.skip_cinder:
      do_cinder_check = False

    res = self.compute_check(compute_limit, net_limit, do_cinder_check)
    print()
    self.resource_report(self.creport, self.areport)
    sys.exit(res)

if __name__ == "__main__":
    QC()
