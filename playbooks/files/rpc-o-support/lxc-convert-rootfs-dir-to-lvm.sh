#!/bin/bash

LANG=en_US.UTF-8

export VG=lxc
export LXCROOT=/var/lib/lxc
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export TMPMNT=/mnt/lxc-conversion

echo
echo "Current configuration"
echo "---------------------"
echo "LVM VG Name: $VG"
echo "LXC ROOT: $LXCROOT"
echo "Temporary Mount Point: $TMPMNT"
echo
echo "PLEASE ENSURE ~80GB AVAILABLE DISK SPACE WITHIN THE LVM VG BEFORE CONTINUING !"

if [ $( echo "$@" |grep i-know-what-i-do |wc -l ) -eq 0 ]; then
  echo "Please call execute $0 i-know-what-i-do"
  exit 1
fi

for i in $(seq 1 10); do
  echo "${i}/10 Press CTRL+C to stop"
  sleep 1
done


lxc-system-manage containers-stop

echo
for l in $(lxc-ls -1); do
  echo -n "Processing $l: "; size=5G
  case $l in
    *glance_*)
      size=12G
      ;;
    *repo_*)
      size=10G
      ;;
  esac

  #Checks
  test $(lvs |grep $l |wc -l) -gt 0 && lvmexist=1 || lvmexist=0
  test $(grep "lxc.rootfs.backend = dir" $LXCROOT/$l/config |wc -l) -gt 0 && lxcdir=1 || lxcdir=0

  #Execution
  echo -n "Size: $size LVM Existing: $lvmexist Rootfs-on-dir: $lxcdir"

  echo
  if [ $lvmexist -eq 0 ]; then
    echo "  Creating LVM $VG/${l}: "
    lvcreate -L $size -n $l $VG >/dev/null 2>&1; rc=$?
    test $rc -eq 0 && echo -n "OK" || echo -n "FAILED"
    test $rc -gt 0 && exit 1
  fi

  if [ $lxcdir -eq 1 ]; then
    echo -n "  Checking for existing filesystem: "
    dumpe2fs -h /dev/$VG/$l >/dev/null 2>&1; rc=$?
    test $rc -eq 0 && echo -n "OK. Skipping creation." || echo -n "creating ext4:"
    test $rc -eq 1 && mkfs.ext4 /dev/$VG/$l >/dev/null 2>&1 && rc=$? || rc=1
    test $rc -eq 0 && echo -n "OK"

    echo
    echo -n "  Mounting ext4 filesystem to ${TMPMNT}: "
    test -d $TMPMNT || mkdir -p $TMPMNT >/dev/null 2>&1
    mount /dev/$VG/$l $TMPMNT >/dev/null 2>&1; rc=$?
    test $rc -eq 0 && echo -n "OK" || echo -n "FAILED"
    test $rc -gt 1 && exit 1

    echo
    echo -n "  Copying lxc rootfs to $TMPMNT: "
    pushd $LXCROOT/$l/rootfs >/dev/null
      tar -cf - *| ( cd ${TMPMNT} && tar xf - ); rc1=$?
      test $rc -eq 0 && echo -n "OK" || echo -n "FAILED"
      umount -f ${TMPMNT} >/dev/null 2>&1; rc2=$?
      test $rc2 -eq 1 && echo "  Unmount failed. Skipping" && continue

      test $rc1 -eq 0 && mv $LXCROOT/$l/rootfs $LXCROOT/$l/rootfs.moved-to-lvm
      test $rc1 -eq 0 && echo -n "  Remove $LXCROOT/$l/rootfs.moved-to-lvm once containers have been verified for function."

      echo
      echo -n "  Update LXC config to LVM: "
      sed -i -e 's/lxc.rootfs.backend =.*/lxc.rootfs.backend = lvm/g' -e "s/lxc.rootfs = .*/lxc.rootfs = \/dev\/$VG\/$l/g" $LXCROOT/$l/config >/dev/null 2>&1; rc=$?
      test $rc -eq 0 && echo -n "OK" || echo -n "FAILED"
      test $rc -eq 1 && continue

    popd
  else
    echo "  Skipping as lxc.rootfs.backend is not dir"
    continue
  fi
done

echo
echo "Please start containers with \"lxc-system-manage containers-start\" once you verified correct move."
