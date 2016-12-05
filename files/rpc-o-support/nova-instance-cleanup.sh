#!/bin/bash

test -f /root/.my.cnf || exit 1
test -x "$(which mysql)" || exit 1

cat << EOF > /root/nova-instance-cleanup.sql
delete from nova.block_device_mapping where instance_uuid in ( select uuid from nova.instances where deleted > 0 );
delete from nova.instance_actions_events where action_id in ( select id from nova.instance_actions where instance_uuid in ( select uuid from nova.instances where deleted > 0 ));
delete from nova.instance_actions where instance_uuid in ( select uuid from nova.instances where deleted > 0 );
delete from nova.instance_info_caches where instance_uuid in ( select uuid from nova.instances where deleted > 0 );
delete from nova.instance_metadata where instance_uuid in ( select uuid from nova.instances where deleted > 0 );
delete from nova.instance_system_metadata where instance_uuid in ( select uuid from nova.instances where deleted > 0 );
delete from nova.instance_extra where instance_uuid in ( select uuid from nova.instances where deleted > 0 );
delete from nova.instance_faults where instance_uuid in ( select uuid from nova.instances where deleted > 0 );
delete from nova.migrations where instance_uuid in ( select uuid from nova.instances where deleted > 0 );
delete from nova.instances where deleted > 0;
EOF

mysql -BNe 'source /root/nova-instance-cleanup.sql;' | tee /root/nova-instance-cleanup.log
