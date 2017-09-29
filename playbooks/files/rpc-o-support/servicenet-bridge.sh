#! /bin/sh
### BEGIN INIT INFO
# Provides:   servicenet-bridge
# Required-Start:
# Required-Stop:    reboot
# X-Stop-After:
# Default-Start:    2 3 4 5
# Default-Stop:     0 1 6
# Short-Description: Set up servicenet bridging to allow instance access to servicenet
# Description:
### END INIT INFO

PATH=/sbin:/bin:/usr/bin/
DEFAULTS=/etc/default/servicenet-bridge

. /lib/lsb/init-functions

[ -r $DEFAULTS ] && . $DEFAULTS

if [ ! "$SNET_INTERFACE" ]; then
  echo "Please set SNET_INTERFACE in $DEFAULTS"
  exit 3
fi

if [ ! "$SNET_ADDRSPACE" ]; then
  echo "Please set SNET_ADDRSPACE in $DEFAULTS"
  exit 3
fi


set_up_all_the_things () {
  log_action_msg "Setting up Servicenet Bridge"

  # Grab live ServiceNet configuration from interface
  SNET_CIDR=`ip a sh $SNET_INTERFACE | grep -Po 'inet [0-9\./]+? ' | cut -d\  -f2`
  SNET_ROUTE=`ip r list | grep $SNET_INTERFACE | egrep -o 'via [0-9\.]+.'`

  # Swap out the .0 for a .1 to create the gateway address.
  TENANT_GATEWAY=`echo $SNET_ADDRSPACE | sed 's/\.0\//.1\//'`

  # Create veth pair
  ip link add dev veth-snet-a type veth peer name veth-snet-z
  ip link set veth-snet-a up

  # Create ServicNet Namespace
  ip netns add ns-servicenet

  # Move Z into Namespace
  ip link set veth-snet-z netns ns-servicenet
  ip netns exec ns-servicenet ip link set veth-snet-z up

  # Move ServiceNet interface into Namespace
  ip link set $SNET_INTERFACE netns ns-servicenet
  ip netns exec ns-servicenet ip link set $SNET_INTERFACE up
  ip netns exec ns-servicenet ip addr a $SNET_CIDR dev $SNET_INTERFACE
  ip netns exec ns-servicenet ip link set lo up
  ip netns exec ns-servicenet ip route add default $SNET_ROUTE

  # Create br-snet inside Namespace
  ip netns exec ns-servicenet brctl addbr br-snet
  ip netns exec ns-servicenet ip addr a $TENANT_GATEWAY dev br-snet
  ip netns exec ns-servicenet ip link set br-snet up

  # Connect Z to br-snet
  ip netns exec ns-servicenet brctl addif br-snet veth-snet-z

  # Add MASQ Rule
  ip netns exec ns-servicenet iptables -t nat -A POSTROUTING -s $SNET_ADDRSPACE \! -d $SNET_ADDRSPACE -j MASQUERADE
  
  log_action_msg "Done!"
}

destroy_all_the_things () {

  log_action_msg "Shutting down Servicenet Bridge"

  if [ "$( ip netns | grep ns-servicenet )" ]; then
    ip netns delete ns-servicenet
    ifup $SNET_INTERFACE > /dev/null 2>&1
    log_action_msg "Done"
  else
    log_action_msg "Namespace does not exist.  Exiting with no action."
  fi

}

status_all_the_things () {
  ip netns | grep ns-servicenet > /dev/null 2>&1  
  [ $? -eq 0 ] && log_action_msg "[GOOD] Namespace Exists" || log_action_msg "[BAD] No Namespace" 

  ip netns exec ns-servicenet ip l sh $SNET_INTERFACE > /dev/null 2>&1
  [ $? -eq 0 ] && log_action_msg "[GOOD] Servicenet Interface is inside the Namespace"  || log_action_msg "[BAD] Servicenet Interface not found inside of Namespace"

  ip netns exec ns-servicenet brctl show 2> /dev/null | grep br-snet > /dev/null 2>&1
  [ $? -eq 0 ] && log_action_msg "[GOOD] br-snet created inside Namespace" || log_action_msg "[BAD] br-snet missing from Namespace"

  ip netns exec ns-servicenet brctl show br-snet 2> /dev/null | grep veth-snet-z > /dev/null 2>&1
  [ $? -eq 0 ] && log_action_msg "[GOOD] veth-snet-z in br-snet" || log_action_msg "[BAD] veth-snet-z missing from br-snet"

  ip netns exec ns-servicenet iptables -L -t nat -n 2> /dev/null | grep "MASQ.*$SNET_ADDRSPACE" > /dev/null 2>&1
  [ $? -eq 0 ] && log_action_msg "[GOOD] IPTables Masquerade rule configured." || log_action_msg "[BAD] IPTables Masquerade rule MISSING"

}

case "$1" in
  start)
    [ ! "$( ip netns | grep ns-servicenet)" ] && set_up_all_the_things || log_action_msg "ns-servicenet already exists.  Exiting with no action."
  ;;
  restart|reload|force-reload)
    destroy_all_the_things
    sleep 1
    set_up_all_the_things
  ;;

  stop)
    destroy_all_the_things
  ;;

  status)
    status_all_the_things
  ;;

  *)
    echo "Usage: $0 start|restart|stop" >&2
    exit 3
  ;;
esac
exit 0
