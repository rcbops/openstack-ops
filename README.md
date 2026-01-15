rcbops/openstack-ops
====================

Version
-------

Version **1.3.x** is intended for all releases of OSA up to Rocky (18).

All following releases (19 and later) will use the **master** branch.


Intent
------

This repository is intended to collect all scripts around OpenStack administration with RPC.
It has been converted into a standalone module to be compatible with RPC-O and increasingly
other products, R or ceph, to automate common maintenance and administrative tasks.


Playbooks
---------

| Name                      | Parameters       |  Description                  |
|---------------------------|------------------|-------------------------------|
| archive-control-plane.yml | openstack_release (Optional, used to designate the origin version of the backup) | Archives running OSA managed LXC containers into /openstack/backup/control-plane. Services inside containers will experiences short freeze during archiving |
| configure-packagemanager.yml | For debian style os, `apt_autoupdate_enabled` can be set as `apt_autoupdate_enabled=1` to enable automatic upgrades moving forward | Installs package dependencies while also configuring automated package update |
| configure-bash-environment.yml | None | Configures openstack cli bash completion, set vim as default editor and maintain MOTD |
| configure-cpu-governor.yml | None | Optional, disable CPU ondemand governor and replace it with performance |
| configure-hosts.yml | ops_host_kernel_modules, ops_host_kernel_sysctl | Load bonding and 8021q modules, enabled IP forwarding |
| configure-glance.yml | None | Install standard RPC OSS images like CentOS, Ubuntu etc.  |
| configure-neutron.yml | None | Setup RPC security group and install neutron debugging tools inside agent container |
| configure-nova.yml | None | Install standard nova flavor (e.g. m1.small) |
| configure-ceph.yml | Defaults ceph_stable_release to pacific, options include octopus for older releases.  | Configure ceph for openstack (mainly pools at this time) |
| gather-facts.yml | None | Rebuild ansible facts when necessary |
| fix-lxc-container-bindmount.yml | None | Optional mitigation for RO-4387 on Newton+ containers when needed |
| install-consul.yml | None | Playbook used to install consul on the infra hosts, used as consensus service for masakari |
| install-holland-db-backup.yml| None | Installs Holland DB backup into the galera container |
| install-hp-server-monitoring.yml | None | Installs the HP Server Monitoring Tools |
| install-dell-server-monitoring.yml | None | Installs the Dell Server Monitoring Tools |
| install-hw-raid-tools.yml | None | Installs the famous  megacli, lsiutil, arcconf tools onto all storage hosts |
| install-pccommon.yml | None | Deploys the post install QC script pccommon |
| install-sos-tool.yml | None | Deploys the RPC sos tool onto all hosts |
| rebuild-ssh-known-hosts.yml | None | Rebuild local SSH known hosts from current installed containers and hosts which is necessary post leapfrog upgrades |
| support-key.yml | None | Install the RPC support SSH key into nova which is used for pccommon |
| swift-datacrusher.yml | xfs_inode_size, xfs_mount_options, xfs_format_options, exclude_drive_labels, exclude_drive_labels_format_option | Automatically reformat a entire swift cluster (WIPE ALL DATA). Use only with caution |
| update-hp-firmware.yml | firmware_use_meltdown | Automatically install the latest tested firmware for HP DL380 G9 server (NIC,ILO,RAID,BIOS) |


Product scripts
---------------

| Name                           | Parameters       |  Description                                  |
|--------------------------------|------------------|-----------------------------------------------|
| scripts/deploy-rpco.sh         | OSA_RELEASE      | Defaults to the latest greenfield OSA release |
| scripts/build-ironic-images.sh | [bionic,jammy,jammy-lvm,centos9] | Builds the given OS image, only one at a time can be specified |


Support scripts
---------------

Most RPC OpenStack supports scripts are currently running outside of ansible and are stored
inside the `playbooks/files` folder.
Those scripts will be converted into individual Ansible tasks over time, when necessary.

### rpc-o-support

This folder currently collects all support scripts for active RPC-O products
RPC-R should be keept in a different once applicable due to the architectual differences.

### archive folder

The scripts listed inside the archive folder or for historical reasons keept in this folder until the
the product, it was intended to be used for, completely was removed from operations like RPC4 (probably never dies).


Requirements
------------

This module expect to be installed/applied on a working RPC OpenStack environment which does run a
supported product lifecycle (RPC-O currently)


Execution
---------

    # Rocky and older releases
    git checkout 1.3.x (Rocky and lower)
    cd /opt/openstack-ops

    . /usr/local/bin/openstack-ansible.rc
    openstack-ansible playbooks/main.yml


    # Newer releases
    git clone https://github.com/rcbops/openstack-ops.git /opt/openstack-ops

    /opt/openstack-ops/bootstrap.sh
    cd /opt/openstack-ops && ansible-playbook playbooks/main.yml


License
-------

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Author Information
------------------

Rackspace Private Cloud - OpenStack
