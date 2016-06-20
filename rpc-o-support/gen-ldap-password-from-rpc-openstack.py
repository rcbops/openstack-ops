#!/usr/bin/python

from __future__ import print_function
import ldap,yaml

ldap_host = 'ldap://ldap'
ldap_base_dn = 'OU=OpenStack,OU=Service Accounts,OU=Administrative Accounts,DC=foo,DC=bar'
simulation = 0 #Flip to one if you just want to get the output of what the script is doing

# If initial_user_pwd is specified, the ldap bind will use this password to authenticate and update the password
# with the service_password from the user_secrets.yml and user_extras_secrets.yml
ldap_initial_bind_pwd = 'HolySmokes123'

# Where is my openstack-ansible (OSA) service username and password configuration stored
osa_variables_file = '/etc/openstack_deploy/user_variables.yml'
osa_variables_extras_file = '/etc/openstack_deploy/user_extras_variables.yml'
osa_secrets_file = '/etc/openstack_deploy/user_secrets.yml'
osa_secrets_extras_file = '/etc/openstack_deploy/user_extras_secrets.yml'

osa_user_tokens =  { #'ceilometer_service_user_name':'ceilometer_service_password',
                      'cinder_service_user_name':'cinder_service_password',
                      'glance_service_user_name':'glance_service_password',
                      'heat_service_user_name':'heat_service_password',
                      'heat_stack_domain_admin':'heat_stack_domain_admin_password',
                      'keystone_admin_user_name':'keystone_auth_admin_password',
                      'keystone_service_user_name':'keystone_service_password',
                      'neutron_service_user_name':'neutron_service_password',
                      'nova_service_user_name':'nova_service_password',
                      'swift_dispersion_user':'swift_dispersion_password',
                      'swift_service_user_name':'swift_service_password',
                      'maas_keystone_user':'maas_keystone_password' }



def get_config(path):
  try:
    with open(path) as f:
      data = f.read()
  except IOError as e:
    if e.errno == errno.ENOENT:
      data = None
    else:
      raise e

  if data is None:
    return {}
  else:
    # assume config is a dict
    return yaml.safe_load(data)



def update_ldap_passwords_from_osa():
  ldap_con = ldap.initialize(ldap_host)
  ldap_con.set_option( ldap.OPT_X_TLS_DEMAND, True )
  ldap_con.set_option( ldap.OPT_DEBUG_LEVEL, 255 )


  for token in osa_user_tokens:
    print("="*25)
    print("OSA Token: ", token)
    vyml = dict( get_config(osa_variables_file).items() + get_config(osa_variables_extras_file).items() )
    syml = dict( get_config(osa_secrets_file).items() + get_config(osa_secrets_extras_file).items() )

    service_user = vyml[ token ]
    service_password = syml[ osa_user_tokens[ token ] ]

    try:
      bind_pwd=""
      if ldap_initial_bind_pwd:
        bind_pwd = ldap_initial_bind_pwd
      else:
        bind_pwd = service_password

      ldap_con.simple_bind_s( service_user, bind_pwd )
      print ("Service user ",service_user, " password ", service_password)

      new_service_password = service_password
      ldap_new_password = ('"%s"' % new_service_password).encode("utf-16-le")
      if not simulation:
        ldap_mod_attrs = [( ldap.MOD_REPLACE, 'unicodePwd', ldap_new_password)],( ldap.MOD_REPLACE, 'unicodePwd', ldap_new_password)]
        ldap_con.modify_s('CN=%s,%s' % service_user, ldap_base_dn, ldap_mod_attrs)
      else:
        print("LDAP update skipped during simulation while trying to update unicodePwd with ", ldap_new_password)
    except Exception as e:
       print("Could not update user ", service_user, " with token ", token)
       print("ERROR: ", e )
    else:
        print("LDAP Password successfully changed.")



if __name__ == "__main__":
   update_ldap_passwords_from_osa()
