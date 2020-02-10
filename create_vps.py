# Application imports
import argparse
import json
import vultr
import time

# Constants
#: CONSTANT : The target OS that needs to be installed.
TARGET_OS = 'Debian 10 x64 (buster)'
#: CONSTANT : The target price that the VPS will be billed at.
TARGET_PLAN_PRICE = '5.00'
#: CONSTANT : The target datacenter that the VPS will be spawned in.
TARGET_DATACENTER = 'Toronto'
#: CONSTANT : The hostname and label attached to the server.
HOSTNAME = 'bgp-coldnorthadmin'
#: CONSTANT: The name of the desired SSH key.
TARGET_SSHKEY = 'bgp-coldnorthadmin'


class MaxServerAlreadyRunning(Exception):
  """Raised when we already have one server running."""
  pass


class GenericMissingAttribute(Exception):
  """We tried to find a VPS atttribute and nothing returned from Vultr was matched"""
  pass


def check_return_value(value, message):
  """Will raise a GenericMissingAttribute if the value is None
  
  Arguments:
      value {Dict} -- The value to check to None
      message {str} -- The message to output of the Exception is raised
  
  Raises:
      GenericMissingAttribute: The Generic Exception raised if the value is None
  """
  if value is None:
    raise GenericMissingAttribute(message)


def get_limit_running_servers(servers_dict):
  """Ensure that we only have one server running at the same time

  Arguments:
      servers_dict {DICT} -- Dict of currently running servers.
  
  Returns:
      Boolean -- Return True if the condition is respected - False if we already have more than one running.
  """
  if len(servers_dict) >= 1:
    raise MaxServerAlreadyRunning("Maximum servers currently running")
  return True


def get_ssh_key(ssh_keys_dict):
  """Expects a dict that contains a tuple of STR, DICT and returns a dict that the matches the TARGET_SSHKEY
  
  Arguments:
      sshkeys_dict {DICT} -- Dict if currently existing SSH keys.
  
  Returns:
      dict -- Dictionary of the sshkey matching the TARGET_SSHKEY constant.
  """
  target_ssh_key = None

  for ssh_key in ssh_keys_dict.items():
    (key_id, key_details) = ssh_key
    if key_details['name'] == TARGET_SSHKEY:
      target_ssh_key = key_details

  check_return_value(target_ssh_key, "We tried to find: {} and nothing matched from Vultr".format(TARGET_SSHKEY))

  return target_ssh_key


def get_plan(plans_dict):
  """Expects a dict that contains a tuple of STR, DICT and returns a dict that matches the TARGET_PLAN_PRICE.
  DICT OF TUPLES --> TUPLES OF STR, DICT --> DICT
  
  Arguments:
      plans_dict {DICT} -- Dictionary of VULTR VPS plans (containing machine specs and prices).
  
  Returns:
      target_plan -- Dictionary of the plan matching the TARGET_PLAN_PRICE constant.
  """

  target_plan = None

  for plan in plans_dict.items():
    if plan[1]['price_per_month'] == TARGET_PLAN_PRICE:
      target_plan = plan[1]

  check_return_value(target_plan, "We tried to find: {} and nothing matched from Vultr".format(TARGET_PLAN_PRICE))

  return target_plan


def get_os(os_dict):
  """Expects a dict that contains a tuple of STR, DICT and returns a dict that matches the TARGET_OS.
  DICT OF TUPLES --> TUPLES OF STR, DICT --> DICT
  
  Arguments:
      os_dict {DICT} -- Dictionary of VULTR OS
  
  Returns:
      target_os -- Dictionary of the plan matching the TARGET_OS constant.
  """

  for os in os_dict.items():
    (osid, os_details) = os
    if os_details['name'] == TARGET_OS:
      target_os = os_details
  
  check_return_value(target_os, "We tried to find: {} and nothing matched from Vultr".format(TARGET_OS))

  return target_os


def get_datacenter(regions_dict):
  """Expects a dict that contains a tuple of STR, DICT and returns a dict that matches the TARGET_DATACENTER.
  DICT OF TUPLES --> TUPLES OF STR, DICT --> DICT
  
  Arguments:
      regions_dict {DICT} -- Dictionary of VULTR datacenter regions
  
  Returns:
      target_datacenter -- Dictionary of the plan matching the TARGET_DATACENTER constant.
  """

  for datacenter in regions_dict.items():
    if datacenter[1]['name'] == TARGET_DATACENTER:
      target_datacenter = datacenter[1]

  check_return_value(target_datacenter, "We tried to find: {} and nothing matched from Vultr".format(TARGET_DATACENTER))

  return target_datacenter


def poll_server(vultr_client):
  """Poll the server status API and return if the server is ready to be  used
  
  Arguments:
      vultr_client {vultr client object} -- Vultr client for API access
  """
  server_state = False
  timeout = 0

  while server_state is not True and timeout < 10:
    time.sleep(2)
    servers_dict = vultr_client.server.list()
    # Sleep two seconds so that we don't get rate-limited or banned by Vultr
    if len(servers_dict) == 0:
      print('There are no servers currently running or shutdown')
      timeout += 1
    else:
      for server in servers_dict.items():
        (server_id, server_details) = server
        if server_details['label'] == HOSTNAME:
          if server_details['status'] != 'active' or server_details['server_state'] != 'ok':
            print('Expecting STATUS "ACTIVE" and SERVER_STATE "OK" but Vultr returned: {} and {}'.format(server_details['status'], server_details['server_state']))
          else:
            server_state = True
  else:
    print('Server is Ready!')


def main():
  parser = argparse.ArgumentParser(description='Automate the creation of Vultr VPS')
  parser.add_argument('api_key', type=str, help='API key for Vultr')
  args = parser.parse_args()
  vultr_api_key = args.api_key

  vultr_client = vultr.Vultr(vultr_api_key)
  
  # Make sure we really only have one server to prevent overbilling.
  servers_dict = vultr_client.server.list()
  get_limit_running_servers(servers_dict)
  
  # Get the current ID for required instantiation variables.
  plans_dict = vultr_client.plans.list()
  os_dict = vultr_client.os.list()
  regions_dict = vultr_client.regions.list()
  ssh_keys_dict = vultr_client.sshkey.list()
  
  target_plan = get_plan(plans_dict)
  target_os = get_os(os_dict)
  target_datacenter = get_datacenter(regions_dict)
  target_ssh_key = get_ssh_key(ssh_keys_dict)

  # Create the server
  print("Creating server now")
  server = vultr_client.server.create(target_datacenter['DCID'], target_plan['VPSPLANID'], target_os['OSID'], {'hostname': HOSTNAME, 'label': HOSTNAME, 'SSHKEYID' : target_ssh_key['SSHKEYID']})
  poll_server(vultr_client)



if __name__ == '__main__':
  main()
