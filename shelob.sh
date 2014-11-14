#!/bin/bash
#
# Test end-to-end VLAN connectivity between this and other nodes.
#
# -v VLANID -i INTERFACE [-s SOURCEIP] [-d DESTIP] -l LISTFILE
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
#============================================================================#
VLANID=
NIC=
SRCIP=192.168.231.102
DSTIP=192.168.231.103
LIST=
CLEAN=0
TOCLEAN=
export VLANID NIC SRCIP DSTIP LIST TOCLEAN CLEAN
#============================================================================#

function cleanup() {
  [ $CLEAN -ne 0 ] && return || CLEAN=1
  echo ""
  echo "# Running cleanup..."

  for ip in $TOCLEAN; do 
    if [ "$ip" != "local" ]; then
      ssh $ip "grep ${NIC}.${VLANID} /proc/net/dev" > /dev/null 2>&1
      if [ $? -eq 0 ]; then 
        ssh $ip "vconfig rem ${NIC}.${VLANID}" > /dev/null 2>&1
        if [ $? -gt 0 ]; then
          echo "# Unable to remove tagged interface ${NIC}.${VLANID} on $ip"
        fi
      fi
    else
      vconfig rem ${NIC}.${VLANID} > /dev/null 2>&1
      if [ $? -gt 0 ]; then
        echo "# Unable to remove local tagged interface ${NIC}.${VLANID}"
      fi
    fi
  done

  echo
}

function usage() {
  echo "`basename $0`, by Aaron Segura - Rackspace Private Cloud"
  echo ""
  echo "$ `basename $0` <-v VLAN> <-i NIC> <-l LISTFILE> [-s SOURCEIP] [-d DESTIP]"
  echo ""
  echo "SRCIP and DESTIP are optional.  They have defaults which can be overridden."
  echo ""
  echo "- LISTFILE should contain IP addresses of remote systems to test."
  echo "- SOURCEIP and DESTIP should be two unused addresses within the same network"
  echo "- NIC is pretty self-explanatory."
  echo ""
  echo "This script will configure a local VLAN-tagged interface, then connect remotely"
  echo " to each system listed in LISTFILE, configure another tagged interface, then ping"
  echo " across in order to definitively test connectivity."
  exit 1
}


function parse_args() {
  while getopts ":hv:i:s:d:l:" OPT; do
    case "$OPT" in
      "h") usage ;;
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

  for pkg in vlan arping; do 
    dpkg -l $pkg | grep ^ii > /dev/null 2>&1
    if [ $? -gt 0 ]; then
      echo "# Installing $pkg package locally..."
      apt-get install -y $pkg > /dev/null 2>&1
      if [ $? -gt 0 ]; then
        echo "!   Unable to install $pkg locally.  Please install before proceeding."
        exit 1
      fi
    fi
  done
}

function configure_local_network() {

  echo "# Configuring local tagged interface ${NIC}.${VLANID}"
  vconfig add $NIC $VLANID > /dev/null 2>&1

  if [ $? -gt 0 ]; then
    echo "!!! Unable to create local tagged interface.  Giving up."
    exit 1
  else
    TOCLEAN="local"
    ip l set up ${NIC}.${VLANID}

    arping -c1 -S $DSTIP -p -i ${NIC}.${VLANID} $SRCIP > /dev/null 2>&1
    if [ $? -eq 0 ]; then
      echo ""
      echo "    Unable to use source IP $SRCIP, already in use!  Choose another."
      exit 1
    fi

    ip a a ${SRCIP}/24 dev ${NIC}.${VLANID} > /dev/null 2>&1
    if [ $? -gt 0 ]; then
      echo "!!! Unable to add ${SRCIP} to ${NIC}${VLANID}.  Giving up."
      exit 1
    fi
  fi

  arping -c1 -S $SRCIP -p -i ${NIC}.${VLANID} $DSTIP > /dev/null 2>&1
  if [ $? -eq 0 ]; then
    echo "Unable to use dest IP $DSTIP, already in use!  Choose another."
    exit 1
  fi

}

function do_work() {
  echo "# Testing Remote Systems..."
  echo
  for ip in `cat $LIST`; do 
    echo -n "  $ip: "
    ssh $ip vconfig add $NIC $VLANID > /dev/null 2>&1
    if [ $? -gt 0 ]; then
      echo "Unable to create VLAN tagged interface"
      continue
    else
      TOCLEAN="$ip ${TOCLEAN}"
      ssh $ip ip a a ${DSTIP}/24 dev ${NIC}.${VLANID}
      ssh $ip ip l set up ${NIC}.${VLANID}
      if [ $? -gt 0 ]; then
        echo "Unable to put address on tagged interface: $R"
        continue
      else
        ssh $ip ping -c3 -i0.25 -w1 $SRCIP > /dev/null 2>&1
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

if [ $UID -ne 0 ]; then
  echo "You must be root to use this script."
  exit 1
fi

parse_args "$@"

if [ ! "$VLANID" -o ! "$NIC" -o ! "$SRCIP" -o ! "$DSTIP" -o ! "$LIST" ]; then
  usage
fi

check_prereqs

trap cleanup SIGINT SIGTERM SIGHUP EXIT
configure_local_network
do_work

#============================================================================#
