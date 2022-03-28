#!/bin/bash

LANG=en_US.UTF-8

OA_INF=/opt/openstack-ansible/playbooks/inventory

cd /opt/openstack-ansible/playbooks 2>/dev/null || cd /opt/rpc-openstack/openstack-ansible/playbooks

if [ $( echo "$@" |grep i-know-what-i-do |wc -l ) -eq 0 ]; then
  echo "Please call execute $0 i-know-what-i-do"
  exit 1
fi

for i in $(seq 1 20); do
  echo "${i}/20 Press CTRL+C to stop"
  sleep 1
done

grep -q 'no_containers: true' /etc/openstack_deploy/*.yml /etc/openstack_deploy/conf.d/*.yml 2>/dev/null
if [ $? -eq 1 ]; then
  openstack-ansible -e container_group="rabbit_mq_container" -e force_containers_destroy="yes" -e force_containers_data_destroy="yes" lxc-containers-destroy.yml
  openstack-ansible lxc-containers-create.yml --limit rabbit_mq_container:shared-infra_hosts:infra_hosts
else
  ansible shared-infra_hosts -m shell -a 'pkill -f epmd; apt -y purge rabbitmq-server'
  ansible shared-infra_hosts -m shell -a 'rm -rf /var/lib/rabbitmq/mnesia; mkdir /var/lib/rabbitmq/mnesia; chown rabbitmq:rabbitmq /var/lib/rabbitmq/mnesia'
fi

openstack-ansible rabbitmq-install.yml

# Re-add OpenStack rabbitmq users
OUTP=`openstack-ansible --list-tags /opt/openstack-ansible/playbooks/os-nova-install.yml 2>&1`

if [ `echo "$OUTP" |grep nova-rabbitmq-user |wc -l` -gt 1 ]; then
  TAGS="keystone-rabbitmq,keystone-rabbitmq-user,keystone-rabbitmq-vhost,glance-rabbitmq,glance-rabbitmq-user,glance-rabbitmq-vhost,cinder-rabbitmq,cinder-rabbitmq-user,cinder-rabbitmq-vhost,nova-rabbitmq,nova-rabbitmq-user,nova-rabbitmq-vhost,neutron-rabbitmq,neutron-rabbitmq-user,neutron-rabbitmq-vhost,heat-rabbitmq,heat-rabbitmq-user,heat-rabbitmq-vhost,common-rabbitmq"

  ansible 'ceilometer_collector' --list-hosts 2>/dev/null | grep -q "No hosts matched" || TAGS="$TAGS,ceilometer-rabbitmq,ceilometer-rabbitmq-user,ceilometer-rabbitmq-vhost"
elif [ `echo "$OUTP" |grep common-rabbitmq |wc -l` -gt 1 ]; then
  TAGS="common-rabbitmq"
fi;

echo "Running OSA Plays with tag: $TAGS"

if [ -n "$TAGS" ]; then
  openstack-ansible setup-openstack.yml --tags "$TAGS"

  if [ -d /opt/rpc-maas/playbooks ]; then
    pushd /opt/rpc-maas/playbooks
      openstack-ansible -i $OA_INF maas-infra-rabbitmq.yml
    popd
  else
    pushd /opt/rpc-openstack/rpcd/playbooks
      openstack-ansible setup-maas.yml --tags rabbitmq-user
    popd
  fi
fi
