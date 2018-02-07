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
The repository is currently being converted into a Ansible Galaxy compatible role in order to
support intregration into post deployment processes of RPC-O and others.


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

    git clone -b 1.0.0 https://github.com/rsoprivatecloud/openstack-ops.git /opt/openstack-ops
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
