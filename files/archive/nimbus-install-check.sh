#!/bin/bash

pgrep -f openstack-probes.pl > /dev/null

if [ ! -e /opt/nimsoft/probes ]; then
	    echo $(hostname) - Nimbus not installed!;
	    exit 1
fi

if [ $? == 1 ]; then 
    echo $(hostname) - Openstack probes not running!
    exit 1
fi

echo $(hostname) - Nimbus OK!
exit 0
