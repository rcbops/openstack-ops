#!/usr/bin/env python
#
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

from __future__ import print_function
from subprocess import PIPE

import argparse
import copy
import datetime as dt
import json
import os
import platform
import pprint

import re
import requests
import six
import sys
import subprocess
import xml.dom.minidom

# Globals
VERSION = '2020-01-14'
PP = pprint.PrettyPrinter(indent=4)

# Command to package name mappings
checkPrereqs = {
    "dmidecode": "dmidecode",
    "ethtool": "ethtool",
    "ssacli": "ssacli",
    "hponcfg": "hponcfg",
    "lspci": "pciutils",
    "lshw": "lshw",
    "ipmitool": "ipmitool"
}
installPrereqs = {
    "Ubuntu": {
        "rpm2cpio": "rpm2cpio"
    },
    "RedHat": {}
}


# Determine os device name for a potential embedded Broadcom NIC
nics = []
nics = os.listdir('/sys/class/net/')
testnic = "em1"
for nic in nics:
    if re.match("^(eth|em|eno)[0-9]+$", nic):
        with open("/sys/class/net/{}/device/uevent".format(nic), "r") as uevent:
            for cnt, line in enumerate(uevent):
                if "DRIVER=tg3" in line:
                    testnic = nic
                    uevent.close()
                    break

# Map platforms against firmware versions
firmwares = {}

# GEN9 definitions
firmwares["ProLiant DL360 Gen9"] = {
    "spp-gen": "gen9",
    "spp-version": "2019.12.0",
    "NIC": {
        "check": "ethtool -i {} | grep firmware | cut -d:  -f2- | tr -d ' '".format(testnic),
        "ver": "5719-v1.46NCSIv1.5.1.0",
        "fwpkg": "hp-firmware-nic-broadcom-2.23.10-1.1.x86_64.rpm",
        "md5": "7f40390d8d89d150faea075812ab9a90",
        "inp": "\n",
        "ret": 1
    },
    "SYSTEM": {
        "check": "hpasmcli -s \"show server\" | grep ROM | cut -d: -f2- | tr -d ' '",
        "ver": "10/21/2019",
        "fwpkg": "hp-firmware-system-p89-2.76_2019_10_21-1.1.i386.rpm",
        "md5": "952e3b3244dd818084fbd09cc3f8c14e",
        "inp": "y\nn\n",
        "ret": 1
    },
    "RAID": {
        "check": "ssacli controller all show config detail | grep -i firmware\ version | cut -d: -f2 | tr -d ' '| head -1",
        "ver": "7.00",
        "fwpkg": "hp-firmware-smartarray-ea3138d8e8-7.00-1.1.x86_64.rpm",
        "md5": "84261221942a6dd6bd6898620f460f56",
        "inp": "A\n",
        "ret": 1
    },
    "ILO": {
        "check": "hponcfg -h | awk '/Firmware/ {print $4}'",
        "ver": "2.70",
        "fwpkg": "hp-firmware-ilo4-2.70-1.1.i386.rpm",
        "md5": "3828dae3a4cb068428bc7cf71a06d3dd",
        "inp": "y\n",
        "ret": 0
    },
    "INIC": {
       "560FLB": { "ver": "800008F0", "fwpkg": "hp-firmware-nic-intel-1.16.0-1.1.x86_64.rpm" },
       "560FLR-SFP+": { "ver": "80000838", "fwpkg": "hp-firmware-nic-intel-1.19.11-1.1.x86_64.rpm" },
       "560SFP+": { "ver": "80000838", "fwpkg": "hp-firmware-nic-intel-1.19.11-1.1.x86_64.rpm" },
       "560M": { "ver": "8000083D", "fwpkg": "hp-firmware-nic-intel-1.16.0-1.1.x86_64.rpm" },
       "561FLR-T": { "ver": "800005B6", "fwpkg": "hp-firmware-nic-intel-1.16.0-1.1.x86_64.rpm" },
       "561T": { "ver": "80000636", "fwpkg": "hp-firmware-nic-intel-1.16.0-1.1.x86_64.rpm" },
       "562i": { "ver": "800006FC", "fwpkg": "hp-firmware-nic-intel-1.16.0-1.1.x86_64.rpm" },
       "562FLR-SFP+": { "ver": "8000641A", "fwpkg": "hp-firmware-nic-intel-1.19.11-1.1.x86_64.rpm" },
       "562FLR-T": { "ver": "80000F56", "fwpkg": "hp-firmware-nic-intel-1.19.11-1.1.x86_64.rpm" },
       "562SFP+": { "ver": "80006424", "fwpkg": "hp-firmware-nic-intel-1.19.11-1.1.x86_64.rpm" },
       "562T": { "ver": "80000F55", "fwpkg": "hp-firmware-nic-intel-1.19.11-1.1.x86_64.rpm" },
       "563i": { "ver": "800035C0", "fwpkg": "hp-firmware-nic-intel-1.19.11-1.1.x86_64.rpm" },
       "568i": { "ver": "80001DEE", "fwpkg": "hp-firmware-nic-intel-1.19.11-1.1.x86_64.rpm" },
       "568FLR-MMSFP+": { "ver": "80001DE9", "fwpkg": "hp-firmware-nic-intel-1.19.11-1.1.x86_64.rpm" },
       "568FLR-MMT": { "ver": "80001DE9", "fwpkg": "hp-firmware-nic-intel-1.19.11-1.1.x86_64.rpm" },
       "hp-firmware-nic-intel-1.16.0-1.1.x86_64.rpm": { "md5": "c2af9badd28debbee468486ecac9fc4e", "ret": 1 },
       "hp-firmware-nic-intel-1.19.11-1.1.x86_64.rpm": { "md5": "bf479b6ec8105c284b169c7d67d55e6b", "ret": 1 }
    }
}

firmwares["ProLiant DL380 Gen9"] = copy.deepcopy(
    firmwares["ProLiant DL360 Gen9"])

firmwares["ProLiant DL380 Gen9"]["SYSTEM"] = {
    "check": "hpasmcli -s \"show server\" | grep ROM | cut -d: -f2- | tr -d ' '",
    "ver": "10/21/2019",
    "fwpkg": "hp-firmware-system-p89-2.76_2019_10_21-1.1.i386.rpm",
    "md5": "952e3b3244dd818084fbd09cc3f8c14e",
    "inp": "y\nn\n",
    "ret": 1
}

# GEN10 definition
firmwares["ProLiant DL360 Gen10"] = {
    "spp-gen": "gen10",
    "spp-version": "2019.12.0",
    "NIC": {
        "check": "ethtool -i {} | grep firmware | cut -d:  -f2- | tr -d ' '".format(testnic),
        "ver": "5719-v1.46NCSIv1.5.1.0",
        "fwpkg": "hp-firmware-nic-broadcom-2.23.10-1.1.x86_64.rpm",
        "md5": "7f40390d8d89d150faea075812ab9a90",
        "inp": "\n",
        "ret": 1
    },
    "SYSTEM": {
        "check": "ipmitool fru |grep 'MB BIOS' -A5 |awk -F ': ' '/Product Version/ {print $2}'",
        "ver": "10/21/2019",
        "fwpkg": "hp-firmware-system-u32-2.22_2019_11_13-1.1.x86_64.rpm",
        "md5": "b5222bb8f139229bcf06177c817772f5",
        "inp": "y\nn\n",
        "ret": 1
    },
    "RAID": {
        "check": "ssacli controller all show config detail | grep -i firmware\ version | cut -d: -f2 | tr -d ' '| head -1",
        "ver": "2.62",
        "fwpkg": "hp-firmware-smartarray-f7c07bdbbd-2.62-1.1.x86_64.rpm",
        "md5": "6757387a3419412a417eba2da6dda2f0",
        "inp": "A\n",
        "ret": 1
    },
    "ILO": {
        "check": "hponcfg -h | awk '/Firmware/ {print $4}'",
        "ver": "1.45",
        "fwpkg": "hp-firmware-ilo5-1.45-1.1.x86_64.rpm",
        "md5": "3ddccffc3c4030955e70ae6277425364",
        "inp": "y\n",
        "ret": 0
    },
    "INIC": {
       "560FLB": { "ver": "800008F0", "fwpkg": "hp-firmware-nic-intel-1.16.0-1.1.x86_64.rpm" },
       "560FLR-SFP+": { "ver": "80000838", "fwpkg": "hp-firmware-nic-intel-1.19.11-1.1.x86_64.rpm" },
       "560SFP+": { "ver": "80000838", "fwpkg": "hp-firmware-nic-intel-1.19.11-1.1.x86_64.rpm" },
       "560M": { "ver": "8000083D", "fwpkg": "hp-firmware-nic-intel-1.16.0-1.1.x86_64.rpm" },
       "561FLR-T": { "ver": "800005B6", "fwpkg": "hp-firmware-nic-intel-1.16.0-1.1.x86_64.rpm" },
       "561T": { "ver": "80000636", "fwpkg": "hp-firmware-nic-intel-1.16.0-1.1.x86_64.rpm" },
       "562i": { "ver": "800006FC", "fwpkg": "hp-firmware-nic-intel-1.16.0-1.1.x86_64.rpm" },
       "562FLR-SFP+": { "ver": "8000641A", "fwpkg": "hp-firmware-nic-intel-1.19.11-1.1.x86_64.rpm" },
       "562FLR-T": { "ver": "80000F56", "fwpkg": "hp-firmware-nic-intel-1.19.11-1.1.x86_64.rpm" },
       "562SFP+": { "ver": "80006424", "fwpkg": "hp-firmware-nic-intel-1.19.11-1.1.x86_64.rpm" },
       "562T": { "ver": "80000F55", "fwpkg": "hp-firmware-nic-intel-1.19.11-1.1.x86_64.rpm" },
       "563i": { "ver": "800035C0", "fwpkg": "hp-firmware-nic-intel-1.19.11-1.1.x86_64.rpm" },
       "568i": { "ver": "80001DEE", "fwpkg": "hp-firmware-nic-intel-1.19.11-1.1.x86_64.rpm" },
       "568FLR-MMSFP+": { "ver": "80001DE9", "fwpkg": "hp-firmware-nic-intel-1.19.11-1.1.x86_64.rpm" },
       "568FLR-MMT": { "ver": "80001DE9", "fwpkg": "hp-firmware-nic-intel-1.19.11-1.1.x86_64.rpm" },
       "hp-firmware-nic-intel-1.16.0-1.1.x86_64.rpm": { "md5": "c2af9badd28debbee468486ecac9fc4e", "ret": 1 },
       "hp-firmware-nic-intel-1.19.11-1.1.x86_64.rpm": { "md5": "bf479b6ec8105c284b169c7d67d55e6b", "ret": 1 }
    }
}

firmwares["ProLiant DL380 Gen10"] = copy.deepcopy(
    firmwares["ProLiant DL360 Gen10"])

firmwares["ProLiant DL380 Gen10"]["SYSTEM"] = {
    "check": "ipmitool fru |grep 'MB BIOS' -A5 |awk -F ': ' '/Product Version/ {print $2}'",
    "ver": "11/13/2019",
    "fwpkg": "hp-firmware-system-u30-2.22_2019_11_13-1.1.x86_64.rpm",
    "md5": "071d68e372601a62ecaee54bf119daf8",
    "inp": "y\nn\n",
    "ret": 1
}

baseUrl = "http://d490e1c1b2bc716e2eaf-63689fefdb0190e2db0220301cd1330e.r14.cf5.rackcdn.com/"
workDir = "{}/{}-{}".format(os.environ["HOME"], "hpfw-upgrade",
                            dt.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"))


def parse_args(args):
    parser = argparse.ArgumentParser(
        description="HP Firmware Upgrade Utility v{}".format(VERSION))
    parser.add_argument("-f", help="Do Flash (otherwise, just dry run)", dest="flash", action="store_const", const=True,
                        default=False)
    parser.add_argument("-i", help="Install missing utilities and run check, no Flash", dest="install",
                        action="store_const", const=True, default=False)
    parser.add_argument("-r", help="Generate JSON report of current versions", dest="report", action="store_const",
                        const=True, default=False)
    parser.add_argument("--NIC", help="Flash NIC firmware",
                        dest="do", action="append_const", const="NIC")
    parser.add_argument("--SYS", help="Flash System BIOS",
                        dest="do", action="append_const", const="SYSTEM")
    parser.add_argument("--RAID", help="Flash RAID Controller",
                        dest="do", action="append_const", const="RAID")
    parser.add_argument("--ILO", help="Flash ILO Controller",
                        dest="do", action="append_const", const="ILO")
    parser.add_argument("--INIC", help="Flash Intel NIC firmware",
                        dest="do", action="append_const", const="INIC")

    return parser.parse_args(args)


def isRedhatOS():
    if 'Red Hat Enterprise Linux Server' in platform.linux_distribution():
        return True
    return False


def checkChassisSupport():
    p = subprocess.Popen(['/usr/bin/env', 'dmidecode',
                          '-s', 'system-product-name'], stdout=PIPE)
    (sysType, stdErr) = p.communicate()

    sysType = sysType.strip().decode(encoding='UTF-8')
    if sysType not in firmwares:
        return (sysType, False)
    else:
        return (sysType, True)


def checkRHPrereq(sysType=""):
    sppgen = firmwares[sysType]["spp-gen"]
    sppversion = firmwares[sysType]["spp-version"]

    hpspp = "[hp-spp]\n" \
            "name = HP Service Pack for ProliantPackage\n" \
            "baseurl = https://downloads.linux.hpe.com/SDR/repo/spp-{}/rhel/$releasever/$basearch/{}\n" \
            "enabled = 1\n" \
            "gpgcheck = 1\n" \
            "gpgkey = https://downloads.linux.hpe.com/SDR/repo/spp/GPG-KEY-spp".format(
                sppgen, sppversion)

    if not os.path.isfile('/etc/yum.repos.d/hp-spp.repo'):
        print("Adding hp-spp repo...\n")
        with open("/etc/yum.repos.d/hp-spp.repo", "w+") as hprepo:
            hprepo.write(hpspp)
            hprepo.close()
    else:
        with open("/etc/yum.repos.d/hp-spp.repo", "r") as hprepo_check:
            for cnt, line in enumerate(hprepo_check):
                if re.match("^baseurl.*mirror\.rackspace\.com.*", line):
                    hprepo_check.close()

                    print("Switching hp-spp repo to upstream...\n")
                    with open("/etc/yum.repos.d/hp-spp.repo", "w+") as hprepo:
                        hprepo.write(hpspp)
                        hprepo.close()
                    break

    if sppgen == "gen9":
        verCheck = subprocess.Popen(
            "rpm -q hp-health | cut -d - -f 3", stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
        hpasmcliver = verCheck.communicate()[0].strip().decode(encoding='UTF-8')
        update_packages = False
        if hpasmcliver:
            if float(hpasmcliver) < 10.90:
                print("Installed version of hp-health package ({}) is out of date.\n"
                      " {} installed, 10.90 or later required.".format(i, hpasmcliver))
                update_packages = True
        else:
            update_packages = True

        if update_packages:
            print("hp-health package ver out of date or not installed, installing...")
            u = subprocess.Popen(['/usr/bin/env', 'yum', 'install',
                                  '-y', 'hp-health'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
            u.communicate().decode(encoding='UTF-8')
            if u.returncode > 0:
                print("Failed. Please correct and restart!")
                exit(1)
            else:
                verCheck = subprocess.Popen(
                    "rpm -q hp-health | cut -d - -f 3", stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
                hpasmcliver = verCheck.communicate()[0].strip().decode(encoding='UTF-8')
                if float(hpasmcliver) < 10.90:
                    print("Update successful, but version {} still not greater than 10.90. Check manually.".format(
                        hpasmcliver))
                    exit(2)
                else:
                    print("Update successful, new version is {}!".format(hpasmcliver))


def instPackages(packages={}):
    for i in packages:
        p = subprocess.Popen(['/usr/bin/env', 'which', i],
                             stdin=PIPE, stdout=PIPE, stderr=PIPE)
        p.communicate()
        if p.returncode > 0:
            if not args.flash and not args.install:
                print(
                    "Unable to find {}, but performing DRY RUN, so will not be installed. Stopping.\n".format(i))
                exit(2)
            else:
                print("Unable to find {} Installing...".format(i))
                if not isRedhatOS():
                    p = subprocess.Popen(['/usr/bin/env', 'apt-get', 'install', '-y', checkPrereqs[i]], stdin=PIPE, stdout=PIPE,
                                         stderr=PIPE)
                else:
                    p = subprocess.Popen(['/usr/bin/env', 'yum', '-y', 'install', checkPrereqs[i]], stdin=PIPE, stdout=PIPE,
                                         stderr=PIPE)

                (stdoutdata, stderrdata) = p.communicate()
                if p.returncode > 0:
                    print("Failed. Please correct and restart!\n{}".format(stderrdata.decode(encoding='UTF-8')))
                    exit(1)
                else:
                    print("Success!")

def downloadFlash(sysType = None, part = None, url = None, model = None):
    if sysType is None or part is None or url is None:
        print("No parameters found for downloadFlash")
        exit(255)

    print("{}".format(url))
    sys.stdout.write("Downloading {} ".format(
        firmwares[sysType][part]["fwpkg"]))
    sys.stdout.flush()
    try:
        r = requests.get(url)
    except:
        print("Failed!  Aborting.")
        exit(3)

    fileName = "./{}".format(firmwares[sysType][part]["fwpkg"])
    if part == "INIC":
        fileName = "./{}".format(firmwares[sysType][part][model]["fwpkg"])

    md5Hash = firmwares[sysType][part]["fwpkg"]
    if part == "INIC":
        md5Hash = firmwares[sysType][part][fileName]["md5"]

    try:

        with open(fileName, "wb") as pkg:
            pkg.write(r.content)
    except IOError:
        print("Unable to write file {}. Aborting.".format(
            fileName))
        exit(4)
    else:
        print(" -> Success!")

    # Check MD5Sum
    sys.stdout.write("Checking MD5: ")
    sys.stdout.flush()

    md5sumCmd = "/usr/bin/env md5sum {}".format(fileName)

    p = subprocess.Popen(md5sumCmd, stdin=PIPE,
                         stdout=PIPE, stderr=PIPE, shell=True)
    (md5, err) = p.communicate()

    md5 = md5.decode(encoding='UTF-8')
    if md5.split(" ")[0] == md5Hash:
        print("Match!")
    else:
        print("Mismatch!  Report this to the author of https://github.com/rcbops/openstack-ops/OWNERS")
        exit(66)

    sys.stdout.write("Extracting firmware: ")
    sys.stdout.flush()

    try:
        os.mkdir("{}/{}".format(workDir, part))
    except:
        pass

    try:
        os.chdir("{}/{}".format(workDir, part))
    except:
        print("Unable to chdir {}/{}. Aborting.".format(workDir, part))
        continue

    extractCmd = "rpm2cpio {}/{} | cpio -id".format(
        workDir, firmwares[sysType][part]["fwpkg"])
    extractProc = subprocess.Popen(
        extractCmd, stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)

    (stdout, stderr) = extractProc.communicate()

    stdout = stdout.decode(encoding='UTF-8')
    if extractProc.returncode != 0:
        print("Failed! {}".format(stderr.decode(encoding='UTF-8')))
    else:
        print("Success!")
        sys.stdout.write("Flashing...")
        sys.stdout.flush()

        dirCmd = "dirname {}/{}/usr/lib/*/*firmware-*/hpsetup".format(
            workDir, part)
        dirProc = subprocess.Popen(dirCmd, stdout=PIPE, shell=True)
        (flashDir, stderr) = dirProc.communicate()

        flashDir = flashDir.decode(encoding='UTF-8')
        try:
            os.chdir(flashDir.strip())
        except OSError as err:
            print("Failed - cannot chdir to \"{}\", {}".format(
                flashDir.strip(), err.strerror))

        flashProc = subprocess.Popen(["/usr/bin/env", "bash", "./hpsetup"], stdout=PIPE, stderr=PIPE,
                                     stdin=PIPE)
        (stdout, stderr) = flashProc.communicate(
            firmwares[sysType][part]["inp"].encode(encoding='UTF-8'))

        stdout = stdout.decode(encoding='UTF-8')
        if flashProc.returncode == firmwares[sysType][part]["ret"]:
            print("Success!")
        else:
            print("Failed!")

        print("Writing log to {}/{}.log".format(workDir, part))

        with open("{}/{}.log".format(workDir, part), "w+") as fp:
            fp.write(stdout)
            fp.write(stderr.decode(encoding='UTF-8'))

        os.chdir(workDir)

def main(debug=False, **kwargs):
    """Run the main application.
    :param debug: ``bool`` enables debug logging
    :param kwargs: ``dict`` for passing command line arguments
    """
    ret = 0

    if not args.flash and not args.install and not args.report:
        print("")
        print("*********************************************")
        print("PERFORMING DRY RUN. NO CHANGES WILL BE DONE.")
        print("*********************************************")
        print("")
    elif args.install:
        print("")
        print("*********************************************")
        print("     INSTALLING REQUIRED UTILITIES ONLY.")
        print("*********************************************")
        print("")

    if not os.path.exists(workDir) and args.flash:
        try:
            os.mkdir(workDir)
        except OSError as err:
            print("ERROR: {}".format(err.message))
            if 'exists' in err.message:
                pass
            else:
                print("Unable to create working directory {}: {}".format(
                    workDir, err.message))
                exit(255)

    if args.flash:
        try:
            os.chdir(workDir)
        except:
            print("Something went horribly wrong. Aborting.")
            exit(254)

    if "INIC" in args.do:
        # Verifying the presence of 10G Intel NICs.
        nicError = False
        inics = {}
        lshw_s = ""

        s = subprocess.Popen(['/usr/bin/env', 'lshw', '-c', 'network',
            '-xml', '-sanitize'], stdin=PIPE, stdout=PIPE, stderr=PIPE)

        lshw = s.communicate()[0].decode(encoding='UTF-8').splitlines()
        lshw_s = lshw_s.join(lshw)
        DOMTree = xml.dom.minidom.parseString(lshw_s)
        networks = DOMTree.documentElement.getElementsByTagName("node")

        for network in networks:
            try:
                productName = network.getElementsByTagName('product')[0].childNodes[0].data
                vendorName = network.getElementsByTagName('vendor')[0].childNodes[0].data
                busInfo = network.getElementsByTagName('businfo')[0].childNodes[0].data
                logicalName = network.getElementsByTagName('logicalname')[0].childNodes[0].data
            except:
                pass

            if productName.startswith("Ethernet Controller 10-Gigabit") and \
                "Intel Corporation" in vendorName and logicalName:
                slot = busInfo.split(':')[1] +":"+ busInfo.split(':')[2]
                inics[slot] = {}

                s = subprocess.Popen(['/usr/bin/env', 'lspci', '-v', '-d', '8086:1528'],
                    stdin=PIPE, stdout=PIPE, stderr=PIPE)
                out = s.communicate()[0].strip().decode(encoding='UTF-8')
                for x in re.split('\n\n', out):
                    try:
                        model = re.search('56[0-8][A-Z,i]{1,3}-?[A-Z]{0,5}\+?', x).group(0)
                    except IndexError:
                        print("Could not find the model number for the nic in slot {}.".format(slot))
                        nicError = True

                if not nicError:
                    f = subprocess.Popen(['/usr/bin/env', 'ethtool', '-i', logicalName],
                        stdin=PIPE, stdout=PIPE,stderr=PIPE)
                    warez = f.communicate()[0].strip().decode(encoding='UTF-8').upper().splitlines()
                    for line in warez:
                        if 'FIRMWARE-VERSION:' in line:
                            try:
                                nvm = re.search('(?<=FIRMWARE-VERSION:\s0X)[A-F,0-9]{8}', line).group(0)
                                inics[slot]['Names'] = logicalName
                                inics[slot]['Model'] = model
                                inics[slot]['NVM'] = nvm
                            except IndexError:
                                print('Could not find the firmware version.')
                                print('Check "ethtool -i" output for NIC: {}'.format(logicalName))
                                nicError = True
                            except KeyError:
                                    print("Hit KeyError setting inic values")
                                    exit(1)

        if nicError:
            print("Look into the NIC info errors above before "
                   "attempting to flash the Intel 10Gb NICs.")
            exit(1)
        else:
            inicinp = '\n\n' * len(inics)
            firmwares[sysType]["INIC"]["inp"] = inicinp

        if len(inics) < 1:
            print("No Intel 10Gb NICs to flash, skipping...")
            args.do.remove('INIC')

    # Generate JSON firmware report
    if args.report:
        sysCurrent = True
        report = {}
        servernum = re.findall('\d{6}(?=-)', os.uname()[1])[0]
        report[servernum] = {}
        for part in firmwares[sysType]:
            if not part == 'INIC':
                verProc = subprocess.Popen(firmwares[sysType][part]["check"], stdin=PIPE, stdout=PIPE, stderr=PIPE,
                                           shell=True)
                (version, stderr) = verProc.communicate()
                version = version.decode(encoding='UTF-8')
                if verProc.returncode == 0 and version:
                    report[servernum][part] = {
                        "Installed": version.strip(),
                        "Available": firmwares[sysType][part]["ver"]
                    }
                    if firmwares[sysType][part]["ver"] not in version.strip():
                        sysCurrent = False
                else:
                    if verProc.returncode != 0 or not version:
                        print("Detection Failed for {}! {}".format(part, stderr))
                        print("Try running the check manually:\n{}".format(
                            firmwares[sysType][part]["check"]))
                        exit(5)
            elif part == 'INIC':
                report[servernum][part] = {}
                report[servernum][part]['Cards'] = []
                for nic in inics:
                    report[servernum][part]['Cards'].append({
                        "Model": inics[nic]['Model'],
                        "Names": inics[nic]['Names'],
                        "Installed": inics[nic]['NVM'],
                        "Available": firmwares[sysType]["INIC"][inics[nic]['Model']]['ver']
                    })
                    if inics[nic]['NVM'] != firmwares[sysType]["INIC"][inics[nic]['Model']]['ver']:
                        sysCurrent = False
        report[servernum]["Current"] = sysCurrent
        print("{}".format(json.dumps(report)))

    # Check existing firmware version and install if necessary
    needsUpdate = False
    if not args.report:
        for part in args.do:
            partUpdate = False
            if not part == 'INIC':
                sys.stdout.write("\n")
                sys.stdout.write("Verifying current {} version: ".format(part))
                sys.stdout.flush()
                verProc = subprocess.Popen(firmwares[sysType][part]["check"], stdin=PIPE, stdout=PIPE, stderr=PIPE,
                                           shell=True)
                (version, stderr) = verProc.communicate()
                version = version.decode(encoding='UTF-8')

                if verProc.returncode == 0 and firmwares[sysType][part]["ver"] in version.strip():
                    print("Already current ({}). Nothing to do.".format(
                        version.strip()))
                else:
                    if verProc.returncode != 0:
                        print("Detection Failed! {}".format(stderr.decode(encoding='UTF-8')))
                        exit(5)
                    else:
                        needsUpdate = True
                        partUpdate = True
                        sys.stdout.write(
                            "Needs update ({} -> {})\n".format(version.strip(), firmwares[sysType][part]["ver"]))
                        sys.stdout.flush()

            elif part == 'INIC':
                print("")
                print("Verifying current Intel 10G NIC Versions: ")
                for nic in inics:
                    if inics[nic]['NVM'] == firmwares[sysType]["INIC"][inics[nic]['Model']]['ver']:
                        print(" {} already current. Nothing to do.".format(
                            inics[nic]['Names']))
                    else:
                        needsUpdate = True
                        partUpdate = True
                        print(" {} needs update ({} -> {})".format(inics[nic]['Names'], inics[nic]['NVM'],
                                                                   firmwares[sysType]["INIC"][inics[nic]['Model']]['ver']))

            if args.flash and partUpdate:
                # Download the firmwares
                if not part == "INIC":
                    url = "{}{}".format(baseUrl, firmwares[sysType][part]["fwpkg"])
                    downloadFlash(sysType, part, url)
                else:
                    for nics in inics:
                        fwname = firmwares[sysType]["INIC"][inics[nic]['Model']]['fwpkg']
                        url = "{}{}".format(baseUrl, firmwares[sysType]["INIC"][inics[nic][fwname])
                        downloadFlash(sysType, part, url, nics)

        print("")

    if not args.flash and not args.report:
        if needsUpdate:
            print("SUMMARY: Needs Update")
            ret = 1
        else:
            print("SUMMARY: System up-to-date")
            ret = 0

    exit(ret)


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    # Upate all components if none is specified
    if args.do is None:
        args.do = ["NIC", "SYSTEM", "RAID", "ILO", "INIC"]

    sysType, isSupported = checkChassisSupport()
    if not isSupported:
        print("Hardware version \"{}\" not supported.".format(sysType))
        exit(2)
    elif not args.report:
        print("Verified supported hardware: {}".format(sysType))

    # Check if RedHat based systems have the correct hp-health tools
    # installed. Ubuntu packages are managed by openstack-ops
    if isRedhatOS():
        checkRHPrereq(sysType)

    # Check for pre-requisite packages necessary to determine versions
    if not args.report or args.install:
        print("Checking for intial pre-requisites...")
        instPackages(checkPrereqs)

    # Check for additional pre-requisite packages necessary to install the firmware
    if args.flash:
        print("Checking for installation pre-requisites...")
        instReqs = installPrereqs['RedHat'] if isRedhatOS() else installPrereqs['Ubuntu']
        instPackages(instReqs)

    main(args)
