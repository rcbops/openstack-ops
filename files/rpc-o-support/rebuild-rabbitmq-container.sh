#!/bin/bash
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
