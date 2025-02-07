#!/usr/bin/env bash

# Copyright 2020-Present, Rackspace US, Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

if [ $(id -u) -ne 0 ]; then
  echo "Run scripts with sudo as partitioning tools require elevated access"
  exit 1
fi

if [ ! -d "/opt/image-builder/bin" ]; then
  apt -y install qemu uuid-runtime curl kpartx qemu-utils squashfs-tools
  virtualenv /opt/image-builder
  /opt/image-builder/bin/pip install diskimage-builder==3.37.0 --isolated
fi

. /opt/image-builder/bin/activate


DIST=${1:-jammy}
export OUTPUT_DIR=~/ironic-images

#### Disk Image Builder variables (DIB)
export ELEMENTS_PATH=/opt/openstack-ops/dib-elements 

export FS_TYPE=ext4
export LVM=false
export COMPRESS_IMAGE='1'
export DIB_MODPROBE_BLACKLIST='usb-storage cramfs freevxfs jffs2 hfs hfsplus squashfs udf bluetooth'
export DIB_BOOTLOADER_DEFAULT_CMDLINE='rdblacklist=bfa,lpfc nofb nomodeset vga=normal console=tty0 console=ttyS1,115200n8 audit=1 audit_backlog_limit=8192'
export DIB_CLOUD_INIT_DATASOURCES="Ec2, ConfigDrive, OpenStack"

#### Disk Image Builder variables (DIB)

case $DIST in
  bionic)
    export DISTRO_NAME=ubuntu
    export DIB_RELEASE=bionic
    export DIB_BOOTLOADER_DEFAULT_CMDLINE+=" biosdevname=1 net.ifnames=0"
  ;;

  jammy)
    export DISTRO_NAME=ubuntu
    export DIB_RELEASE=jammy
  ;;

  jammy-lvm)
    export DISTRO_NAME=ubuntu
    export DIB_RELEASE=jammy
    export LVM=true
  ;;
  
  centos9)
    export DISTRO_NAME=centos
    export DIB_RELEASE=9-stream
  ;;

  *)
    export DISTRO_NAME=ubuntu
    export DIB_RELEASE=jammy
  ;;
esac


IMG_NAME=${DISTRO_NAME}-${DIB_RELEASE}-${FS_TYPE}-metal-efi

echo "Building ${DISTRO_NAME}-${DIB_RELEASE} with ${OUTPUT_DIR}/${IMG_NAME}"

#### LVM Testing
if $LVM; then

  export DIB_IMAGE_SIZE='299G'
  export DIB_BLOCK_DEVICE_CONFIG='''
- local_loop:
    name: image0

- partitioning:
    base: image0
    label: gpt
    partitions:
      - name: BSP
        type: 'EF02'
        size: 8MiB
      - name: ESP
        type: 'EF00'
        size: 550MiB
        mkfs:
        type: vfat
        mount:
          mount_point: /boot/efi
          fstab:
            options: "defaults"
            fsck-passno: 2
      - name: boot
        size: 1G
        flags: [ "primary","boot" ]
        mkfs:
          name: fs_boot
          type: ext4
          mount:
            mount_point: /boot
            fstab:
              options: "defaults"
              fck-passno: 1
      - name: "Linux LVM"
        type: 1F
        size: 100%
        flags: [ "primary" ]
- lvm:
    name: lvm
    pvs:
      - name: pv
        base: "Linux LVM"
        options: [ "--force" ]
    vgs:
      - name: vglocal00
        base: [ "pv" ]
        options: [ "--force" ]
    lvs:
      - name: lv_root
        base: vglocal00
        extents: 20%VG 
      - name: lv_roothome
        base: vglocal00
        extents: 10%VG 
      - name: lv_tmp
        base: vglocal00
        extents: 10%VG 
      - name: lv_var
        base: vglocal00
        extents: 20%VG
      - name: lv_log
        base: vglocal00
        extents: 10%VG
      - name: lv_opt
        base: vglocal00
        extents: 10%VG
      - name: lv_home
        base: vglocal00
        extents: 10%VG
- mkfs:
    name: fs_root
    base: lv_root
    type: ext4
    label: "img-rootfs"
    mount:
      mount_point: /
      fstab:
        options: "rw"
        fck-passno: 1
- mkfs:
    name: fs_tmp
    base: lv_tmp
    type: ext4
    mount:
      mount_point: /tmp
      fstab:
        options: "rw,nosuid,nodev,noexec,relatime"
- mkfs:
    name: fs_opt
    base: lv_opt
    type: ext4
    mount:
      mount_point: /opt
      fstab:
        options: "rw"
- mkfs:
    name: fs_var
    base: lv_var
    type: ext4
    mount:
      mount_point: /var
      fstab:
        options: "rw"
- mkfs:
    name: fs_log
    base: lv_log
    type: ext4
    mount:
      mount_point: /var/log
      fstab:
        options: "rw"
- mkfs:
    name: fs_roothome
    base: lv_roothome
    type: ext4
    mount:
      mount_point: /root
      fstab:
        options: "rw"
- mkfs:
    name: fs_home
    base: lv_home
    type: ext4
    mount:
      mount_point: /home
      fstab:
        options: "rw,nodev"
'''

echo $DIB_BLOCK_DEVICE_CONFIG

fi



### Build image
mkdir -p $OUTPUT_DIR

pushd $OUTPUT_DIR
  disk-image-create $DISTRO_NAME \
    $(test "$DISTRO_NAME" = "centos" && echo epel) \
    $(test "$DISTRO_NAME" = "ubuntu" && echo ubuntu-common) \
    $(test "$LVM" = true && echo block-device-efi-lvm || echo block-device-gpt) \
    disable-nouveau \
    cloud-init-datasources \
    vm \
    dhcp-all-interfaces \
    baremetal \
    grub2 \
    dynamic-login \
    rackspace -o $IMG_NAME
popd

if [ $? -eq 0 ]; then
  echo -e "\n\n\n"
  echo "File located at ${OUTPUT_DIR}/${IMG_NAME}"
fi

