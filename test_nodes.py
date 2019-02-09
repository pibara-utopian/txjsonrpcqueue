#!/usr/bin/env python3
import operator
import json
import logging
import time
from twisted.python import log
from twisted.internet import reactor
import txjsonrpcqueue

class AppbaseTest(object):
    def __init__(self, callback):
        self.callback = callback
        self.testcount = 0
        self.results = dict()
        self.results["bad_errors"] = list()
        self.start_time = time.time()
    def add_command(self, api, condenser, call):
        def ok_fun(result):
            if not api in self.results:
                self.results[api] = dict()
            self.results[api][condenser] = True
        def fail_fun(err):
            try:
                err.raiseException()
            except txjsonrpcqueue.exception.JsonRpcCommandError as exception:
                if not api in self.results:
                    self.results[api] = dict()
                self.results[api][condenser] =False
            except Exception as exception:
                if not api in self.results:
                    self.results[api] = dict()
                self.results[api][condenser] =False
                self.results["bad_errors"].append(exception)
        def finaly_fun(hmm=None):
            self.testcount -= 1
            if self.testcount == 0:
                duration = time.time() - self.start_time
                self.callback(self.results, duration)
        self.testcount +=1
        call.addCallbacks(ok_fun, fail_fun)
        call.addBoth(finaly_fun)

class ApiNodeMonitor(object):
    def __init__(self, url, callback, newurl):
        self.url=url
        self.callback = callback
        self.appbase = txjsonrpcqueue.WildcardQueue(low=8000, high=10000, namespace="condenser_api")
        self.forwarder = txjsonrpcqueue.RpcForwarder(queue=self.appbase, host_url=url)
        self.tick()
    def tick(self):
        def cbwrapper(rval, duration):
            self.callback(self.url, rval, duration)
            reactor.callLater(40, self.tick)
        abt = AppbaseTest(cbwrapper)
        abt.add_command(
            api="account_by_key", 
            condenser=True,
            call=self.appbase.condenser_api.get_key_references(
                ["STM7GQPbcb96hmX2jMJDSHVeNokm6WknjpSwjz1N4bMHxauRgW2HP"]))
        abt.add_command(
            api="account_by_key",
            condenser=False,
            call=self.appbase.account_by_key_api.get_key_references(
                keys=["STM7GQPbcb96hmX2jMJDSHVeNokm6WknjpSwjz1N4bMHxauRgW2HP"]))
        abt.add_command(
            api="account_history",
            condenser=True,
            call=self.appbase.condenser_api.get_account_history("mattockfs",-1,2))
        abt.add_command(
            api="account_history",
            condenser=False,
            call=self.appbase.account_history_api.get_account_history(account="mattockfs", start=-1, limit=2))
        abt.add_command(
            api="database",
            condenser=True,
            call=self.appbase.condenser_api.get_reward_fund("post"))
        abt.add_command(
            api="database",
            condenser=False,
            call=self.appbase.database_api.get_reward_funds())
        abt.add_command(
            api="follow",
            condenser=True,
            call=self.appbase.condenser_api.get_followers("mattockfs",None,"blog",2))
        abt.add_command(
            api="follow",
            condenser=False,
            call=self.appbase.follow_api.get_followers(account="mattockfs", start=None, type="blog", limit=2))
        abt.add_command(
            api="jsonrpc",
            condenser=False,
            call=self.appbase.jsonrpc.get_methods())
        abt.add_command(
            api="market_history",
            condenser=True,
            call=self.appbase.condenser_api.get_market_history(
                86400, "2019-01-01T00:00:00", "2018-02-01T00:00:00"))
        abt.add_command(
            api="market_history",
            condenser=False,
            call= self.appbase.market_history_api.get_market_history(
                bucket_seconds=86400,
                start="2019-01-01T00:00:00",
                end="2018-02-01T00:00:00"))
        abt.add_command(
            api="rc",
            condenser=False,
            call=self.appbase.rc_api.find_rc_accounts(accounts=["mattockfs"]))
        abt.add_command(
            api="reputation",
            condenser=True,
            call=self.appbase.condenser_api.get_account_reputations("mattockfs", 1))
        abt.add_command(
            api="reputation",
            condenser=False,
            call=self.appbase.reputation_api.get_account_reputations(account_lower_bound="mattockfs", limit=1))
        abt.add_command(
            api="tags",
            condenser=True,
            call=self.appbase.condenser_api.get_discussions_by_active({"tag":"fiction","limit":1}))
        abt.add_command(
            api="tags",
            condenser=False,
            call=self.appbase.tags_api.get_discussions_by_active(tag="fiction", limit=1))
        abt.add_command(
            api="block",
            condenser=True,
            call=self.appbase.condenser_api.get_block(30000000))
        abt.add_command(
            api="block",
            condenser=False,
            call=self.appbase.block_api.get_block(block_num=30000000))


class CurentResults(object):
    def __init__(self):
        self.api = dict()
        self.lastfail = dict()
        self.lastupdate = dict()
        self.speed_array = dict()
        self.speed = dict()
        for api in ["account_by_key", "account_history", "database", "follow", "jsonrpc", "market_history", "rc", "reputation", "tags", "block"]:
            self.api[api] = set()
    def process_node_results(self, url, result, duration):
        now = time.time()
        self.lastupdate[url] = now
        if result["bad_errors"]:
            print(url,result["bad_errors"][0])
            self.lastfail[url] = now
            if url in self.speed:
                del self.speed[url]
            for api in self.api.keys():
                if "C" + url in self.api[api]:
                    self.api[api].remove("C" + url)
                if "N" + url in self.api[api]:
                    self.api[api].remove("N" + url)
                if "A" + url in self.api[api]:
                    self.api[api].remove("A" + url)
            self.speed_array[url] = list()
        else:
            if not url in self.speed_array:
                self.speed_array[url] = list()
            self.speed_array[url].append(duration)
            self.speed_array[url] = self.speed_array[url][-10:]
            tspeed = 0
            for speed in self.speed_array[url]:
                tspeed += speed
            self.speed[url] = tspeed / len(self.speed_array[url])
            for api in result:
                if api != "bad_errors":
                    cond_ok = False
                    nsap_ok = False
                    any_ok = False
                    if True in result[api] and result[api][True]:
                        cond_ok = True
                    if False in result[api] and result[api][False]:
                        nsap_ok = True
                    if not True in result[api] and nsap_ok:
                        cond_ok = True
                    if not False in result[api] and cond_ok:
                        nsap_ok = True
                    if cond_ok or nsap_ok:
                        any_ok = True
                    if cond_ok:
                        self.api[api].add("C" + url)
                    if nsap_ok:
                        self.api[api].add("N" + url)
                    if any_ok:
                        self.api[api].add("A" + url)
        self.lookup(["block"], "A")
    def lookup(self, api_list, prefix):
        sets = list()
        for api in api_list:
            if api in self.api.keys():
                sets.append(self.api[api])
        if sets:
            api_set = sets.pop(0)
            for sn in sets:
                api_set = api_set.intersection(sn)
            results = list()
            for api in api_set:
                if api[0] == prefix:
                    key = api[1:]
                    val = self.speed[key]
                    results.append([key, val])
            results = [i[0] for i in sorted(results, key=operator.itemgetter(1))]
            print(results)

def new_url(url):
    pass

log.PythonLoggingObserver().start()
logging.basicConfig(filename="test_nodes.log", level=logging.DEBUG)
cr = CurentResults()


nodes = ["https://steemd.minnowsupportproject.org",
         "https://rpc.usesteem.com",
         "https://rpc.steemviz.com",
         "https://anyx.io",
         "https://api.steemitdev.com",
         "https://api.steem.house",
         "https://appbasetest.timcliff.com",
         "https://steemd.privex.io",
         "https://api.steemit.com",
         "https://rpc.curiesteem.com",
         "https://rpc.steemliberator.com",
         "https://api.steemitstage.com",
         "https://gtg.steem.house:8090"]
for node in nodes:
    n1 = ApiNodeMonitor(node, cr.process_node_results, new_url)




reactor.run()
