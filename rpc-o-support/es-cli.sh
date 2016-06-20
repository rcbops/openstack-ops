#!/bin/bash
# 
# es-cli.sh: Search server logs from the comfort of your terminal!
#
# This is a command-line wrapper for Elasticsearch's RESTful API.
# This is super-beta, version .000001-alpha. Questions/comments/hatemail to Kale Stedman,
# I'm so sorry. You should probably pipe the output to less.
# 
# usage: ./es-cli.sh -u $USER -p $PASS -h es-hostname -q "$query" -t $time -n 500
# ex: ./es-cli.sh -u kstedman -p hunter2 -h es.hostname.com -q "program:crond" -t 5 -n 50
# 
# -h host      The Elasticsearch host you're trying to connect to.
# -u username  Optional: If your ES cluster is proxied through apache and you have http auth enabled, username goes here
# -p password  Optional: If your ES cluster is proxied through apache and you have http auth enabled, password goes here
# -q query     Optional: Query to pass to ES. If not given, "*" will be used.
# -t timeframe Optional: How far back to search. Value is in mimutes. If not given, defaults to 5.
# -n results   Optional: Number of results to return. If not given, defaults to 500.


# Declare usage fallback/exit
usage() { echo "Usage: $0 -h host [ -u USER ] [ -p PASS ] [ -q "QUERY" ] [ -t TIMEFRAME ] [ -n NUMRESULTS ]" 1>&2; exit 1; }

# Parse options
while getopts ":u:p:h:q:t:n:" o; do
    case "${o}" in
        u)
            u=${OPTARG}
            ;;
        p)
            p=${OPTARG}
            ;;
        h)
            h=${OPTARG}
            ;;
        q)
            q="${OPTARG}"
            ;;
        t)
            t=${OPTARG}
            ;;
        n)
            n=${OPTARG}
            ;;
        *)
            usage
            ;;
    esac
done
shift $((OPTIND-1))

if [ -z "${p}" ] && [ ! -z "${u}" ] ; then
  echo -n "Password: "
  read -s p
  echo
fi

# Check for required variables
if [ -z "${h}" ] ; then
    usage
fi

# Set defaults if not set
if [ -z "${n}" ] ; then
  # default: 500 results returned 
  n=500
fi

if [ -z "${q}" ] ; then
  # default: query "*"
  q="*"
fi

if [ -z "${t}" ] ; then
  # default: 5 minutes ago
  t="5"
fi

# cross-platform time compatibilities
FROMDATE=`python -c "from datetime import date, datetime, time, timedelta; print (datetime.now() - timedelta(minutes=${t})).strftime('%s')"`
NOWDATE=`python -c "from datetime import date, datetime, time, timedelta; print (datetime.now()).strftime('%s')"`
ZEROS="000"
NOW=${NOWDATE}${ZEROS}
FROM=${FROMDATE}${ZEROS}

# Build query
query="{\"query\":{\"filtered\":{\"query\":{\"bool\":{\"should\":[{\"query_string\":{\"query\":\"${q}\"}}]}},\"filter\":{\"bool\":{\"must\":[{\"range\":{\"@timestamp\":{\"from\":$FROM,\"to\":$NOW}}}]}}}},\"size\":${n},\"sort\":[{\"syslog_timestamp\":{\"order\":\"asc\"}}]}"

if [ ! -z "${u}" ] ; then
  up="${u}:${p}@"
else
  up=""
fi

# run query and prettify the output
URL="http://${up}${h}/_all/_search?pretty"
curl -s -XGET "${URL}" -d ''"${query}"'' | python -mjson.tool |grep '"message"' | awk -F\: -v OFS=':' '{ $1=""; print $0}' | sed -e 's/^: "//g' | sed -e 's/", $//g' | sed -e 's/\\n/\ /g'
