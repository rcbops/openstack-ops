#!/bin/bash
#
# Test end-to-end VLAN connectivity between this and other nodes.
#
# -v VLANID -i INTERFACE -s SOURCEIP -d DESTIP -l LISTFILE
#
#
#  Given a list of IPs in LISTFILE, this script will create a 
#    VLANID-tagged interface with SOURCEIP assigned, then SSH to 
#    each IP, configure a VLANID-tagged interface with DESTIP
#    assigned, then ping between.  Addresses are removed and
#    VLANID-tagged interfaces are destroyed afterwards.
#
#   *** Script assumes /24 network ***
#
#  Questions, Comments -> Aaron Segura / RPC
#

export CLEAN=0
function cleanup() {
  [ $CLEAN -ne 0 ] && return || CLEAN=1
  echo "# Running cleanup..."

  for ip in `cat $LIST`; do 
    echo -n "  $ip: "
    ssh $ip "grep ${NIC}.${VLANID} /proc/net/dev )" > /dev/null 2>&1
    [ $? -gt 0 ] && ssh $ip "vconfig rem ${NIC}.${VLANID}" > /dev/null 2>&1
    if [ $? -gt 0 ]; then
      echo "# Unable to remove tagged interface ${NIC}.${VLANID}"
    else
      echo "OK"
    fi
  done
  vconfig rem ${NIC}.${VLANID} > /dev/null 2>&1
  if [ $? -gt 0 ]; then
    echo "# Unable to remove local tagged interface ${NIC}.${VLANID}"
  fi
  echo
}

function parse_args() {
  while getopts "v:i:s:d:l:" OPT; do
    case "$OPT" in
      "v")
        if [ ! "$( echo $OPTARG | egrep '^[0-9]{1,4}$' )" ]; then
          echo "Invalid VLAN ID: $OPTARG"
          exit 1
        fi
        if [ $OPTARG -lt 1 -o $OPTARG -gt 4095 ]; then
          echo "Invalid VLAN ID: $OPTARG"
          exit 1
        fi
        VLANID=$OPTARG
      ;;

      "i")
        if [ ! "$( cat /proc/net/dev | awk -F: '/:/ {print $1}' | tr -d ' ' | egrep "^$OPTARG$" )" ]; then
          echo "Invalid Interface, Does not Exist: $OPTARG"
          exit 1
        fi
        NIC=$OPTARG
      ;;

      "s")
        if [ ! "$( echo $OPTARG | awk -F. '$1 >= 1 && $1 < 224 && $2 >= 0 && $2 <= 255 && $3 >= 0 && $3 <= 255 && $4 >= 0 && $4 < 255 { print $0 }')" ]; then
          echo "Invalid Source IP: $OPTARG"
          exit 1
        fi
        SRCIP=$OPTARG
      ;;

      "d")
        if [ ! "$( echo $OPTARG | awk -F. '$1 >= 1 && $1 < 224 && $2 >= 0 && $2 <= 255 && $3 >= 0 && $3 <= 255 && $4 >= 0 && $4 < 255 { print $0 }')" ]; then
          echo "Invalid Destination IP: $OPTARG"
          exit 1
        fi
        DSTIP=$OPTARG
      ;;

      "l")
        if [ ! -s $OPTARG ]; then
          echo "Invalid file: $OPTARG"
          exit 1
        fi

        echo -n "# Parsing $OPTARG for errors..."
        exec 7< $OPTARG
        while read ip <&7; do 
          if [ ! "$( echo $ip | awk -F. '$1 >= 1 && $1 < 224 && $2 >= 0 && $2 <= 255 && $3 >= 0 && $3 <= 255 && $4 >= 0 && $4 < 255 { print $0 }')" ]; then
            echo -e "\nInvalid Mgmt IP in $OPTARG: $ip"
            exit 1
          fi
        done
        echo "Ok!"
        LIST=$OPTARG
      ;;
    esac
  done
}

function check_prereqs() {
  echo "# Checking remote servers for prerequisite packages..."
  for ip in `cat $LIST`; do 
    ssh $ip 'dpkg -l vlan  | grep ^ii > /dev/null 2>&1'
    if [ $? -eq 1 ]; then
      echo "#   Installing 'vlan' package on $ip"
      ssh $ip 'apt-get install -y vlan > /dev/null 2>&1'
      if [ $? -gt 0 ]; then
        echo "!  Unable to install 'vlan' package.  Please install before proceeding."
        exit 1
      fi
    fi
  done

  dpkg -l vlan | grep ^ii > /dev/null 2>&1
  if [ $? -gt 0 ]; then
    echo "# Installing 'vlan' package locally..."
    apt-get install -y vlan > /dev/null 2>&1
    if [ $? -gt 0 ]; then
      echo "!   Unable to install 'vlan' package locally.  Please install before proceeding."
      exit 1
    fi
  fi
}

function do_work() {
  echo "# Configuring local tagged interface ${NIC}.${VLANID}"
  vconfig add $NIC $VLANID > /dev/null 2>&1
  if [ $? -gt 0 ]; then
    echo "!!! Unable to create local tagged interface.  Giving up."
    exit 1
  else
    ip a a ${SRCIP}/24 dev ${NIC}.${VLANID} > /dev/null 2>&1
    ip l set up ${NIC}.${VLANID}
    if [ $? -gt 0 ]; then
      echo "!!! Unable to add ${SRCIP} to ${NIC}${VLANID}.  Giving up."
      exit 1
    fi
  fi

  echo "# Testing Remote Systems..."
  echo
  for ip in `cat $LIST`; do 
    echo -n "  $ip: "
    ssh $ip vconfig add $NIC $VLANID > /dev/null 2>&1
    if [ $? -gt 0 ]; then
      echo "Unable to create VLAN tagged interface"
      exit 1
    else
      ssh $ip ip a a ${DSTIP}/24 dev ${NIC}.${VLANID}
      ssh $ip ip l set up ${NIC}.${VLANID}
      if [ $? -gt 0 ]; then
        echo "Unable to put address on tagged interface: $R"
        exit 1
      else
        ssh $ip ping -c3 -i0.25 $SRCIP > /dev/null 2>&1
        if [ $? -gt 0 ]; then
          echo "FAILED"
        else
          echo "SUCCESS"
        fi
      fi
    fi
    ssh $ip ip a d ${DSTIP}/24 dev ${NIC}.${VLANID} > /dev/null 2>&1
    if [ $? -gt 0 ]; then
      echo "Unable to remove $DSTIP from ${NIC}.${VLANID} on $ip.  Stopping."
      exit 1
    fi
  done
  echo
}

#============================================================================#
VLANID=
NIC=
SRCIP=
DSTIP=
LIST=
export VLANID NIC SRCIP DSTIP LIST

#============================================================================#
parse_args "$@"
trap cleanup SIGINT SIGTERM SIGHUP EXIT
check_prereqs
do_work

#============================================================================#
