#!/usr/bin/env python2
import getpass
import json
import requests
import sys

requests.packages.urllib3.disable_warnings()


def racker_auth():
    password = getpass.getpass("Password: ")
    url = 'https://identity-internal.api.rackspacecloud.com/v2.0/tokens'
    data = {
        "auth": {
            "RAX-AUTH:domain": {
                "name": "Rackspace"
            },
            "passwordCredentials": {
                "username": user,
                "password": password
            }
        }
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    req = requests.post(url, data=json.dumps(data), headers=headers, verify=False)
    token = req.json()['access']['token']['id']
    print req.json()
    return token


def impersonate(account, token):
    url = ('https://identity-internal.api.rackspacecloud.com'
           '/v2.0/RAX-AUTH/impersonation-tokens')
    data = {
        "RAX-AUTH:impersonation": {
            "user": {
                "username": 'hybrid' + account
            },
            "expire-in-seconds": 10800
        }
    }
    headers = {
        "Content-type": "application/json",
        "X-Auth-Token": token
    }
    req = requests.post(url, data=json.dumps(data), headers=headers, verify=False)
    return req.json()['access']['token']['id']


def get_agent_token(account, token):
    url = ('https://monitoring.api.rackspacecloud.com'
           '/v1.0/hybrid:%s/agent_tokens' % account)
    headers = {
        "Content-type": "application/json",
        "X-Auth-Token": token
    }
    req = requests.get(url, headers=headers, verify=False)
    try:
        agent_token = req.json()['values'][0]['token']
    except IndexError:
        agent_token = "Missing, please generate one"
    return agent_token


if __name__ == '__main__':
    try:
        user = sys.argv[1]
        account = sys.argv[2]
    except IndexError:
        print ('cloud-token <UserName> <Account-Num>')
        sys.exit(2)
    else:
        token = racker_auth()
        # print token
        sessionToken = impersonate(account, token)
        print "Session Token: %s" % (sessionToken)
        print "Maas Agent Token: %s" % get_agent_token(account, sessionToken)
