#!/usr/bin/env python

# Having a python lib is nice and all, but I just need basic search
# functionality...so...straight to the API.
#

import urllib
import urllib2
import json
import argparse
import socket
import re
import datetime as dt

from time import sleep

def main():

  parser = argparse.ArgumentParser(
    description="RPC Elastic Search Client.  You know, for kids.")

  parser.add_argument("-u",
                dest="url",
                type=str,
                metavar="http://<host>:<port>/_search",
                help="Elasticsearch URL")

  parser.add_argument("-n",
                dest="numLogs",
                type=int,
                metavar="num",
                help="Number of logs",
                default=20)

  parser.add_argument("-f",
                dest="follow",
                action="store_true",
                help="Live tail of matching logs")

  parser.add_argument("-x",
                dest="extendedOutput",
                action="store_true",
                help="Extended output")

  parser.add_argument("-X",
                dest="extendedMatches",
                action="append",
                type=str,
                metavar="key=val",
                help="Match on arbitrary log fields, see output of -x")

  parser.add_argument("-t",
                dest="tags",
                type=str,
                action="append",
                metavar="tag",
                help="Tag filters, shortcut for -X tags=<tag>")

  parser.add_argument("--debug",
                dest="debug",
                action="store_true",
                help="More unnecessary output!")

  parser.add_argument("optArgs",
                type=str,
                nargs="*",
                metavar="<searchString>",
                help="Text Search",
                default="*")

  args = parser.parse_args()

  if not args.url:
    with open("/etc/hosts","r") as fp:
      hosts = fp.read().split("\n")

    for host in hosts:
      if "elasticsearch" in host:
        esIP = host.split(" ")[0]

    if not esIP:
      raise KeyError("Could not find elasticsearch container IP, and you didn't supply a --url. Giving Up.")
    else:
      esURL = "http://%s:9200/_search" % esIP
      print "[Found Elasticsearch at %s]" % esURL
  else:
    esURL = args.url

    # helper
    if "_search" not in esURL:
      esURL += "/_search"

  
  q={
    "query" : {
      "filtered": {
        "query": {
          "bool":{
            "must" : [
              {"query_string":{"query":" AND ".join(args.optArgs)}}
            ],
          }
        },
      }
    },
    "sort": [
      {"@timestamp":{"order":"desc"}}
    ],
  }

  if args.extendedMatches:
    for pair in args.extendedMatches:
      try:
        (key,val) = pair.split("=")
      except ValueError:
        raise

      q['query']['filtered']['query']['bool']['must'].extend(
        [ { "match" : { key : val } } ])

  if args.tags:
    for tag in args.tags:
      q['query']['filtered']['query']['bool']['must'].extend(
        [ { "term" : { "tags" : tag } } ])

  if args.numLogs > 0:
    q["size"] = args.numLogs

  #handler=urllib2.HTTPHandler(debuglevel=1)
  #opener = urllib2.build_opener(handler)
  #urllib2.install_opener(opener)

  if args.debug:
    print "QUERY: %s" %q 

  data = urllib.urlencode({'q':q})
  req = urllib2.Request(esURL, json.dumps(q))
  r = urllib2.urlopen(req)

  searchReply = json.loads(r.read())

  # Update the query for recurring -f if needed
  hits = searchReply['hits']['hits']
  lastIndex = searchReply['hits']['total']
  q['from'] = lastIndex
  q['sort'][0]['@timestamp']['order'] = "asc"
  del q['size']

  logs = sorted(hits, key=lambda x: x['_source']['message'])

  for i in logs:
    i = i['_source']
    print i['message']
    if args.extendedOutput:
      print "[ %s ]" % i
      print ""

  if args.follow:
    while True:
      sleep(1)

      if args.debug:
        print "QUERY: %s" % q 

      req = urllib2.Request(esURL, json.dumps(q))
      r = urllib2.urlopen(req)
      searchReply = json.loads(r.read())

      hits = searchReply['hits']['hits']
      lastIndex = searchReply['hits']['total']
      q['from'] = lastIndex

      logs = sorted(hits, key=lambda x: x['_source']['message'])

      for i in logs:
        i = i['_source']
        print i['message']
        if args.extendedOutput:
          print "[ %s ]" % i
          print ""

if __name__ == '__main__':
  try:
    main()
  except KeyboardInterrupt:
    print "TRL-C"
  except (
    KeyError,
    ValueError
  ), err:
    print err
