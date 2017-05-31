#!/usr/bin/env python
#
#
#

import requests
import os
import sys
import re
import json
import argparse
import subprocess
import datetime as dt
from subprocess import PIPE

VERSION = '2017-05-31'

checkPrereqs    = ["dmidecode", "ethtool", "hpssacli", "hponcfg"]
installPrereqs  = ["rpm2cpio"]

baseUrl = "http://aaronsegura.com/hpfw/"
workDir = "%s/%s-%s" % (os.environ["HOME"], "hpfw-upgrade", dt.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"))
ret     = 0

parser  = argparse.ArgumentParser(description="HP Firmware Upgrade Utility v%s" % VERSION)
parser.add_argument("-f", help="Do Flash (otherwise, just dry run)", dest="flash", action="store_const", const=True, default=False)
parser.add_argument("-i", help="Install missing utilities and run check, no Flash", dest="install", action="store_const", const=True, default=False)
parser.add_argument("-r", help="Generate JSON report of current versions", dest="report", action="store_const", const=True, default=False)
parser.add_argument("--NIC", help="Flash NIC firmware", dest="do", action="append_const", const="NIC")
parser.add_argument("--SYS", help="Flash System BIOS", dest="do", action="append_const", const="SYSTEM")
parser.add_argument("--RAID", help="Flash RAID Controller", dest="do", action="append_const", const="RAID")
parser.add_argument("--ILO", help="Flash ILO Controller", dest="do", action="append_const", const="ILO")

args = parser.parse_args()

if args.do == None:
  args.do = ["NIC", "SYSTEM", "RAID", "ILO"]

if not args.flash and not args.install and not args.report:
  print ""
  print "*********************************************"
  print "PERFORMING DRY RUN.  NO CHANGES WILL BE DONE."
  print "*********************************************"
  print ""
elif args.install:
  print ""
  print "*********************************************"
  print "     INSTALLING REQUIRED UTILITIES ONLY."
  print "*********************************************"
  print ""

if not os.path.exists(workDir) and args.flash:
  try:
    os.mkdir(workDir)
  except OSError, err:
    print "ERROR: %s" % err.message
    if 'exists' in err.message:
      pass
    else:
      print "Unable to create working directory %s: %s" % (workDir, err.message)
      exit(255)

if args.flash:
  try:
    os.chdir(workDir)
  except:
    print "Something went horribly wrong.  Aborting."
    exit(254)

firmwares = {}
firmwares["ProLiant DL380 Gen9"] = {
  "NIC": {
    "check" : "ethtool -i em1 | grep firmware | cut -d:  -f2- | tr -d ' '",
    "ver"   : "5719-v1.46NCSIv1.3.16.0",
    "fwpkg" : "hp-firmware-nic-broadcom-2.17.6-1.1.x86_64.rpm",
    "md5"   : "d300a2a95c1e4617bd4a07eede322511",
    "inp"   : "\n",
    "ret"   : 1
  },
  "SYSTEM": {
    "check" : "hpasmcli -s \"show server\" | grep ROM | cut -d: -f2- | tr -d ' '",
    "ver"   : "02/17/2017",
    "fwpkg" : "hp-firmware-system-p89-2.40_2017_02_17-2.1.i386.rpm",
    "md5"   : "4506ed3576c05989070fbe75bb58d65e",
    "inp"   : "y\nn\n",
    "ret"   : 1
  },
  "ILO": {
    "check" : "hponcfg -h | egrep Firmware | cut -d\  -f4",
    "ver"   : "2.50",
    "fwpkg" : "hp-firmware-ilo4-2.50-1.1.i386.rpm",
    "md5"   : "2141f1ff4f7a3ea637fd6e500add816d",
    "inp"   : "y\n",
    "ret"   : 0
  },
  "RAID": {
    "check" : "hpssacli controller all show config detail | grep -i firmware\ version | cut -d: -f2 | tr -d ' '| head -1",
    "ver"   : "5.04",
    "fwpkg" : "hp-firmware-smartarray-ea3138d8e8-5.04-1.1.x86_64.rpm",
    "md5"   : "a2fd504e1f77333f38ba5bbdbdeec36a",
    "inp"   : "A\n",
    "ret"   : 1
  }
}

# Check for pre-requisite packages necessary to determine versions
if not args.report:
  print "Checking for intial pre-requisites..."
for i in checkPrereqs:
  p = subprocess.Popen(['/usr/bin/env', 'which', i], stdin=PIPE, stdout=PIPE, stderr=PIPE)
  p.communicate()
  if p.returncode > 0:
    if not args.flash and not args.install:
      sys.stdout.write("Unable to find %s, but performing DRY RUN, so will not be installed.  Stopping.\n" % i)
      exit(2)
    else:
      sys.stdout.write("Unable to find %s.  Installing..." % i)
      sys.stdout.flush()
      p = subprocess.Popen(['/usr/bin/env', 'apt-get', 'install', '-y', i], stdin=PIPE, stdout=PIPE, stderr=PIPE)
      p.communicate()
      if p.returncode > 0:
        print "Failed.  Do the needful." 
        exit(1)
      else:
        print "Success!"


# Verify supported hardware
p = subprocess.Popen(['/usr/bin/env', 'dmidecode', '-s', 'system-product-name'], stdout=PIPE)
(sysType, stdErr) = p.communicate()

sysType = sysType.strip()
if sysType not in firmwares:
  print "Hardware version \"%s\" not supported." % sysType
  exit(2)
elif not args.report:
  print "Verified supported hardware: %s" % sysType

# Check for additional pre-requisite packages necessary to install the firmware
if args.flash:
  print "Checking for installation pre-requisites..."
  for i in installPrereqs:
    p = subprocess.Popen(['/usr/bin/env', 'which', i], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    p.communicate()
    if p.returncode > 0:
      if not args.flash:
        sys.stdout.write("Unable to find %s, but performing DRY RUN, so will not be installed.  Stopping.\n" % i)
        exit(2)
      else:
        sys.stdout.write("Unable to find %s.  Installing..." % i)
        sys.stdout.flush()
        p = subprocess.Popen(['/usr/bin/env', 'apt-get', 'install', '-y', i], stdin=PIPE, stdout=PIPE, stderr=PIPE)
        p.communicate()
        if p.returncode > 0:
          print "Failed.  Do the needful." 
          exit(1)
        else:
          print "Success!"

# Generate JSON firmware report
if args.report:
  sysCurrent = True
  report = {}
  servernum = re.findall('\d{6}(?=-)', os.uname()[1])[0]
  report[servernum] = {}
  for part in firmwares[sysType]:
    verProc = subprocess.Popen(firmwares[sysType][part]["check"], stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
    (version, stderr) = verProc.communicate()
    if verProc.returncode == 0 and version:
      report[servernum][part] = {
        "Installed" : version.strip(),
        "Available" : firmwares[sysType][part]["ver"]
      }
      if firmwares[sysType][part]["ver"] not in version.strip():
        sysCurrent = False
    else:
      if verProc.returncode != 0 or not version:
        print "Detection Failed for {}! {}" .format(part, stderr)
        print "Try running the check manually:\n{}" .format(firmwares[sysType][part]["check"])
        exit(5)
  report[servernum]["Current"] = sysCurrent
  print "{}" .format(json.dumps(report))

# Check existing firmware version and install if necessary
needsUpdate = False
if not args.report:
  for part in firmwares[sysType]:
    if part not in args.do:
      continue

    sys.stdout.write("\n")
    sys.stdout.write("Verifying current %s version: " % part)
    sys.stdout.flush()
    verProc = subprocess.Popen(firmwares[sysType][part]["check"], stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
    (version, stderr) = verProc.communicate()

    if verProc.returncode == 0 and firmwares[sysType][part]["ver"] in version.strip():
      print "Already current. Nothing to do."
    else:
      if verProc.returncode != 0:
        print "Detection Failed! %s" % stderr
        exit(5)
      else:
        needsUpdate = True
        sys.stdout.write("Needs update (%s -> %s)\n" % (version.strip(), firmwares[sysType][part]["ver"]))
        sys.stdout.flush()

        if args.flash:
          # Download the firmwares
          url = "%s%s" % (baseUrl, firmwares[sysType][part]["fwpkg"])

          sys.stdout.write("Downloading %s" % firmwares[sysType][part]["fwpkg"])
          sys.stdout.flush()
          try:
            r = requests.get(url)
          except:
            print "Failed!  Aborting."
            exit(3)

          try:
            with open("./%s" % firmwares[sysType][part]["fwpkg"], "wb") as pkg:
              pkg.write(r.content)
          except IOError:
            print "Unable to write file %s.  Aborting." % firmwares[sysType][part]["fwpkg"]
            exit(4)
          else:
            print " -> Success!"

          # Check MD5Sum
          sys.stdout.write("Checking MD5: ")
          sys.stdout.flush()

          md5sumCmd = "/usr/bin/env md5sum %s" % firmwares[sysType][part]["fwpkg"]
          p = subprocess.Popen(md5sumCmd, stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
          (md5, err) = p.communicate()

          if md5.split(" ")[0] == firmwares[sysType][part]["md5"]:
            print "Match!"
          else:
            print "Mismatch!  Report this immediately to aaron.segura@rackspace.com."
            exit(66)

          sys.stdout.write("Extracting firmware: " )
          sys.stdout.flush()

          try:
            os.mkdir("%s/%s" % (workDir, part))
          except:
            pass

          try:
            os.chdir("%s/%s" % (workDir, part))
          except:
            print "Unable to chdir %s/%s.  Aborting." % (workDir, part)
            continue

          extractCmd  = "rpm2cpio %s/%s | cpio -id" % (workDir,firmwares[sysType][part]["fwpkg"])
          extractProc = subprocess.Popen(extractCmd, stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
          (stdout, stderr) = extractProc.communicate()

          if extractProc.returncode != 0:
            print "Failed! %s" % stderr
          else:
            print "Success!"
            sys.stdout.write("Flashing...")
            sys.stdout.flush()

            dirCmd = "dirname %s/%s/usr/lib/*/hp-firmware-*/hpsetup" % (workDir, part)
            dirProc = subprocess.Popen(dirCmd, stdout=PIPE, shell=True)
            (flashDir, stderr) = dirProc.communicate()

            try:
              os.chdir(flashDir.strip())
            except OSError, err:
              print "Failed - cannot chdir to \"%s\", %s" % (flashDir.strip(), err.strerror)

            flashProc = subprocess.Popen(["/usr/bin/env", "bash", "./hpsetup"], stdout=PIPE, stderr=PIPE, stdin=PIPE)
            (stdout, stderr) = flashProc.communicate(firmwares[sysType][part]["inp"])
            if flashProc.returncode == firmwares[sysType][part]["ret"]:
              print "Success!"
            else:
              print "Failed!"

            print "Writing log to %s/%s.log" % (workDir, part)

            with open("%s/%s.log" % (workDir, part), "w+") as fp:
              fp.write(stdout)
              fp.write(stderr)

            os.chdir(workDir)

  print ""

if not args.flash and not args.report:
  if needsUpdate:
    print "SUMMARY: Needs Update"
    ret = 1
  else:
    print "SUMMARY: System up-to-date"
    ret = 0

exit(ret)
