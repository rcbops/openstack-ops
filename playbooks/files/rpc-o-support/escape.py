#!/usr/bin/env python

# Having a python lib is nice and all, but I just need basic search
# functionality...so...straight to the API.
#

import urllib
import urllib2
import json
import argparse
import re
import datetime as dt
import sys
import random

from time import sleep
from collections import deque


def mkRequest(url, query, debug=False):
    # handler=urllib2.HTTPHandler(debuglevel=1)
    # opener = urllib2.build_opener(handler)
    # urllib2.install_opener(opener)

    if isinstance(query, dict):
        data = json.dumps(query)
    else:
        data = query

    if debug:
        print "%s\n\n%s\n" % (url, query)

    req = urllib2.Request(url, data)

    try:
        r = urllib2.urlopen(req)
    except urllib2.HTTPError:
        raise

    return json.loads(r.read())


def writeLogs(logs, extended=False):
    for i in logs:
        i = i['_source']

        if 'message' in i:
            print i['message']
        else:
            if '@message' in i:
                timeStrings = re.findall('[0-9]+', i['@timestamp'])
                timeNumbers = [int(x) for x in timeStrings]
                timeDT = dt.datetime(*timeNumbers)

                print "%s %s" % (timeDT.strftime("%Y-%m-%d %H:%M:%S"), i['@message'])

        if extended:
            print "[ %s ]" % i
            print ""


def main():
    nowDT = dt.datetime.now()
    oneDay = dt.timedelta(days=1)

    parser = argparse.ArgumentParser(
        description="RPC Elastic Search Client.  You know, for kids.")

    parser.add_argument("--host",
                        dest="host",
                        type=str,
                        metavar="host[:port]",
                        help="Elasticsearch URL")

    parser.add_argument("-n",
                        dest="numLogs",
                        type=int,
                        metavar="num",
                        help="Limit to X most recent logs.")

    parser.add_argument("-d",
                        dest="daysAgo",
                        type=int,
                        metavar="[1]",
                        help="Number of days to search. 0 for all.",
                        default=1)

    parser.add_argument("-s",
                        dest="startTime",
                        metavar="YYYY-MM-DD [HH[:MM[:SS]]]",
                        help="Start time.  Overrides -d.")

    parser.add_argument("-e",
                        dest="endTime",
                        metavar="YYYY-MM-DD [HH[:MM[:SS]]]",
                        help="End time. Default now.")

    parser.add_argument("-f",
                        dest="follow",
                        action="store_true",
                        help="Live tail of matching logs")

    parser.add_argument("-x",
                        dest="extendedOutput",
                        action="store_true",
                        help="Extended output showing log metadata")

    parser.add_argument("-X",
                        dest="extendedMatches",
                        action="append",
                        type=str,
                        metavar="key=val",
                        help="Match on log metadata, see output of -x")

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

    # Massage the date stuff
    if args.startTime:
        startTimeStr = re.findall("[0-9]+", args.startTime)
        startTimeVals = (int(x) for x in startTimeStr)
        startTimeDT = dt.datetime(*startTimeVals)

        if args.debug:
            print "StartTime: %s " % startTimeDT

    else:
        startTimeDT = dt.datetime.now() - dt.timedelta(days=args.daysAgo)

    if args.endTime:
        endTimeStr = re.findall("[0-9]+", args.endTime)
        endTimeVals = (int(x) for x in endTimeStr)
        endTimeDT = dt.datetime(*endTimeVals)

        if len(endTimeStr) == 3:  # should include the specified day
            endTimeDT = endTimeDT.replace(hour=23, minute=59, second=59)

        if args.follow:
            raise ValueError("It is improper to use -f with -e.")
    else:
        endTimeDT = nowDT

    # Generate index list.
    indices = []
    indexTimeDT = endTimeDT
    while indexTimeDT >= startTimeDT:
        indices.extend([indexTimeDT.strftime("logstash-%Y.%m.%d")])
        indexTimeDT -= oneDay

    # Too many or to few indexes?
    if len(indices) > 50 or len(indices) == 0:
        indices = ["_all"]
        print "! Date range too long for URL indexes.  Searching all documents."

    # Auto-detect elasticsearch container address and build URL
    esIP = None
    if not args.host:
        with open("/etc/hosts", "r") as fp:
            hosts = fp.read().split("\n")

        for host in hosts:
            if "elasticsearch" in host:
                esIP = host.split(" ")[0]
                esPort = 9200
    else:
        if ":" in args.host:
            (esIP, esPort) = args.host.split(":")
        else:
            esIP = args.host
            esPort = 9200

    if not esIP:
        raise KeyError("Could not find elasticsearch container IP, and you didn't supply --host. Giving Up.")

    esURL = "http://%s:%s/" % (esIP, esPort) + ",".join(indices) + "/_search"
    scrollURL = "http://%s:%s/" % (esIP, esPort) + ",".join(indices) + "/_search?scroll=5s"

    print "Found Elasticsearch at http://%s:%s/]" % (esIP, esPort)

    # Elasticsearch queries are weird.
    q = {
        "query": {
            "filtered": {
                "query": {
                    "bool": {
                        "must": [
                            {"query_string": {"query": " AND ".join(args.optArgs)}},
                            {"range": {"@timestamp": {"gte": startTimeDT.strftime("%s000")}}}
                        ],
                    }
                },
            }
        },
        "sort": [
            {"@timestamp": {"order": "asc"}}
        ],
        "size": 2500
    }

    # Add an endtime if specified
    if args.endTime:
        q['query']['filtered']['query']['bool']['must'].extend(
            [{"range": {"@timestamp": {"lte": endTimeDT.strftime("%s000")}}}])

    # Build extra conditions and append them to the ^query
    if args.extendedMatches:
        for pair in args.extendedMatches:
            try:
                (key, val) = pair.split("=")
            except ValueError:
                raise

            q['query']['filtered']['query']['bool']['must'].extend(
                [{"match": {key: val}}])

    # Specialized -t handling for tags: [x,x,x]
    if args.tags:
        for tag in args.tags:
            q['query']['filtered']['query']['bool']['must'].extend(
                [{"term": {"tags": tag}}])

    sys.stdout.write("Searching...")
    sys.stdout.flush()

    try:
        searchReply = mkRequest(scrollURL, q, args.debug)
    except:
        raise

    if not args.numLogs:
        print ""

    hits = searchReply['hits']['hits']
    numHits = searchReply['hits']['total']

    if args.numLogs:
        if len(hits) <= args.numLogs:
            logs = sorted(hits, key=lambda x: x['_source']['@timestamp'])
            print ""
            writeLogs(logs, args.extendedOutput)
        else:
            q['from'] = numHits - args.numLogs
            try:
                searchReply = mkRequest(esURL, q, args.debug)
            except:
                raise

            hits = searchReply['hits']['hits']
            logs = sorted(hits, key=lambda x: x['_source']['@timestamp'])
            print ""
            writeLogs(logs, args.extendedOutput)
    else:
        scrollURL = "http://" + esIP + ":" + str(esPort) + "/_search/scroll?scroll=5s"
        logs = sorted(hits, key=lambda x: x['_source']['@timestamp'])

        while len(hits):
            if args.numLogs:
                if random.randrange(0, 100) > 75:
                    sys.stdout.write(".")
                    sys.stdout.flush()
                for i in hits:
                    displayLogs.append(i)
            else:
                print ""
                writeLogs(logs, args.extendedOutput)

            searchReply = mkRequest(scrollURL, searchReply['_scroll_id'], args.debug)

            hits = searchReply['hits']['hits']
            logs = sorted(hits, key=lambda x: x['_source']['@timestamp'])

    q['from'] = numHits

    if args.follow:
        while True:
            sleep(1)

            try:
                searchReply = mkRequest(esURL, q, args.debug)
            except:
                raise

            hits = searchReply['hits']['hits']
            q['from'] = searchReply['hits']['total']

            logs = sorted(hits, key=lambda x: x['_source']['message'])
            writeLogs(logs, args.extendedOutput)


if __name__ == '__main__':
    try:
        main()
        print ""
    except KeyboardInterrupt:
        print "TRL-C"
    except (
            KeyError,
            ValueError,
    ), err:
        print "Error: %s" % err.message
    except urllib2.HTTPError, err:
        print "Request Error: %s" % err
