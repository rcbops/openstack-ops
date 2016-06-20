*** Welcome to the dying scripts folder ***

The scripts listed here are for historical reasons keept in this folder until the
the product, it was intended to be used for, completely was removed from operations like RPC4 (probably never dies) 

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


shelob.sh
---------

$ shelob.sh -v VLAN -i NIC -s SOURCEIP -d DESTIP -l LISTFILE

    SRCIP and DESTIP are optional.  They have defaults which can be overridden.

    - LISTFILE should contain IP addresses or hostnames of remote systems to test.
    - NIC is pretty self-explanatory.

    This script will configure a local VLAN-tagged interface, then connect remotely
    to each system listed in LISTFILE, configure another tagged interface, then ping
    across in order to definitively test connectivity.

    Script attempts to detect duplicate IP addresses so it doesn't stomp on others.

    It would be a REALLY good idea to set up SSH keys for root logins before running
      this script.

