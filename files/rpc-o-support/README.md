*** If you add something to this repo, document it below ***

escape.py
---------

See documentation @ [escape.md](https://github.com/rsoprivatecloud/openstack-ops/blob/master/files/rpc-o-support/escape.md)

pccommon.sh
-----------
`$ source ./pccommon.sh`

Provides the following functions for private cloud admins:

  - ix() - Quickly post things to ix.io
    * echo things into this and it will return a URL for sharing

  - rpc-hypervisor-vms() - Display all hypervisors and associated instances
    * Pulls information from MySQL, shows a list of VMs along with their associated resources

  - rpc-hypervisor-free() - Display free resources on each Hypervisor
    * Pulls information from MySQL, displays free resources per Hypervisor

  - rpc-filter() - Replace stinky UUIDs with refreshing descriptive names inline
    * echo things into this and it will replace any known UUIDs with descriptive names for the following items:
        * Networks
        * Flavors
        * Instances
        * Images
        * Users
        * Tenants

  - rpc-iscsi-generate-sessions() - Generate list of commands to re-initiate currently open iscsi sessions
    * Will create a list of iscsiadm commands based on the currently-mounted iscsi targets that will re-create all current mounts.

  - rpc-common-errors-scan() - Pretty much what it sounds like
    * This is a piece of shit and probably should just be removed

  - rpc-bondflip() - Change given bondX to backup NIC
    * Will flip a given bond interface; you don't have to know which interfaces are in the bond.

  - rpc-environment-scan() - Update list of internal filters
    * Updates the list of filters used by rpc-filter(), run automatically on load.

  - rpc-os-version-check() - Are we running latest availble version?
    * Checks apt-cache policy to see if we are running latest version of nova-common.  Only for v4 environments.

  - rpc-instance-test-networking() - Test instance networking.
    * Same checks performed by rpc-instance-per-* functions.  Can be used on arbitrary instances.

  - rpc-instance-per-network() - Per network, spin up an instance on given hypervisor, ping, and tear down
    * Spins up an instance per network on the given hypervisor, waits for them to boot, then runs rpc-instance-test-networking() on them

  - rpc-instance-per-network-per-hypervisor() - Per network, spin up an instance on each hypervisor, ping, and tear down
    * Spins up an instance on each hypervisor, per network, waits for them to boot, then runs rpc-instance-test-networking() on them.

  - rpc-sg-rules() - Makes security groups easier to read.  Pass it a Security Group ID (not name)
    * Pulls from MySQL

  - rpc-image-check() - Shows all running instances and the state of their base images (active/deleted)
    * Checks to make sure all running instances still have a backing image in glance

  - rpc-update-pccommon() - Grabs the latest version of pccommon.sh if there is one
    * Self explanitory

  - swap-usage() - Shows current usage of swap memory, by process
    * Yep, this one, too.


On load, this script will scan the environment for various openstack things in order to pre-populate the rpc 
filters.  This process takes a few seconds to complete, and can be skipped by setting S=1 in your environment:

    $ S=1 source ./pccommon.sh

** the rpc-sg-rules() function will not work if you skip the scan **

You can also suppress all messages entirely by adding Q=1
```
    $ Q=1 source ./pccommon.sh
```
They can be used in combination.  Both of these values are automatically assumed if the script detects that 
you are running via remote execution (eg, $ ssh 10.240.0.200 '. ./pccommon.sh; rpc-bondflip bond1')


swift-datacrusher.yml
---------------------

Play to tear down Swift data nodes with reformatting all labeled swift disks

WARNING: This playbook will stop the swift services on the swift_obj server group and unmount/reformat/remount the XFS disks
         mounted under /srv/node. If there is no disk mounted, the play will not execute any tasks.

                               !!!!! DATA WILL BE DELETED WHEN RUNNING THIS PLAY !!!!!

Overrides:
 - xfs_inode_size defaults to 1024 and is used for the -i parameter with mkfs.xfs
 - xfs_mount_options default to rw,noatime,nodiratime,nobarrier,logbufs=8,noquota
 - xfs_format_options defaults to ""
 - exclude_drive_labels defaults to ""
 - exclude_drive_labels_format_option to ""

Run it:
`openstack-ansible swift-datacrusher.yml`

Options can be overridden with passing these arguments to openstack-ansible:
`openstack-ansible swift-datacrusher.yml -e xfs_inode_size=256 -e xfs_format_options='-linternal' -e exclude_drive_labels="disk1,disk2" -e exclude_drive_labels_format_option="disk3,disk4"`


rebuild-rabbitmq-container.sh
-----------------------------

This script will rebuilt RabbitMQ and its containers from scratch.
All current RabbitMQ messages will be lost executing this script.
Hence it should only be used in sitations where a complete rebuild
is indented, e.g (QC, complete site failures) etc.

WARNING: THIS SCRIPT WILL DESTROY AND REBUILD THE RABBITMQ CONTAINERS.
         IT SHOULD ONLY BE USED IN DEV/TEST ENVIRONMENTS OR EXTREME PRODUCTION
         OUTAGES WHERE NO OTHER RECOVERY IS POSSIBLE AND THE CUSTOMER ACKNOWLEDGED
         THAT HE IS OK WITH LOOSING POSSIBLE RABBITMQ MESSAGES!

```
$ ./rebuild-rabbitmq-container.sh iknowwhatido=1
```
