#!/bin/bash

test -f /root/.my.cnf || exit 1
test -x "$(which mysql)" || exit 1

cat << EOF > /root/nova-instance-cleanup.sql
USE nova;

DELETE FROM nova.block_device_mapping WHERE instance_uuid IN ( SELECT uuid FROM nova.instances WHERE deleted > 0 );
DELETE FROM nova.instance_actions_events WHERE action_id IN ( SELECT id FROM nova.instance_actions WHERE instance_uuid IN ( SELECT uuid FROM nova.instances WHERE deleted > 0 ));
DELETE FROM nova.instance_actions WHERE instance_uuid IN ( SELECT uuid FROM nova.instances WHERE deleted > 0 );
DELETE FROM nova.instance_info_caches WHERE instance_uuid IN ( SELECT uuid FROM nova.instances WHERE deleted > 0 );
DELETE FROM nova.instance_metadata WHERE instance_uuid IN ( SELECT uuid FROM nova.instances WHERE deleted > 0 );
DELETE FROM nova.instance_system_metadata WHERE instance_uuid IN ( SELECT uuid FROM nova.instances WHERE deleted > 0 );
DELETE FROM nova.instance_extra WHERE instance_uuid IN ( SELECT uuid FROM nova.instances WHERE deleted > 0 );
DELETE FROM nova.instance_faults WHERE instance_uuid IN ( SELECT uuid FROM nova.instances WHERE deleted > 0 );
DELETE FROM nova.migrations WHERE instance_uuid IN ( SELECT uuid FROM nova.instances WHERE deleted > 0 );

DROP PROCEDURE IF EXISTS NewtonVifCleanup;
DELIMITER $$

CREATE PROCEDURE NewtonVifCleanup(
    OUT nova_vif_table_exists BOOL)
BEGIN
    SELECT COUNT(*) > 0 as BOOL FROM information_schema.TABLES
      WHERE TABLE_NAME = 'virtual_interfaces'
      AND TABLE_SCHEMA LIKE 'nova%' INTO nova_vif_table_exists;

    IF (nova_vif_table_exists) THEN
      DELETE FROM nova.virtual_interfaces WHERE instance_uuid IN ( SELECT uuid FROM nova.instances WHERE deleted > 0 );
    END IF;
END$$

DELIMITER ;

CALL NewtonVifCleanup(@nova_vif_table_exists);

DELETE FROM nova.instances WHERE deleted > 0;

DROP PROCEDURE NewtonVifCleanup;
EOF

mysql -BNe 'source /root/nova-instance-cleanup.sql;' | tee /root/nova-instance-cleanup.log
