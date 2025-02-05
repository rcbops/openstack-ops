#!/usr/bin/env python3
import getpass
import json
import requests
import sys

requests.packages.urllib3.disable_warnings()


def racker_auth_pw():
    try:
        password = getpass.getpass("Password:")
    except KeyboardInterrupt:
        print("\nCtrl+C pressed, exiting...")
        sys.exit()

    url = "{}/v2.0/tokens".format(auth_ep)
    data = {
        "auth": {
            "RAX-AUTH:domain": {
                "name": "Rackspace",
            },
            "passwordCredentials": {
                "username": user,
                "password": password,
            },
        }
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    req = requests.post(url, data=json.dumps(data), headers=headers, verify=False)
    token = req.json()["access"]["token"]["id"]
    return token


def racker_auth_rsa():
    try:
        password = getpass.getpass("RSA token:")
    except KeyboardInterrupt:
        print("\nCtrl+C pressed, exiting...")
        sys.exit()

    url = "{}/v2.0/tokens".format(auth_ep)
    data = {
        "auth": {
            "RAX-AUTH:domain": {
                "name": "Rackspace",
            },
            "RAX-AUTH:rsaCredentials": {
                "username": user,
                "tokenKey": password,
            },
        }
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    req = requests.post(url, data=json.dumps(data), headers=headers, verify=False)
    token = req.json()["access"]["token"]["id"]
    return token


def get_admin_user(account, token):
    """
    Attempt to retrieve "admin" user instead of hybridACCT default
    See: https://github.com/racker/ele-kb/issues/274
    """
    url = "{}/v2.0/users?admin_only=True&tenant_id=hybrid:{}".format(auth_ep, account)
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Auth-Token": token,
    }
    req = requests.get(url, headers=headers)
    if req.status_code != 200:
        raise Exception(req.text)
    return req.json()["users"][0]["username"]


def impersonate(account, token):
    try:
        user = get_admin_user(account, token)
    except IndexError:
        user = "hybrid" + account

    url = "{}/v2.0/RAX-AUTH/impersonation-tokens".format(auth_ep)
    data = {
        "RAX-AUTH:impersonation": {
            "user": {
                "username": user,
            },
            "expire-in-seconds": 10800,
        }
    }
    headers = {
        "Content-type": "application/json",
        "X-Auth-Token": token,
    }
    req = requests.post(url, data=json.dumps(data), headers=headers, verify=False)
    return req.json()["access"]["token"]["id"]


def get_agent_token(account, token):
    url = "{}/v1.0/hybrid:{}/agent_tokens".format(mon_ep, account)
    headers = {
        "Content-type": "application/json",
        "X-Auth-Token": token,
    }
    req = requests.get(url, headers=headers, verify=False)
    try:
        agent_token = req.json()["values"][0]["token"]
    except IndexError:
        agent_token = "Missing agent token, please generate one"
    return agent_token


if __name__ == "__main__":
    auth_ep = "https://identity-internal.api.rackspacecloud.com"
    mon_ep = "https://monitoring.api.rackspacecloud.com"

    try:
        user = sys.argv[1]
        account = sys.argv[2]
    except IndexError:
        print("cloud-token <UserName> <Account-Num>")
        sys.exit(2)
    else:
        token = racker_auth_pw()
        sessionToken = impersonate(account, token)
        print("Impersonation Token: {}".format(sessionToken))
        print("Maas Agent Token: {}".format(get_agent_token(account, sessionToken)))
