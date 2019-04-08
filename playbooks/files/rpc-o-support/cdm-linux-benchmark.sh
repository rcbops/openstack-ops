#!/bin/bash

LANG=en_US.UTF-8

THREADS=${1:-16}
ITER=${2:-10}
WAIT_INBETWEEN_TESTS=60
IO_BLK_DEV=${3:-/dev/lxc/fio}
IO_BLK_DURATION=${4:-180}

test -x $(which sysbench) || apt install -y sysbench fio > /dev/null 2>&1
SB="$(which sysbench)"
FIO="$(which fio)"

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
