#!/bin/bash

# Copyright 2019-Present, Rackspace US, Inc.
#
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

# Parameters
#  Number of threads: 20 by default. The CPU benchmarks will be run with 1, the number threads desired and 2x the desired threads
#  Number of test iterations: 10 by default
#  Device to use for FIO: /dev/lxc/fio by default. Fio is instructed to use direct IO to a block device to remove variability caused from filesystems/caches
#  IO test duration: 180 by default

LANG=en_US.UTF-8

THREADS=${1:-20}
ITER=${2:-10}
WAIT_INBETWEEN_TESTS=60
IO_BLK_DEV=${3:-/dev/lxc/fio}
IO_BLK_DURATION=${4:-180}

test -x "$(which sysbench)" || apt install -y sysbench fio > /dev/null 2>&1
SB="$(which sysbench)"
FIO="$(which fio)"


# Check for version 1.0 on sysbench
if [ -x "$(which sysbench)" ]; then
  # Try to upgrade sysbench
  apt install -y sysbench fio > /dev/null 2>&1

  if [ "$($SB --version | cut -d " " -f2 | tr -d '.')" -lt 1000 ]; then
    echo "Sysbench is too old, version 1.0 is required."
    echo "Install the RPC first in order to be able to install sysbench in the required version."
    exit 1
  fi
fi

function cpu {
  local threads=$1
  local maxprime=200000

  echo -n "$(date +'%s');CPU (Max Prime $maxprime);"

  for i in 1 $threads $(($threads*2)); do
    OPTS="--test=cpu --cpu-max-prime=$maxprime --threads=$i run"
    $SB $OPTS 2>/dev/null |awk -F 'events per second: ' '/events per second/ {printf "%.1f",$2}'
    echo -n ";"
  done

  echo
}

function memory {
  local threads=$1
  local pg=$(getconf PAGE_SIZE)

  echo -n "$(date +'%s');RAM (Page Size $pg);"

  for i in 1 $threads $(($threads*2)); do
    OPTS="--test=memory --threads=$i --time=30 --memory-block-size=$pg --memory-scope=global run"
    $SB $OPTS 2>/dev/null |awk -F 'transferred \\(' '/ transferred.*sec/ {printf "%.1f",$2}'
    echo -n ";"
  done

  echo
}

function fio {
  local fiotests="randwrite:16k randread:16k write:1024k read:1024k"

  if [ ! -e $IO_BLK_DEV ]; then
    echo "Device IO_BLK_DEV not found for fio tests"
    return
  fi

  for t in $fiotests; do
    ftest=$(echo $t |cut -d ":" -f1)
    fblk=$(echo $t |cut -d ":" -f2)

    echo -n "$(date +'%s');fio $ftest ($fblk block size);"
      OPTS="--filename=$IO_BLK_DEV --name $ftest --ioengine=libaio --direct=1 --rw=$ftest --bs=$fblk --time_based --runtime=$IO_BLK_DURATION"
      OPTS2=""
      case $ftest in
        rand*)
          OPTS2="--size=1G --numjobs=16 --group_reporting --norandommap"
        ;;

        write|read)
          OPTS2="--randrepeat=0 --iodepth=8"
        ;;
      esac

      $FIO $OPTS $OPTS2 2>/dev/null |awk -F 'iops=' '/iops=/ {printf "%d",$2}'
      echo -n ";"
    echo
  done
}


echo "Timestamp;Benchmark;1 Thread Performance;$THREADS Thread Performance;$(($THREADS*2)) Thread Performance;"
for i in $(seq 1 $ITER); do
  cpu $THREADS
  memory $THREADS
  sleep $WAIT_INBETWEEN_TESTS
done

echo
echo "Timestamp;Benchmark; IOPS"
for i in $(seq 1 $ITER); do
  fio
  sleep $WAIT_INBETWEEN_TESTS
done
