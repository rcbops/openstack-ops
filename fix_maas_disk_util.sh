#!/bin/bash

#Courtesy James Dewey:
#
#05/05/2015 07:09 PM, James Dewey wrote:
#So due to the sweet bug Bjoern found with the playbooks picking up iscsi drives, you might end up with alarms that have been created for disk utilization for them.  
#Here’s the script I used to fix up ViaSat’s monitoring. Hopefully you don’t need it, but here’s saving you some time if you do.

#ignore case
shopt -s nocasematch

AUTH_TOKEN=163389b659824c61917d1f3e99282d4c

OLDIFS=$IFS
IFS=$(echo -en "\n")
for list in $(raxmon-entities-list --auth-token=$AUTH_TOKEN)
do
        while read entity
	do
		label=$(echo $list | awk "\$2 ~ /id=$entity/ {gsub(/label=/,\"\"); print \$3}")
	        echo "Checking entity $entity - $label"
        	while read alarm
	        do
			remove_alarm=0
	        	if [[ $label =~ cinder ]]
			then
				if [[ $alarm =~ percentage_disk_utilisation_sd[^(a|b)]-- ]]
				then
					remove_alarm=1
				fi
                	else
				if [[ $alarm =~ percentage_disk_utilisation_sd[^a]-- ]]
				then
					remove_alarm=1
				fi
 			fi

        		if [ $remove_alarm -eq 1 ]
	                then
                		alarm_id=$(echo $alarm | awk '{gsub(/id=/,""); gsub(/,/,""); print $2}')
                        	echo "Deleting $alarm"
                	        #raxmon-alarms-delete --auth-token=$AUTH_TOKEN --id=$alarm_id --entity-id=$entity
        	        fi
        	done < <(raxmon-alarms-list --auth-token=$AUTH_TOKEN --entity-id=$entity)
	done < <( echo $list | awk '$2 ~ /id/ {gsub(/id=/,""); print $2}' )
done

IFS=$(echo $OLDIFS)
