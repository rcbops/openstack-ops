#!/bin/bash

test -f /root/.my.cnf || exit 1
test -x "$(which mysql)" || exit 1

cat << EOF > /root/nova-instance-cleanup.sql
DELETE FROM nova.block_device_mapping WHERE instance_uuid IN ( SELECT uuid FROM nova.instances WHERE deleted > 0 );
DELETE FROM nova.instance_actions_events WHERE action_id IN ( SELECT id FROM nova.instance_actions WHERE instance_uuid IN ( SELECT uuid FROM nova.instances WHERE deleted > 0 ));
DELETE FROM nova.instance_actions WHERE instance_uuid IN ( SELECT uuid FROM nova.instances WHERE deleted > 0 );
DELETE FROM nova.instance_info_caches WHERE instance_uuid IN ( SELECT uuid FROM nova.instances WHERE deleted > 0 );
DELETE FROM nova.instance_metadata WHERE instance_uuid IN ( SELECT uuid FROM nova.instances WHERE deleted > 0 );
DELETE FROM nova.instance_system_metadata WHERE instance_uuid IN ( SELECT uuid FROM nova.instances WHERE deleted > 0 );
DELETE FROM nova.instance_extra WHERE instance_uuid IN ( SELECT uuid FROM nova.instances WHERE deleted > 0 );
DELETE FROM nova.instance_faults WHERE instance_uuid IN ( SELECT uuid FROM nova.instances WHERE deleted > 0 );
DELETE FROM nova.migrations WHERE instance_uuid IN ( SELECT uuid FROM nova.instances WHERE deleted > 0 );
DELETE FROM nova.virtual_interfaces WHERE instance_uuid IN ( SELECT uuid FROM nova.instances WHERE deleted > 0 );
DELETE FROM nova.instances WHERE deleted > 0;
EOF

mysql -BNe 'source /root/nova-instance-cleanup.sql;' | tee /root/nova-instance-cleanup.log
