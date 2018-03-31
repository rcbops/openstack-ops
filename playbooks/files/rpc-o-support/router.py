from __future__ import print_function                                                                                                                                                    
import os
import sys
import uuid
import logging
import socket
from neutronclient.v2_0 import client as neutron
from keystoneclient.auth.identity import v3
from keystoneclient.auth.identity.generic import password as v2
from keystoneclient import session
from keystoneclient import client as keystone
from keystoneclient.v3 import client as keystone3
from prettytable import PrettyTable
import pprint
import paramiko

class router:

  def __init__(self):
    """ Construct """
    self.main()

  def warning(self, *objs):
    print("!! ", *objs, file=sys.stderr)

  def log(self, *objs):
    print("** ", *objs, file=sys.stdout)

  def ssh(self, command, host):
    '''
    Execute command on host
    Return output as dict
    '''
    logger = paramiko.util.logging.getLogger()
    logger.setLevel(logging.ERROR)

    #if self.private_key:
    #  k = paramiko.RSAKey.from_private_key_file(self.private_key)

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

  def neutron_routerlist(self):
    n = self.neutron_connect()
    if n:
      routers = n.list_routers()
      return routers["routers"]
    else:
      return None

  def neutron_routerportlist(self, router):
    n = self.neutron_connect()
    if n:
      ports = n.list_ports(device_id=router)
      return ports['ports']
    else:
      return None

  def neutron_l3agent_hosting_router(self, router):
    n = self.neutron_connect()
    if n:
      agent = n.list_l3_agent_hosting_routers(router)
      return agent
    else:
      return None

  def neutron_router_iface_count(self, host, netns, iface):
    command = 'ip net exe qrouter-%s ip a s %s| grep -c inet\ ' % (netns, iface)
    result = self.ssh(command, host)
    return result['stdout']

  def main(self):
    routers = self.neutron_routerlist()
    ports = {}
    self.iface = None
    for r in routers:
      id = r['id']
      name = r['name']
      ports = self.neutron_routerportlist( id )
      print('\nRouter: %s (%s)' % (id, name))
      print('Tenant: %s' % r['tenant_id'])
      port_table = PrettyTable(['Port ID', 'Host ID', 'Device Owner', 'Status'])

      for p in ports:
        host_id = p['binding:host_id']
        port_id = p['id']
        status = p['status']
        device_owner = p['device_owner']
        port_table.add_row([port_id, host_id, device_owner, status])

        if device_owner == 'network:router_gateway':
          self.iface = 'qg-%s' % port_id[:11]

      print( port_table )

      agents = self.neutron_l3agent_hosting_router(id)
      agent_table = PrettyTable(['L3 Agent ID', 'Admin State', 'Alive', 'Host', 'iface #', 'Actual iface #'])
      for a in agents['agents']:
        heartbeat = a['heartbeat_timestamp']
        admin_state = a['admin_state_up']
        alive = a['alive']
        id = a['id']

        host = a['host']
        ip = None
        iface_count = 0
        try:
          socket.gethostbyname( str(host) )
        except:
          print( '%s is not resolveable. Please provide IP address of Neutron Agents host.' % host )
          ip = raw_input('IP: ')
        
        if ip and self.iface:
          iface_count = self.neutron_router_iface_count(ip, r['id'], self.iface)
        elif self.iface:
          iface_count = self.neutron_router_iface_count(host, r['id'], self.iface)

        interfaces = a['configurations']['interfaces']
        floating_ips = a['configurations']['floating_ips']
        agent_table.add_row([id, admin_state, alive, host, int(interfaces) + int(floating_ips), iface_count])

      print( agent_table )




if __name__ == "__main__":
  router()
