#!/bin/bash

# Purpose: This script performs a quick check to determine if udev and devicemapper devices are misaligned as a result of LP bug 1436999
#   [1] https://bugs.launchpad.net/openstack-ansible/+bug/1436999

cd /dev/mapper || exit 1

# Find the volume group where cinder volumes are stored
if [ -e /etc/cinder/cinder.conf ]; then
    vg=$(grep '^volume_group' /etc/cinder/cinder.conf | sed 's/volume_group=//')
else
    echo "Error: unable to open /etc/cinder/cinder.conf"
    exit 1
fi

for c in $( ls ${vg}-* ); do
  file=$( ls -l /dev/mapper/$c |awk '{print $6}' |egrep '[0-9]+' )
  test -z "$file" && file=$( ls -l /dev/mapper/$c |awk -F 'dm-' '{print $2}' |egrep '[0-9]+' )
  dm=$( dmsetup ls |egrep "$c\s+" |cut -d ':' -f2 |egrep -o '[0-9]+' )
  test "${file}" != "${dm}"  && echo "$c is bad minor ${file} does not match ${dm}" || echo "$c is ok minor ${file} does match ${dm}"
done
