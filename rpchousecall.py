#!/usr/bin/python

import os, sys, urllib2, time, re, subprocess, MySQLdb, socket

try:
  from novaclient import exceptions as novaExceptions
  from keystoneclient import exceptions as keystoneExceptions
except ImportError:
  log("E", 0, "Unable to import python libraries.")
  exit(1)

try:
  from cinderclient import exceptions as cinderExceptions
except ImportError:
  pass

try:
  from neutronclient import exceptions as neutronExceptions
except ImportError:
  pass


####################################################################################################
#  Helper Functions
def log(severity, depth, msg):
  x = 0
  spacer = ""
  while x < depth:
    spacer += "--"
    x += 1

  print "[%s] (%s) %s %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), severity, spacer, msg)
  return 0

####################################################################################################
class RPCHCError(Exception):
  def __init__(self, errormsg):
    self.msg = errormsg

  def __str__(self):
    return self.msg

####################################################################################################
class KeystoneHealthCheck():
  def __init__(self):

    self.service = {}
    self.credentials = {}
    self.token = ""

    try:
      from keystoneclient.v2_0 import client as ksClient
    except ImportError, err:
      raise RPCHCError("Unable to import python libraries for Keystone client.  Please make sure python-keystoneclient is installed.")

    try:
      self.credentials["username"] = os.environ["OS_USERNAME"]
      self.credentials["password"] = os.environ["OS_PASSWORD"]
      self.credentials["auth_url"] = os.environ["OS_AUTH_URL"]
      self.credentials["tenant_name"] = os.environ["OS_TENANT_NAME"]
    except KeyError, err:
      raise RPCHCError("Could not find user credentials in environment.  Source your openrc file.")

    log(".", 1, "Keystone Init:")

    try:
      self.client = ksClient.Client(**self.credentials)
    except ksClient.exceptions.Unauthorized, err:
      raise RPCHCError("Unable to authenticate: %d %s" % (err.http_status, err.message))

    for svc in self.client.service_catalog.get_data():
      self.service[svc["type"]] = svc

    self.token  = self.client.auth_token

    log("+", 2, "Authenticated and received token: %s" % (self.token))

    for tenant in self.client.tenants.list():
      if tenant.name == "admin":
        self.tenant = self.client.tenants.get(tenant.id)

    log(".", 2, "Admin Tenant ID: %s" % (self.tenant.id))

    log(".", 1, "Keystone Init Complete")

    return

####################################################################################################
class NeutronHealthCheck():
  def __init__(self, ks):

    self.netName     = "RPCHealthCheckNetwork"
    self.subnetName  = "RPCHealthCheckSubnet"

    self.agents     = []
    self.networks   = []

    self.client     = None
    self.network    = None
    self.subnet     = None

    log(".", 1, "Neutron Init:")

    try:
      from neutronclient.neutron import client as neutronClient
    except ImportError, err:
      raise RPCHCError("Unable to import python libraries for neutron client.  Please make sure python-neutronclient is installed.  %s" % err.message)

    self.client = neutronClient.Client("2.0", **ks.credentials)

    networks = self.client.list_networks()
    agents = self.client.list_agents()

    log("+", 2, "Authenticated at endpoint")

    if "agents" in agents.keys():
      for agent in agents["agents"]:
        self.agents.extend([agent])
        if agent["alive"] != True and agent["admin_state_up"] == True:
          log("X", 2, "Agent %s in DOWN state while enabled on %s" % (agent["binary"], agent["host"]))

    if "networks" in networks.keys():
      for network in networks["networks"]:
        self.networks.extend([network])
        if network["name"] == self.netName:
          self.network = network
          log("W", 2, "Network %s already exists with ID %s.  Verify cleanup below." % (self.netName, network["id"]))

    if self.network:
      try:
        self.subnet = self.client.list_subnets(network_id=self.network["id"])["subnets"][0]
      except IndexError:
        pass

    log(".", 1, "Neutron Init Complete")
    return

  def setup(self, ks, nv):
    log(".", 1, "Neutron Environment Prep:")

    if not self.network:
      log(".", 2, "Creating Network...")
      newNet =  { 
                  "network": 
                  {
                    "name": self.netName
                  }
                }

      self.client.create_network(newNet)
      try:
        self.network = self.client.list_networks(name=self.netName)["networks"][0]
      except IndexError:
        raise RPCHCError("Unable to create network %s." % self.netName)
      else:
        log("+", 2, "Successfully created network %s with ID %s" % ( self.netName, self.network["id"]))
    else:
      log("W", 2, "Using already-existing network %s with ID %s" % (self.netName, self.network["id"]))

    if not self.subnet:
      log(".", 2, "Creating Subnet...")
      newSubnet = {
                    "subnet": 
                    {
                      "network_id": self.network["id"],
                      "name": self.subnetName,
                      "ip_version": 4,
                      "cidr": "10.0.0.0/24",
                      "allocation_pools": [{"start": "10.0.0.20", "end": "10.0.0.50"}]
                    }
                  }

      self.client.create_subnet(newSubnet)
      try:
        self.subnet = self.client.list_subnets(network_id=self.network["id"])["subnets"][0]
      except KeyError:
        raise RPCHCError("Unable to create subnet %s." % self.subnetName)

      log("+", 2, "Successfully created subnet %s with ID %s, cidr %s" % (self.subnetName, self.subnet["id"], self.subnet["cidr"]))
    else:
      log("W", 2, "Using already-existing subnet %s with ID %s, cidr %s" % (self.subnetName, self.subnet["id"], self.subnet["cidr"]))


    log(".", 1, "Neutron Environment Prep Complete")
    return

  def run(self, nv):
    log(".", 1, "Neutron Testing:")

    cmd = "ip netns exec qdhcp-%s ping -c1 %s > /dev/null 2>&1" % (self.network["id"], nv.instance.networks[self.netName][0])

    log(".", 2, "Ping?")

    result = subprocess.call(cmd, shell=True)

    if result == 0:
      log("+", 2, "Pong!")
    else:
      log("!", 2, "Unable to ping instance inside of namespace!")

    log(".", 1, "Neutron Testing Complete")
    return

  def cleanup(self):
    log(".", 1, "Neutron Cleanup:")

    self.client.delete_subnet(self.subnet["id"])

    log(".", 2, "Deleted Subnet %s" % self.subnetName)

    self.client.delete_network(self.network["id"])

    log(".", 2, "Deleted Network %s" % self.netName)

    log(".", 1, "Neutron Cleanup Complete")
    return

####################################################################################################
class NovaHealthCheck():
  def __init__(self, ks):

    self.flavorName   = "RPCHealthCheckFlavor"
    self.keypairName  = "controller-id_rsa"
    self.secgroupName = "rpc-support"
    self.instanceName = "RPCHealthCheckInstance"
    self.snapName     = "RPCHealthCheckSnapshot"

    self.flavor     = None
    self.keypair    = None
    self.secgroup   = None
    self.instance   = None

    self.services   = []

    self.credentials = {}
    self.credentials["username"] = ks.credentials["username"]
    self.credentials["api_key"] = ks.credentials["password"]
    self.credentials["auth_url"] = ks.credentials["auth_url"]
    self.credentials["project_id"] = ks.credentials["tenant_name"]

    log(".", 1, "Nova Init:")

    try:
      from novaclient.v1_1 import client as nvClient
    except ImportError, err:
      raise RPCHCError("Unable to import python libraries for Nova client.  Please make sure python-novaclient is installed.")

    self.client = nvClient.Client(**self.credentials)

    log("+", 2, "Successful authentication")

    # Check for offline services
    r = [self.client.services.list()]
    for i in r:
      for x in i:
        self.services.extend([{"host": x.host, "binary": x.binary, "status": x.status, "state": x.state}])
        if x.state == "down" and x.status != "disabled":
          log("X", 2, "Nova Service %s is %s on %s while marked \"%s\"" % (x.binary, x.state, x.host, x.status))

    try:
      self.flavor = self.client.flavors.find(name=self.flavorName)
    except novaExceptions.NotFound:
      pass
    else:
      log("W", 2, "HealthCheck Flavor \"%s\" already exists with ID %s, verify cleanup below." % (self.flavorName, self.flavor.id))


    try:
      self.keypair = self.client.keypairs.find(name=self.keypairName)
    except novaExceptions.NotFound:
      log("!", 2, "Keypair %s does not exist." % (self.keypairName))
    else:
      log(".", 2, "Found keypair %s." % (self.keypairName))

    #try:
      #self.network = self.client.networks.find(label=self.netName)
    #except novaExceptions.NotFound:
      #raise RPCHCError("Unable to find %s network for launching instances." % (self.netName))
    #else:
      #log(".", 2, "Found %s with ID %s" % (self.netName, self.network.id))

    try:
      self.secgroup = self.client.security_groups.find(name="rpc-support")
    except novaExceptions.NotFound:
      log("!", 2, "Unable to find security group %s.  Cannot test instance connectivity.")
    else:
      log(".", 2, "Found security group %s with ID %s" % (self.secgroupName, self.secgroup.id))

    try:
      self.client.servers.find(name=self.instanceName)
    except novaExceptions.NotFound:
      pass
    else:
      raise RPCHCError("Instance \"%s\" already exists.  Remove it before running this script." % (self.instanceName))


    log(".", 1, "Nova Init Complete")
    return


  #======================#
  def setup(self, ks):

    log(".", 1, "Nova Environment Prep:")

    if not self.flavor:
      log(".", 2, "Creating Flavor \"%s\" (512M, 1CPU, 5G, 0 swap, not public)" % self.flavorName)
      try:
        self.flavor = self.client.flavors.create(name=self.flavorName, ram=512, vcpus=1, disk=5, flavorid="auto", swap=0, rxtx_factor=1.0, is_public=False)
      except novaclient.exceptions.Conflict:
        # already exists
        pass
      else:
        log("+", 2, "Successfully created \"%s\" Flavor" % self.flavorName)

    try:
      self.client.flavor_access.add_tenant_access(self.flavor.id, ks.tenant.id)
    except AttributeError, err:
      # TOTO: Figure out why this throws an attributeError even on success
      if err.args != "name":
        raise RPCHCError("addTenantAccess: %s" % err.args)
      else:
        log("+", 2, "Admin tenant added to access list for flavor \"%s\"" % self.flavor.name)
    except novaExceptions.Conflict:
      log("+", 2, "Admin tenant has access to flavor \"%s\"" % self.flavor.name)


    log(".", 1, "Nova Environment Prep Complete")
    return

  #======================#
  def run(self, ks, gl, nt):
    log(".", 1, "Nova Testing:")

    self.instance = self.client.servers.create(self.instanceName, gl.image.id, self.flavor.id, key_name=self.keypair.name, security_groups=[self.secgroup.id], nics=[{"net-id": nt.network["id"]}])

    log(".", 2, "Booting test instance...")

    while self.instance.status == "BUILD":
      time.sleep(1)
      self.instance = self.client.servers.find(name=self.instanceName)

    if self.instance.status == "ACTIVE":
      log("+", 3, "Instance booted successfully with ID %s" % (self.instance.id))
    else:
      raise RPCHCError("Instance did not go into ACTIVE status after BUILD.  Instance ID %s, status %s" % (self.instance.id, self.instance.status))

    log(".", 3, "Waiting for instance OS to load...")

    ctr = 0
    finished_booting = False

    while not finished_booting and ctr < 120:  # 2 minutes
      console = self.instance.get_console_output()

      for line in console.split("\n"):
        match = re.search("^Cloud-init .* finished", line)
        if match:
          finished_booting = True

      ctr += 1
      time.sleep(1)

    log(".", 1, "Nova Testing Complete")
    pass

  #======================#
  def cleanup(self, ks):
    log(".", 1, "Nova Cleanup:")

    log(".", 2, "Deleting instance %s" % self.instanceName)
    self.instance.delete()
    time.sleep(1)

    ctr = 0
    while self.instance and ctr < 30:
      try:
        self.instance = self.client.servers.find(name=self.instanceName)
      except novaExceptions.NotFound:
        log("+", 2, "Instance Deleted Successfully")
        self.instance = None
      else:
        time.sleep(1)
        ctr += 1

    if self.instance:
      log("X", 2, "Unable to delete instance %s with ID.  Investigate." % (self.instanceName, self.instance.id))

    self.flavor.delete()
    time.sleep(1)

    ctr = 0
    while self.flavor and ctr < 30:
      try:
        self.flavor = self.client.flavors.find(name=self.flavorName)
      except novaExceptions.NotFound:
        log("+", 2, "HealthCheck Flavor \"%s\" Successfully deleted." % self.flavorName)
        self.flavor = None
      else:
        time.sleep(1)
        ctr += 1

    if self.flavor:
      log("X", 2, "HealthCheck Flavor \"%s\" was not deleted successfully, ID %s" % (self.flavorName, self.flavor.id))



    log(".", 1, "Nova Cleanup Complete")
    pass

####################################################################################################
class CinderHealthCheck():
  def __init__(self, ks, nv):

    self.volName    = "RPCHealthCheckVolume"

    self.client     = None
    self.volume     = None
    self.enabled    = False
    self.services   = []

    log(".", 1, "Cinder Init:")

    try:
      from cinderclient import client as cnClient
    except ImportError, err:
      raise RPCHCError("Could not import python cinderclient.  Please make sure python-cinderclient is installed.")

    try:
      self.client = cnClient.Client("1", **nv.credentials)
    except RPCHCError, err:
      raise

    # Check for offline services
    r = [self.client.services.list()]
    for i in r:
      for x in i:
        self.services.extend([{"host": x.host, "binary": x.binary, "status": x.status, "state": x.state}])
        if x.binary == "cinder-volume":
          self.enabled = True
        if x.state == "down" and x.status != "disabled":
          log("X", 2, "Cinder Service %s is %s on %s while marked \"%s\"" % (x.binary, x.state, x.host, x.status))

    volumes = self.client.volumes.list()

    for vol in volumes:
      if vol.display_name == self.volName:
        if vol.status != "available":
          raise RPCHCError("Volume \"%s\" already exists with ID %s, not available: %s" % (self.volName, vol.id, vol.status))
        else:
          log("W", 2, "Volume \"%s\" already exists with ID %s, status \"%s\".  Verify cleanup below." % (self.volName, vol.id, vol.status))
          self.volume = vol

    log(".", 1, "Cinder Init Complete")
    return

  #======================#
  def setup(self, ks, nv):
    log(".", 1, "Cinder Environment Prep:")

    if not self.volume:
      log(".", 2, "Creating new volume: %s" % self.volName)
      try:
        self.volume = self.client.volumes.create(1, display_name=self.volName, project_id=ks.tenant.id)
      except cinderExceptions, err:
        raise RPCHCError("Unable to create new volume: %s", err.message)
      else:
        ctr = 0
        while self.volume.status == "creating" and ctr < 30:
          time.sleep(1)
          self.volume = self.client.volumes.find(display_name=self.volName)
          ctr += 1

        if self.volume.status == "available":
          log("+", 2, "Created volume with ID %s, status %s" % (self.volume.id, self.volume.status))
        else:
          raise RPCHCError("New Cinder volume with ID %s is not in \"available\" status: %s" % (self.volume.id, self.volume.status))

    log(".", 1, "Cinder Environment Prep Complete")
    pass

  #======================#
  def run(self, ks, nv):
    log(".", 1, "Cinder Testing:")
    log(".", 2, "Attaching volume %s to instance %s" % (self.volume.id, nv.instance.id))

    self.volume.attach(nv.instance.id, "/dev/vdb")

    time.sleep(0.5)
    self.volume = self.client.volumes.find(display_name=self.volName)

    if self.volume.status == "in-use":
      log("+", 3, "Attachment successful")

    log(".", 1, "Cinder Testing Complete")
    pass

  #======================#
  def cleanup(self, ks, nv):
    log(".", 1, "Cinder Cleanup:")

    log(".", 2, "Detaching and deleting %s..." % (self.volName))

    self.volume.detach()
    self.volume.delete()

    ctr = 0
    while self.volume and ctr < 30:
      try:
        self.volume = self.client.volumes.find(status="deleting")
      except cinderExceptions.NotFound:
        log("+", 3, "HealthCheck Volume \"%s\" Successfully deleted." % self.volName)
        self.volume = None
      else:
        time.sleep(1)
        ctr += 1

    if self.volume:
      log("X", 3, "HealthCheck Volume \"%s\" was not deleted successfully, ID %s" % (self.volName, self.volume.id))

    log(".", 1, "Cinder Cleanup Complete")
    pass



####################################################################################################
class GlanceHealthCheck():

  def __init__(self, ks, nv):

    self.imageURL  = "http://cloud-images.ubuntu.com/saucy/current/saucy-server-cloudimg-amd64-disk1.img"
    self.imageFile = "/root/RPCHealthCheckImage.img"
    self.imageName = "RPCHealthCheckImage"
    self.snapName  = "RPCHealthCheckSnapshot"

    self.image     = None
    self.snapshot  = None
    self.snapID    = None
    self.client    = None

    log(".", 1, "Glance Init:")

    try:
     from glanceclient import Client as glanceClient
    except ImportError, err:
      raise RPCHCError("Unable to import python libraries for glance client.  Please make sure python-glanceclient is installed.")

    self.client = glanceClient("1", endpoint=ks.service["image"]["endpoints"][0]["adminURL"], token=ks.token)

    try:
      self.image = nv.client.images.find(name=self.imageName)
    except novaExceptions.NotFound:
      pass
    else:
      log("W", 2, "HealthCheck Image \"%s\" already exists with ID %s. Verify cleanup below." % (self.imageName, self.image.id))

    log(".", 1, "Glance Init Complete")
    return

  #======================#
  def setup(self, ks, nv):
    log(".", 1, "Glance Environment Prep:")

    if not self.image:

      log(".", 2, "Loading new image")

      if not os.access(self.imageFile, os.R_OK):
        log(".", 3, "Downloading from %s" % self.imageURL)
        try:
          r = urllib2.urlopen(self.imageURL)
          imageData = r.read()
          try:
            with open(self.imageFile, "w+") as fimg:
              fimg.write(imageData)
          except IOError, err:
            raise RPCHCError("Unable to write image to %s: %s", (self.imageFile, err.reason))
        except IOError, err:
          raise RPCHCError("Unable to download %s to %s: %s", (self.imageName, self.imageFile, err.reason))

      log(".", 3, "Importing from local file %s." % self.imageFile)

      try:
        with open(self.imageFile, "r") as fimg:
          self.client.images.create(name=self.imageName, is_public=False, disk_format="qcow2", container_format="bare", data=fimg)
      except IOError, err:
        raise RPCHCError("Unable to load local image: %s" % (err.reason))

    try:
      self.image = nv.client.images.find(name=self.imageName)
    except novaExceptions.NotFound:
      raise RPCHCError("Image \"%s\" not found after upload.  Check the logs." % (self.imageName))

    if self.image.status == "ACTIVE":
      log("+", 2, "HealthCheck Image \"%s\" in ACTIVE status with ID %s" % (self.imageName, self.image.id))
    else:
      raise RPCHCError("HealthCheck Image in \"%s\" status, not \"ACTIVE\"" % (self.image.status))

    log(".", 1, "Glance Environment Prep Complete")
    return

  #======================#
  def run(self, ks, nv):
    log(".", 1, "Glance Testing:")

    log(".", 2, "Creating Snapshot...")

    self.snapID = nv.instance.create_image(self.snapName)
    self.snapshot = nv.client.images.find(id=self.snapID)

    while self.snapshot.status == "SAVING":
      time.sleep(1)
      self.snapshot = nv.client.images.find(id=self.snapID)

    if self.snapshot.status == "ACTIVE":
      log("+", 3, "Snapshot created successfully.")
    else:
      log("X", 3, "Snapshot creation failed.  ID %s with status %s.  Investigate.")

    log(".", 1, "Glance Testing Complete")

    return
  #======================#
  def cleanup(self, ks, nv):
    log(".", 1, "Glance Cleanup:")

    self.image.delete()

    ctr = 0
    while self.image and ctr < 30:
      try:
        self.image = nv.client.images.find(name=self.imageName)
      except novaExceptions.NotFound:
        log("+", 2, "HealthCheck Image \"%s\" Successfully deleted." % self.imageName)
        self.image = None
      else:
        time.sleep(1)
        ctr += 1

    if self.image:
      log("X", 2, "HealthCheck Image \"%s\" was not deleted successfully, ID %s" % (self.imageName, self.image.id))

    self.snapshot.delete()

    ctr = 0
    while self.snapshot and ctr < 30:
      try:
        self.snapshot = nv.client.images.find(id=self.snapID)
      except novaExceptions.NotFound:
        log("+", 2, "HealthCheck Snapshot \"%s\" successfully deleted." % self.snapName)
        self.snapshot = None
      else:
        time.sleep(1)
        ctr += 1

    if self.snapshot:
      log("X", 2, "HealthCheck Snapshot \"%s\" was not deleted successfully, ID %s" % (self.snapName, self.snapshot.id))

    log(".", 1, "Glance Cleanup Complete")
    pass

####################################################################################################
def main():
  print ""
  log(".", 0, "Initializing Modules")

  keystone = None
  nova     = None
  glance   = None
  cinder   = None
  neutron  = None

  try:
    keystone = KeystoneHealthCheck()
  except RPCHCError, err:
    raise

  try:
    nova = NovaHealthCheck(keystone)
  except RPCHCError, err:
    raise

  try:
    glance = GlanceHealthCheck(keystone, nova)
  except RPCHCError, err:
    raise

  if "volume" in keystone.service.keys():
    try:
      cinder = CinderHealthCheck(keystone, nova)
    except RPCHCError, err:
      raise

  if "network" in keystone.service.keys():
    if keystone.service["network"]["name"] == "neutron":
      log(".", 1, "Found Neutron Networking")
      try:
        neutron = NeutronHealthCheck(keystone)
      except RPCHCError:
        raise

  if not neutron:
    raise RPCHCError("No neutron networking service defined in keystone.")

  #======================#
  # Set up all the things!
  print ""
  log(".", 0, "Configuring Environment")

  glance.setup(keystone, nova)
  neutron.setup(keystone, nova)
  nova.setup(keystone)
  if cinder.enabled:
    cinder.setup(keystone, nova)

  #======================#
  # Test all the things!
  print ""
  log(".", 0, "Testing Environment")

  nova.run(keystone, glance, neutron)
  neutron.run(nova)
  if cinder.enabled:
    cinder.run(keystone, nova)
  glance.run(keystone, nova)

  #======================#
  # Tear down all the things!
  print ""
  log(".", 0, "Cleaning Environment")

  glance.cleanup(keystone, nova)
  if cinder.enabled:
    cinder.cleanup(keystone, nova)
  nova.cleanup(keystone)
  neutron.cleanup()

  print ""
  log(".",0, "Checking Apache:")

  url = "https://%s/" % socket.gethostname()
  try:
    r = urllib2.urlopen(url)
  except (urllib2.URLError,urllib2.HTTPError), err:
    log("!", 1, "Error: %s %s" % (err.code, err.reason))

  str = r.read()

  # HTML output should have the keystone endpoint in a hidden field
  if keystone.service["identity"]["endpoints"][0]["publicURL"] in str:
    log("+",1, "Apache Success!")
  else:
    log("!",1, "Apache Failed.  Got: %s" % str)

  cmd = 'ip netns | grep vips > /dev/null 2>&1'
  result = subprocess.call(cmd, shell=True)

  isHA = 0
  if result == 0:
    isHA = 1

  if isHA:
    log(".",0, "Checking MySQL Replication:")
    cmd = 'mysql -e "show slave status \G" | egrep "Slave_(IO|SQL)_Running.*Yes" | wc -l | grep ^2$ > /dev/null 2>&1'
    result = subprocess.call(cmd, shell=True)
  
    if result == 0:
      log("+",1,"MySQL Slave OK on localhost.")
    else:
      log("!",1,"MySQL check failed.  Check slave replication.")
	
    cmd = 'ssh $( mysql -e "show slave status \G" | awk -F: \'/Master_Host/ {print $2}\') mysql -e "show\ slave\ status\ \\\\\G" | egrep "Slave_(IO|SQL)_Running.*Yes" | wc -l | grep ^2$ > /dev/null 2>&1'
    result = subprocess.call(cmd, shell=True)

    if result == 0:
      log("+",1,"MySQL Slave OK on remote replicant.")
    else:
      log("!",1,"MySQL check failed on remote replicant.: %s" % result)
  
  return

if __name__ == '__main__':
  r = True
  try:
    r = main()
  except KeyboardInterrupt:
    print "Keyboard Interrupt."
    r = 1
  except RPCHCError, err:
    log("!", 0, "%s" % err.msg)
    r = 1

  sys.exit(r)
