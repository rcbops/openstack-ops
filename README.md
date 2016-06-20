rsoprivatecloud/pubscripts
==========================

Intent
------

This repository/role is intended to collect all scripts around
OpenStack administration with RPC
Currently it is structured in a Ansible galaxy style role but does not support Ansible yet.

Operational scripts
-------------------

All RPC OpenStack supports scripts are currently running outside of ansible and are stored 
inside the files folder.
Those scripts will be converted over time into individual Ansible tasks.

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

This role expect to be installed/applied on a working RPC OpenStack environment which does run a
supported product lifecycle.


Role Variables
--------------

None

Dependencies
------------

None

Playbook integration
----------------

    - hosts: all
      roles:
         - { role: pubscripts }

License
-------

The content in this repository is provided on a "as-is" bases,
Rackspace is not liable for any content inside this repoisitory
or environment related issue as a result of using or applying
this role outside of Rackspace manged hosts.


Author Information
------------------

Rackspace Private Cloud - OpenStack
