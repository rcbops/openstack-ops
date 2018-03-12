#!/bin/bash

LANG=en_US.UTF-8

cd /opt/rpc-openstack/openstack-ansible/playbooks

eval $@
if [ -z "$iknowwhatido" ]; then
  echo "Please call execute $0 iknowwhatido=1"
  exit 1
fi

for i in $(seq 1 20); do
  echo "${i}/20 Press CTRL+C to stop"
  sleep 1
done

openstack-ansible -e container_group="rabbit_mq_container" lxc-containers-destroy.yml
openstack-ansible lxc-containers-create.yml --limit rabbit_mq_container
openstack-ansible rabbitmq-install.yml

# Re-add OpenStack rabbitmq users
grep -q nova_rabbitmq_vhost /etc/ansible/roles/os_nova/defaults/main.yml >/dev/null 2>&1
if [ "$?" -eq 0 ]; then
  TAGS="keystone-rabbitmq,keystone-rabbitmq-user,keystone-rabbitmq-vhost,glance-rabbitmq,glance-rabbitmq-user,glance-rabbitmq-vhost,cinder-rabbitmq,cinder-rabbitmq-user,cinder-rabbitmq-vhost,nova-rabbitmq,nova-rabbitmq-user,nova-rabbitmq-vhost,neutron-rabbitmq,neutron-rabbitmq-user,neutron-rabbitmq-vhost,heat-rabbitmq,heat-rabbitmq-user,heat-rabbitmq-vhost"

  ansible 'ceilometer_collector' --list-hosts 2>/dev/null | grep -q "No hosts matched" || TAGS="$TAGS,ceilometer-rabbitmq,ceilometer-rabbitmq-user,ceilometer-rabbitmq-vhost"

  openstack-ansible setup-everything.yml --tags $TAGS
else
  openstack-ansible setup-everything.yml --tags rabbitmq-user
fi;

if [ -d /opt/rpc-maas/playbooks ]; then
  pushd /opt/rpc-maas/playbooks
    openstack-ansible -i /opt/rpc-openstack/openstack-ansible/playbooks/inventory maas-infra-rabbitmq.yml
  popd
else
  pushd /opt/rpc-openstack/rpcd/playbooks
    openstack-ansible setup-maas.yml --tags rabbitmq-user
  popd
fi
