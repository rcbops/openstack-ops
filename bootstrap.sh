#!/usr/bin/env bash

# Copyright 2025, Rackspace Technology, Inc.
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
export LC_ALL=C.UTF-8
mkdir -p ~/.venvs

BASEDIR="$(dirname "$0")"
cd "${BASEDIR}" || error "Could not change to ${BASEDIR}"

source scripts/lib/functions.sh

set -e

success "Environment variables:"
env | grep -E '^(SUDO|RPC_|ANSIBLE_|GENESTACK_|K8S|CONTAINER_|OPENSTACK_|OSH_)' | sort -u

success "Installing base packages (git):"
apt update

DEBIAN_FRONTEND=noninteractive \
  apt-get -o "Dpkg::Options::=--force-confdef" \
          -o "Dpkg::Options::=--force-confold" \
          -qy install git python3-pip python3-venv python3-dev jq build-essential > ~/openstack-ops-base-package-install.log 2>&1

if [ $? -gt 1 ]; then
  error "Check for ansible errors at ~/openstack-ops-base-package-install.log"
else
  success "Local base OS packages installed"
fi

# Create venv and prepare Ansible
python3 -m venv "${HOME}/.venvs/openstack-ops"
"${HOME}/.venvs/openstack-ops/bin/pip" install pip --upgrade
source "${HOME}/.venvs/openstack-ops/bin/activate" && success "Switched to venv ~/.venvs/openstack-ops"
pip install -r "${BASEDIR}/requirements.txt" && success "Installed ansible package"
ansible-playbook "${BASEDIR}/scripts/get-ansible-collection-requirements.yml" \
  -e collections_file="${ANSIBLE_COLLECTION_FILE}" \
  -e user_collections_file="${USER_COLLECTION_FILE}"

source  "${BASEDIR}/scripts/openstack-ops.rc"
success "Environment sourced per ${BASEDIR}/scripts/openstack-ops.rc"
