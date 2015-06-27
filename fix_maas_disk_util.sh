#!/bin/bash

#Courtesy James Dewey:
#
#05/05/2015 07:09 PM, James Dewey wrote:
#So due to the sweet bug Bjoern found with the playbooks picking up iscsi drives, you might end up with alarms that have been created for disk utilization for them.  
#Here’s the script I used to fix up ViaSat’s monitoring. Hopefully you don’t need it, but here’s saving you some time if you do.


AUTH_TOKEN=163389b659824c61917d1f3e99282d4c

OLDIFS=$IFS
IFS=$(echo -en "\n")
for list in $(raxmon-entities-list --auth-token=$AUTH_TOKEN)
do
        while read entity
        do
                echo "Checking entity $entity"
                while read  alarm
                do
                        if [[ $alarm =~ percentage_disk_utilisation_sd[^a]--phx1comp ]]
                        then
                                alarm_id=$(echo $alarm | awk '{gsub(/id=/,""); gsub(/,/,""); print $2}')
                                echo "Deleting $alarm"
                                raxmon-alarms-delete --auth-token=$AUTH_TOKEN --id=$alarm_id --entity-id=$entity
                        fi
                done < <(raxmon-alarms-list --auth-token=$AUTH_TOKEN --entity-id=$entity)
        done < <(echo $list | awk '$2 ~ /id/ {gsub(/id=/,""); print $2}')

done

IFS=$(echo $OLDIFS)
