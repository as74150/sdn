# coding:utf-8
# Copyright (C) 2011 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from ryu.base import app_manager
from ryu.controller import mac_to_port
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.mac import haddr_to_bin
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib import mac
from ryu.topology.api import get_switch, get_link, get_host
from ryu.app.wsgi import ControllerBase
from ryu.topology import event, switches


from ryu.lib.packet import arp
 

import networkx as nx
import matplotlib.pyplot as plt
from ryu.lib import hub


class ProjectController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(ProjectController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}

        self.topology_api_app = self
        self.net = nx.DiGraph()
        self.nodes = {}
        self.links = {}
        self.no_of_nodes = 0
        self.no_of_links = 0
	    self.dps = []
        self.i = 0
	self.threads.append(
            hub.spawn(self._topo_local_sync, 5))
	self.is_active = True
	self.dict_paths = {}
        print "**********ProjectController __init__"

    def printG(self):
        G = self.net
        print "G"
        print "nodes", G.nodes()  # 输出全部的节点： [1, 2, 3]
        print "edges", G.edges()  # 输出全部的边：[(2, 3)]
        print "number_of_edges", G.number_of_edges()  # 输出边的数量：1
        #for e in G.edges():
            #print G.get_edge_data(e[0], e[1])

    # Handy function that lists all attributes in the given object
    def ls(self, obj):
        print("\n".join([x for x in dir(obj) if x[0] != "_"]))

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        print "\n-----------switch_features_handler is called"

        msg = ev.msg
        print 'OFPSwitchFeatures received: datapath_id=0x%016x n_buffers=%d n_tables=%d auxiliary_id=%d capabilities=0x%08x' % (
            msg.datapath_id, msg.n_buffers, msg.n_tables, msg.auxiliary_id, msg.capabilities)

        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = datapath.ofproto_parser.OFPFlowMod(
            datapath=datapath, match=match, cookie=0,
            command=ofproto.OFPFC_ADD, idle_timeout=0, hard_timeout=0, priority=0, instructions=inst)
        datapath.send_msg(mod)
        print "switch_features_handler is over"
	try:
	    self.dps.append(datapath)
	except Exception, e:
	    print str(e)


    def adddict(self,targetDict,src,dst,val):
	if src in targetDict:
	    targetDict[src].update({dst:val})
	else:
	    targetDict.update({src:{dst:val}})

    def isIndict(self,targetDict,src,dst):
	target = False
	if src in targetDict:
	    if dst in targetDict[src]:
		target = True
	return target

    def _topo_local_sync(self, interval):
        while self.is_active:
 	    self.net = nx.DiGraph()
 	    switch_list = get_switch(self.topology_api_app, None)
            switches = [switch.dp.id for switch in switch_list]
            self.net.add_nodes_from(switches)
 	    
 	    links_list = get_link(self.topology_api_app, None)
 	    links = [(link.src.dpid, link.dst.dpid, {'port': link.src.port_no}) for link in links_list]
 	    self.net.add_edges_from(links)
 	    links = [(link.dst.dpid, link.src.dpid, {'port': link.dst.port_no}) for link in links_list]
 	    self.net.add_edges_from(links)
 
 	    hosts_list = get_host(self.topology_api_app, None)
 	    for host in hosts_list:
 	        self.net.add_node(host.mac)
                self.net.add_edge(host.port.dpid, host.mac, port=host.port.port_no, weight=0)
                self.net.add_edge(host.mac, host.port.dpid, weight=0)
	    self.printG()
	    print '' 
            hub.sleep(interval)

    def add_flow(self, datapath, in_port, dst, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = datapath.ofproto_parser.OFPMatch(in_port=in_port, eth_dst=dst)
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = datapath.ofproto_parser.OFPFlowMod(
            datapath=datapath, match=match, cookie=0,
            command=ofproto.OFPFC_ADD, idle_timeout=0, hard_timeout=0,
            priority=ofproto.OFP_DEFAULT_PRIORITY, instructions=inst)
        datapath.send_msg(mod)


    #mac learning
    def mac_learning(self, datapath, src, in_port):
        self.mac_to_port.setdefault((datapath,datapath.id), {})
        # learn a mac address to avoid FLOOD next time.
        if src in self.mac_to_port[(datapath,datapath.id)]:
            if in_port != self.mac_to_port[(datapath,datapath.id)][src]:
                return False
        else:
            self.mac_to_port[(datapath,datapath.id)][src] = in_port
            return True

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # print "**********_packet_in_handler"

        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return

        #if eth.ethertype == ether_types.ETH_TYPE_IPV6:
            # ignore ipv6 packet
         #   return

        dst = eth.dst
        src = eth.src
        dpid = datapath.id

	self.mac_learning(datapath, src, in_port)

        if dst in self.net:

            G= self.net
	    if self.isIndict(self.dict_paths,src,dst) == False:
                path = nx.shortest_path(self.net, src, dst, weight="weight")
		self.adddict(self.dict_paths,src,dst,path)
		tmpPath = list(reversed(path))
		self.adddict(self.dict_paths,dst,src,tmpPath)
	    else:
		path = self.dict_paths[src][dst]
	    print path

            next = path[path.index(dpid) + 1]
            out_port = self.net[dpid][next]['port']
	
	else:
            if self.mac_learning(datapath, src, in_port) is False:
		out_port = ofproto.OFPPC_NO_RECV
		out_port = ofproto.OFPP_FLOOD
		return None
	    else:
                out_port = ofproto.OFPP_FLOOD
	actions = [parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
	    match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
            self.add_flow(datapath, in_port, dst, actions)
	    
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data
        out = datapath.ofproto_parser.OFPPacketOut(
            datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port,
            actions=actions)
        datapath.send_msg(out)

    @set_ev_cls(event.EventLinkDelete)
    def links_deleted(self,ev):
	#print ev.link.src.dpid
	print('deleted link: %d<-->%d' % (ev.link.src.dpid,ev.link.dst.dpid)) 
	self.net.remove_edge(ev.link.src.dpid,ev.link.dst.dpid)
	#self.printG()
	#self.dict_paths
	self.del_linkDeleted(ev.link.src.dpid,ev.link.dst.dpid)
        
        #update mac_learning_table 
	dp = self.get_datapath(ev.link.dst.dpid)
	s_keys = list(self.mac_to_port[(dp,ev.link.dst.dpid)].keys())
	for src in s_keys:
	    if self.mac_to_port[(dp,ev.link.dst.dpid)][src] == ev.link.dst.port_no:
		try:
		    del self.mac_to_port[(dp,ev.link.dst.dpid)][src]
		except Exception,e:
		    print str(e)

    @set_ev_cls(event.EventPortDelete)
    def port_deleted(self,ev):
	print('sw:%d - port_no:%d deleted' % (ev.port.dpid,ev.port.port_no))

    @set_ev_cls(event.EventLinkAdd)
    def links_added(self,ev):
	print ev.link

    def del_linkDeleted(self, src_dpid, dst_dpid):
	#deal path of changed links
	for path_list in self.dict_paths:
	    dict_dst = self.dict_paths[path_list]
	    for dict_dst_list in dict_dst:
		list_path = self.dict_paths[path_list][dict_dst_list]
		for i in range(len(list_path) - 3):
		    if list_path[i+1] == src_dpid and list_path[i+2] ==dst_dpid:
			print 'test......'
			#del_action
			src = list_path[0]
			dst = list_path[len(list_path)-1]
			
			#del_switches's old flow table
#			print self.dict_paths[src][dst]
#			for j in range(len(list_path) - 2):
#			    target_dpid = list_path[j+1]
#			    target_dp = self.get_datapath(target_dpid)
#			    in_port = self.mac_to_port[(target_dp,target_dpid)][src]
#			    try:
#				[self.remove_flows(target_dp, n, in_port, dst) for n in [0, 1]]
#			    except Exception, e:
#				print str(e)
			    				
			#update new path
			old_path = list(self.dict_paths[src][dst])
			path = nx.shortest_path(self.net, src, dst, weight="weight")
		        self.dict_paths[src][dst] = list(path)
			old_path_tmp = list(old_path)
			new_path_tmp = list(path)
			old_path_tmp.pop()
			new_path_tmp.pop()
			print type(path)
			while(1):
			    old_element = old_path_tmp[len(old_path_tmp)-2]
			    new_element = new_path_tmp[len(new_path_tmp)-2]
			    if old_element != new_element:
				break
			    else:
				old_path_tmp.pop()
				new_path_tmp.pop()
			while(1):
			    if len(old_path_tmp) >=2 and len(new_path_tmp) >=2:
			        old_element = old_path_tmp[1]
			        new_element = new_path_tmp[1]
			        if old_element == new_element:
				    del(old_path_tmp[0])
				    del(new_path_tmp[0])
				else:
				    break
			    else:
				break
			print old_path_tmp
			print new_path_tmp

			#del switches's old flow table
			for delete_dpid in old_path_tmp:
			    delete_dp = self.get_datapath(delete_dpid)
			    in_port = self.mac_to_port[(delete_dp,delete_dpid)][src]
			    try:
				[self.remove_flows(delete_dp,n,in_port,dst) for n in [0, 1]]
			    except Exception, e:
				print str(e)
			
			#update switches's new flow table
			for update_dpid in new_path_tmp:
			    update_dp = self.get_datapath(update_dpid)
			    in_port_update = self.mac_to_port[(update_dp,update_dpid)][src]
			    self.update_flow(update_dp,path,in_port_update,dst)	

#			for k in range(len(path) - 2):
#			    update_dpid = path[k+1]
#			    update_dp = self.get_datapath(update_dpid)
#			    in_port_update = self.mac_to_port[(update_dp,update_dpid)][src]
#			    self.update_flow(update_dp,path,in_port_update,dst)
			#			
			break

    def get_datapath(self,dpid):
	for dp in self.dps:
	    if dp.id == dpid:
		return dp
	return None

    def update_flow(self, datapath, path, in_port, dst):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
	next = path[path.index(datapath.id) + 1]
        out_port = self.net[datapath.id][next]['port']
	actions = [parser.OFPActionOutput(out_port)]
	match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
        self.add_flow(datapath, in_port, dst, actions)
        data = None
        out = datapath.ofproto_parser.OFPPacketOut(
            datapath=datapath,buffer_id=ofproto.OFP_NO_BUFFER,in_port=in_port,
            actions=actions)
	print 'update'
	print path
        datapath.send_msg(out)

    def remove_flows(self, datapath, table_id, inp, dst_mac):
        """Removing matched flow entries."""
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        match = parser.OFPMatch(in_port=inp, eth_dst=dst_mac)
        instructions = []
        flow_mod = self.remove_table_flows(datapath, table_id,
                                        match, instructions)
        datapath.send_msg(flow_mod)
    

    def remove_table_flows(self, datapath, table_id, match, instructions):
        """Create OFP flow mod message to remove flows from table."""
        ofproto = datapath.ofproto
        flow_mod = datapath.ofproto_parser.OFPFlowMod(datapath, 0, 0, table_id,
                                                      ofproto.OFPFC_DELETE, 0, 0,
                                                      1,
                                                      ofproto.OFPCML_NO_BUFFER,
                                                      ofproto.OFPP_ANY,
                                                      ofproto.OFPG_ANY, 0,
                                                      match, instructions)
        return flow_mod
	
