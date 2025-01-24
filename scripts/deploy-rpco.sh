#!/usr/bin/env bash

# Copyright 2019-Present, Rackspace US, Inc.

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

# OSA Versions mapping
# 17.x = Queens
# 18.x = Rocky
# 19.x = Stein
# 20.x = Train
# 21.x = Ussuri
# 22.x = Victoria
# 23.x = Wallaby
# 24.x = Xena
# 25.x = Yoga
# 26.x = Zed

set -e

OSA_PYEXE=/opt/ansible-runtime/bin/python3
OSA_RELEASE="${OSA_RELEASE:-26.5.3}"
OSA_TOKEN_GEN="/opt/openstack-ansible/scripts/pw-token-gen.py"
OSA_INVENTORY="/opt/openstack-ansible/inventory/dynamic_inventory.py"
OSA_RUN_PLAY="${OSA_RUN_PLAY:-true}"
ANSIBLE_FORKS=24
SKIP_PROMPTS="${SKIP_PROMPTS:-false}"

case ${OSA_RELEASE%%\.*} in
  19)
    OSA_PYEXE=/opt/ansible-runtime/bin/python2
    RPCO_CONFIG_BRANCH="stable/stein"
    OSA_RELEASE="stein-em"
    ;;
  20)
    OSA_PYEXE=/opt/ansible-runtime/bin/python3
    RPCO_CONFIG_BRANCH="stable/train"
    OSA_RELEASE="train-em"
    ;;
  21)
    OSA_PYEXE=/opt/ansible-runtime/bin/python3
    RPCO_CONFIG_BRANCH="stable/ussuri"
    OSA_RELEASE="ussuri-em"
    ;;
  22)
    OSA_PYEXE=/opt/ansible-runtime/bin/python3
    RPCO_CONFIG_BRANCH="stable/victoria"
    OSA_RELEASE="victoria-em"
    ;;
  23)
    OSA_PYEXE=/opt/ansible-runtime/bin/python3
    RPCO_CONFIG_BRANCH="stable/wallaby"
    OSA_RELEASE="wallaby-em"
    ;;
  24)
    OSA_PYEXE=/opt/ansible-runtime/bin/python3
    RPCO_CONFIG_BRANCH="stable/xena"
    OSA_RELEASE="52f79cd337409bd245f4b023a73382b6b2dee5a2"
    ;;
  25)
    OSA_PYEXE=/opt/ansible-runtime/bin/python3
    RPCO_CONFIG_BRANCH="stable/yoga"
    OSA_RELEASE="70a48ec19df21ba6a4f902e21f0c087dcb5f652b"
    ;;
  26)
    OSA_PYEXE=/opt/ansible-runtime/bin/python3
    RPCO_CONFIG_BRANCH="stable/zed"
    OSA_RELEASE="26679e3b4e6950b20f7f6e99cbeb6f04328b4de2"
    ;;
  *)
    OSA_PYEXE=/opt/ansible-runtime/bin/python3
    RPCO_CONFIG_BRANCH="stable/zed"
    ;;

esac

test -f ~/.rackspace/datacenter && raxdc="$(cat ~/.rackspace/datacenter |tr '[:upper:]' '[:lower:]')"
test -d /opt/rpc-config && rpc_config_inplace=true || rpc_config_inplace=false
rm -rf ~/.pip/pip.conf 2>/dev/null

DEBIAN_FRONTEND=noninteractive apt-get -o "Dpkg::Options::=--force-confdef" -o "Dpkg::Options::=--force-confold" -qy install git 2>&1 > ~/ansible-base-package-install.log
if [ $? -gt 1 ]; then
  echo "*** Check for ansible errors at ~/ansible-base-package-install.log"
  exit 1
fi

OSA_ENV="${OSA_ENV:-$raxdc}"
if [ -z "$OSA_ENV" ]; then
  echo ""
  echo "Which environment do you deploy (Use an acronym like IAD3 for example) ?: "
  read OSA_ENV

  mkdir -p ~/.rackspace
  echo $OSA_ENV > ~/.rackspace/datacenter
fi

# Ensure DC prefix is set
OSA_ENV_LCASE="$(echo $OSA_ENV |tr '[:upper:]' '[:lower:]')"
echo ""
echo "*** Environment Name: $OSA_ENV_LCASE"
echo "*** OSA Release: $OSA_RELEASE"
echo "*** Deploy OSA: $OSA_RUN_PLAY"

if [ "${SKIP_PROMPTS}" != "true" ]; then
  echo "Is this correct (hit any key to continue) ?"
  read
fi

rm -rf /opt/openstack-ansible
test "$rpc_config_inplace" = true || git clone -o template -b ${RPCO_CONFIG_BRANCH} https://github.com/rpc-environments/RPCO-OSA-Template /opt/rpc-config
git clone https://opendev.org/openstack/openstack-ansible /opt/openstack-ansible && ( cd /opt/openstack-ansible && git checkout "$OSA_RELEASE" )

if [ "$rpc_config_inplace" = false ]; then
  cp -r /opt/rpc-config/global /opt/rpc-config/$OSA_ENV_LCASE
  test -d /opt/rpc-config/$OSA_ENV_LCASE && ln -sf /opt/rpc-config/$OSA_ENV_LCASE/configs/openstack /etc/openstack_deploy

  user_global_variables=""
  pushd /opt/rpc-config/global/configs/openstack
    for f in user*global*variables.yml; do
      user_global_variables+="$f "
    done
  popd

  pushd /etc/openstack_deploy
    for f in $user_global_variables; do
      echo "*** Linking $f to RPC default configuration"
      ln -sf ../../../global/configs/openstack/$f $f
    done
  popd

  if [ ! -f /opt/rpc-config/account.yml ]; then
    echo "*** Copying Runbook template into /opt/rpc-config"
    for f in README.md account.yml; do
      cp -f /opt/rpc-config/templates/$f /opt/rpc-config/
    done
  fi
else
  echo "*** /opt/rpc-config already present, skipping."
fi

pushd /etc/openstack_deploy
  if [ ! -d '/etc/ansible/roles' ]; then
    echo "*** Bootstrapping Ansible"
    pushd /opt/openstack-ansible
      scripts/bootstrap-ansible.sh
    popd
  fi

  echo "*** Generating OpenStack service passwords"
  for s in user_*secrets.yml; do
    if [ $(grep AES $s |wc -l) -eq 0 ]; then
      echo "*** $s"
      /usr/bin/env $OSA_PYEXE $OSA_TOKEN_GEN --file $s
    else
      echo "*** $s skipped, as it's encrypted"
    fi
  done
popd


if [ "$OSA_RUN_PLAY" = true ]; then
  if [ "${SKIP_PROMPTS}" != "true" ]; then
    echo ""
    echo "Ready for OSA deployment (updated os-computes.yml etc.) ?"
    read
  fi

  echo "*** OSA Inventory generation"
  $OSA_PYEXE $OSA_INVENTORY --check >/dev/null

  echo "*** Installing OSA base packages"
  ansible hosts -m shell -a 'DEBIAN_FRONTEND=noninteractive apt-get -o "Dpkg::Options::=--force-confdef" -o "Dpkg::Options::=--force-confold" -qy install aptitude build-essential ntp ntpdate openssh-server python-dev sudo' 2>&1 > ~/ansible-base-package-install.log
  if [ $? -gt 1 ]; then
    echo "*** Check for ansible errors at ~/ansible-base-package-install.log"
    exit 1
  fi

  . /usr/local/bin/openstack-ansible.rc
  echo "*** Executing OSA host and infrastructure playbooks"

  pushd /opt/openstack-ansible/playbooks
    plays="setup-hosts.yml setup-infrastructure.yml"
    for p in $plays; do
      openstack-ansible $p
    done
  popd

  if [ -f /etc/openstack_deploy/env.d/designate_bind.yml ]; then
    echo "*** Installing BIND9 service for designate"
    pushd /opt/openstack-ops/playbooks
      openstack-ansible install-bind-designate.yml
    popd
  fi

  echo "*** Executing OSA openstack playbook"
  pushd /opt/openstack-ansible/playbooks
    plays="setup-openstack.yml"
    for p in $plays; do
      openstack-ansible $p
    done
  popd
else
  echo "*** OSA playbook execution skipped"
fi

