*** If you add something to this repo, document it below ***

pccommon.sh
-----------

$ source ./pccommon.sh 

Provides the following functions for private cloud admins:

     - ix() - Quickly post things to ix.io
     - rpc-hypervisor-vms() - Display all hypervisors and associated instances
     - rpc-hypervisor-free() - Display free resources on each Hypervisor, as reported by MySQL
     - rpc-filter() - Replace stinky UUIDs with refreshing descriptive names inline
     - rpc-iscsi-generate-sessions() - Generate list of commands to re-initiate currently open iscsi sessions
     - rpc-common-errors-scan() - Pretty much what it sounds like
     - rpc-bondflip() - Change given bondX to backup NIC
     - rpc-port-stats() - Show live interface usage by port
     - rpc-environment-scan() - Update list of internal filters
     - rpc-os-version-check() - Are we running latest available openstack versions?

On load, this script will scan the environment for various openstack things in order to pre-populate the rpc 
filters.  This process takes a few seconds to complete, and can be skipped by setting S=1 in your environment:

    $ S=1 source ./pccommon.sh

You can also suppress all messages entirely by adding Q=1

    $ Q=1 source ./pccommon.sh

They can be used in combination.  Both of these values are automatically assumed if the script detects that 
you are running via remote execution (eg, $ ssh 10.240.0.200 '. ./pccommon.sh; rpc-bondflip bond1')



rpchousecall.py
---------------

$ python ./rpchousecall.py

Will perform basic healthcheck of RPC environment:
  - Authenticate against all applicable endpoints
  - Import known good Ubuntu Image, download from Ubuntu, if necessary
  - Create a flavor
  - Create a cinder volume, if applicable
  - Create a network and subnet
  - Boot an instance using new flavor and image on new network
  - Ping the instance
  - Attach cinder volume, if applicable
  - Create snapshot
  - Detach cinder volume, if applicable
  - Destroy instance
  - Destroy network and subnet
  - Destroy snapshot
  - Destroy flavor
  - Destroy cinder volume
  - Test MySQL Replication
  - Verify Horizon Login Page

