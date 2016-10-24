escape.py
-----------

Provides command line access to Elasticsearch in RPC environments.

> This script has been seen to work fairly well in RPC11 and RPC12
> environments, and can tolerate being used in RPC10, but don't really
> bet on it.

**CURRENTLY BETA**

```
$ python ./escape.py  -h
usage: escape.py [-h] [--host host[:port]] [-n num] [-d [1]]
                 [-s YYYY-MM-DD [HH[:MM[:SS]]]] [-e YYYY-MM-DD [HH[:MM[:SS]]]]
                 [-f] [-x] [-X key=val] [-t tag] [--debug]
                 [<searchString> [<searchString> ...]]

RPC Elastic Search Client. You know, for kids.

positional arguments:
  <searchString>        Text Search

optional arguments:
  -h, --help            show this help message and exit
  --host host[:port]    Elasticsearch URL
  -n num                Limit to X most recent logs.
  -d [1]                Number of days to search. 0 for all.
  -s YYYY-MM-DD [HH[:MM[:SS]]]
                        Start time. Overrides -d.
  -e YYYY-MM-DD [HH[:MM[:SS]]]
                        End time. Default now.
  -f                    Live tail of matching logs
  -x                    Extended output
  -X key=val            Match on arbitrary log fields, see output of -x
  -t tag                Tag filters, shortcut for -X tags=<tag>
  --debug               More unnecessary output!
```

On initialization, the script will attempt to auto-detect the
elasticsearch URL in the environment based on entries in /etc/hosts.
The last entry in the file matching 'elasticsearch' is used with port
:9200.  You can specify a different IP/port using --host.

By default, escape.py will show you the last day's worth of logs.  This is
probably way too much, and not really what you want.  You need to narrow
it down (or expand, as necessary).

> **It should be kept in mind that unless you specify -s or -d, that you are
> only searching for logs within the last day.**  If you are looking for something
> specific, and are not finding it, you may have to extend the search further
> back in time.

## How2UseIt?

The most simple way to use it would be to just feed it a search term:

```
$ ./escape.py something
```

You can see just the last X logs by using -n:

```
$ ./escape.py -n50 something
```

You can narrow it down further using tags:

```
$ ./escape.py -n50 -t nova something
```

Tags are defined when the logs are inserted into elasticsearch, and are fairly broad,
typically.  You can see what tags are available by viewing extended log information:

```
$ ./escape.py -n50 -t nova -x something
```

You can use tags to filter by the log metadata shown by the -x flag:

```
$ ./escape.py -n50 -t nova -X loglevel=ERROR something
[...]

$ ./escape.py -n50 -t nova -X host=172.16.243.13 something
```

**Probably the best thing ever** is that you can perform a live tail on any matching logs
for the search you specify...

```
$ ./escape.py -n50 -t nova -X loglevel=ERROR -f something
```

This will show you the last 50 ERROR logs tagged with 'nova' also matching 'something',
then will keep the terminal open to display any further logs that come in after your
initial request.  It's like 'tail -f log | grep'...but...you know...for elasticsearch.


## Some Tips

It is best to keep the number of documents being searched to a minimum in order to
be nice to elasticsearch and so that you get the results you want in a timely manner.  To
this end, the script will, by default, only search within the last day of logs.  If you
need information previous to that, you may push this limit back using a simple number of
days:

```
$ ./escape.py -d7 -t nova something
```

or you can specify a start date:

```
$ ./escape.py -s '2016-10-10'
```

Timestamps for date options are somewhat forgiving, in that you only need to specify, at
a minimum, YYYY-MM-DD.  You can also specify HH, or HH:MM, or HH:MM:SS, and they all
work:

```
$ ./escape.py -s '2016-10-10'
# Midnight on October 10th 2016

$ ./escape.py -s '2016-10-10 12'
# Noon on October 10th 2016

$ ./escape.py -s '2016-10-10 12:30'
# You get the idea
```

If you specify a starting time that is more than a few days back, you may also want to
consider adding an -e (endDate) to your query to limit the number of documents being
searched.  Just saying.  Things can be slow when you don't limit the date range of your 
searches.


## Troubleshooting

So, you've searched for something and didn't get any results, or maybe you got a 404 error.
In that case, you can do a couple of things to make sure logstash and elasticsearch are 
working together properly.

First, try viewing the indexes in elasticsearch using curl.  You can grab the elasticsearch
URL from the output of escape:

```
$ ./escape.py -n1
Found Elasticsearch at http://172.19.62.217:9200/]
Searching.....^CTRL-C

$ curl http://172.19.62.217:9200/_aliases
```

The curl command should return a json list of indexes.  You should see a bunch of things
like 'logstash-YYY.MM.DD' where YYYY.MM.DD are recent dates.  If not, then there is most
likely an issue between logstash and elasticsearch.

Next, you can verify that logs are being stored within the indexes.

```
$ curl http://172.19.62.217:9200/_search
```

This should return a json-formatting document with 10 logs in it.  You can pipe to 'jq' 
to view the lots real pretty-like:

```
$ curl http://172.19.62.217:9200/_search | jq .hits.hits
```

If you are seeing results come back here, make sure that your original query that led you
down this path is actually something that should return results.  If it is, and you're certain
you're not just wasting everyone's time here, please open a bug report on escape.py and send 
me an e-mail @ aaron.segura@rackspace.com
