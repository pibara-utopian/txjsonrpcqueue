#!/usr/bin/env python3
import json
from twisted.internet import reactor
import txjsonrpcqueue

class AppbaseTest(object):
    def __init__(self, callback):
        self.callback = callback
        self.testcount = 0
        self.results = dict()
    def add_command(self, api, condenser, call):
        def ok_fun(result):
            if not api in self.results:
                self.results[api] = dict()
            self.results[api][condenser] = True
        def fail_fun(err):
            if not api in self.results:
                self.results[api] = dict()
            self.results[api][condenser] =False
            #print(api, condenser, err)
        def finaly_fun(hmm=None):
            self.testcount -= 1
            if self.testcount == 0:
                self.callback(self.results)
        self.testcount +=1
        call.addCallbacks(ok_fun, fail_fun)
        call.addBoth(finaly_fun)

class Node(object):
    def __init__(self,url):
        self.url=url
        self.appbase = txjsonrpcqueue.WildcardQueue(low=8000, high=10000, namespace="condenser_api")
        self.forwarder = txjsonrpcqueue.RpcForwarder(queue=self.appbase, host_url=url)
    def test(self, callback):
        def cbwrapper(rval):
            callback(self.url,rval)
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

def print_result(url, result):
    print(url)
    for api in result:
        rescount = 0
        okcount = 0
        if True in result[api]:
            rescount += 1
            if result[api][True] == True:
                okcount += 1
        if False in result[api]:
            rescount += 1
            if result[api][False] == True:
                okcount += 1
        if rescount != okcount:
            if okcount == 0:
                print("+ FAILURE:", api)
            else:
                print("+ PARTIAL:", api)
        else:
            print("+ SUCCESS:", api)
            
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
    n1 = Node(node)
    n1.test(print_result)

reactor.run()
