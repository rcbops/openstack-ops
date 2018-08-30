rsoprivatecloud/openstack-ops
=============================

Build status
------------

Travis is now used to lint various scripts in order to guarantee minimal coding standards.

| Branch             | Build status     |
|--------------------|------------------|
| Master Branch | [![Build Status: Master Branch](https://travis-ci.org/rsoprivatecloud/openstack-ops.svg?branch=master)](https://travis-ci.org/rsoprivatecloud/openstack-ops) |


Intent
------

This repository is intended to collect all scripts around OpenStack administration with RPC.
It has been converted into a standalone module to be compatible with RPC-O and increasingly
other products, R or ceph, to automate common maintenance and administrative tasks.


Playbooks
---------

| Name                      | Parameters       |  Description                  |
|---------------------------|------------------|-------------------------------|
| archive-control-plane.yml | rpc_release (Used to designate the origin version of the backup) | Archives running OSA managed LXC containers into /openstack/backup/control-plane. Services inside containers will experiences short freeze during archiving |
| configure-apt.yml | None | Installs openstack-ops APT package dependencies while also turning off unattended APT upgrades |
| configure-bash-environment.yml | None | Configures openstack cli bash completion, set vim as default editor and maintain MOTD |
| configure-cpu-governor.yml | None | Optional, disable CPU ondemand governor and replace it with performance |
| configure-hosts.yml | ops_host_kernel_modules, ops_host_kernel_sysctl | Load bonding and 8021q modules, enabled IP forwarding |
| configure-neutron.yml | None | Setup RPC security group and install neutron debugging tools inside agent container |
| configure-nova.yml | None | Install standard nova flavor (e.g. m1.small) |
| configure-spice-console.yml | None | Reinstall the missing CRTL+ALT+DEL Button to login into Windows guests |
| gather-facts.yml | None | Rebuild ansible facts when necessary |
| fix-lxc-container-bindmount.yml | None | Optional mitigation for RO-4387 on Newton+ containers when needed |
| install-holland-db-backup.yml| None | Installs Holland DB backup into the galera container |
| install-hp-server-monitoring.yml | None | Installs the HP Server Monitoring Tools |
| install-hw-raid-tools.yml | None | Installs the famous  megacli, lsiutil, arcconf tools onto all storage hosts |
| install-pccommon.yml | None | Deploys the post install QC script pccommon |
| install-sos-tool.yml | None | Deploys the RPC sos tool onto all hosts |
| rebuild-ssh-known-hosts.yml | None | Rebuild local SSH known hosts from current installed containers and hosts which is necessary post leapfrog upgrades |
| support-key.yml | None | Install the RPC support SSH key into nova which is used for pccommon |
| swift-datacrusher.yml | xfs_inode_size, xfs_mount_options, xfs_format_options, exclude_drive_labels, exclude_drive_labels_format_option | Automatically reformat a entire swift cluster (WIPE ALL DATA). Use only with caution |
| update-hp-firmware.yml | firmware_use_meltdown | Automatically install the latest tested firmware for HP DL380 G9 server (NIC,ILO,RAID,BIOS) |

Operational scripts
-------------------

Most RPC OpenStack supports scripts are currently running outside of ansible and are stored
inside the playbooks/files folder.
Those scripts will be converted into individual Ansible tasks over time, when necessary.

### rpc-o-support

This folder currently collects all support scripts for active RPC-O products
RPC-R should be keep in a different once applicable due to the architectual differences.

### archive folder

The scripts listed inside the archive folder or for historical reasons keept in this folder until the
the product, it was intended to be used for, completely was removed from operations like RPC4 (probably never dies).


### Other content

Some scripts are still linked in on top level in order not to break existing processes
like rpc-support role of RPC-O until those gets updated



Requirements
------------

This module expect to be installed/applied on a working RPC OpenStack environment which does run a
supported product lifecycle (RPC-O currently)


Execution
----------------

    git clone https://github.com/rsoprivatecloud/openstack-ops.git /opt/openstack-ops
    source /usr/local/bin/openstack-ansible.rc

    cd /opt/openstack-ops/playbooks; openstack-ansible main.yml


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
