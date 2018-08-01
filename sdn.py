#!/usr/bin/python

#from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Controller, RemoteController, OVSController
from mininet.node import CPULimitedHost, Host, Node
from mininet.node import OVSKernelSwitch, UserSwitch
from mininet.node import IVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink
from subprocess import call
import time
import threading
import math
import itertools
import traceback
import random
import os

startMoniter = 4
aps_range = 100
max_v = 20
list_network=[['s1','h1'],['s2','h2'],['s9','h3']]

def myNetwork():
    info( '*** Create network\n' )
    net = Mininet( topo=None,
		   link=TCLink,
                   build=False,
                   ipBase='10.0.0.0/8')


    #cita = 90
    #print math.sin(math.radians(cita))
    info( '*** Adding controller\n' )
    c0=net.addController(name='c0',
                      controller=RemoteController,
                      ip='127.0.0.1',
                      protocol='tcp',
                      port=6633)
    '''
    c1=net.addController(name='c1',
                      controller=RemoteController,
                      ip='192.168.1.2',
                      protocol='tcp',
                      port=6633)
    c2=net.addController(name='c2',
                      controller=RemoteController,
                      ip='192.168.1.3',
                      protocol='tcp',
                      port=6633)s
    '''

    info( '*** Add switches\n')
    s1 = net.addSwitch('s1', cls=OVSKernelSwitch, position='102,76', min_x=100, max_x=150, min_y=75, max_y=150, dpid='1')
    s2 = net.addSwitch('s2', cls=OVSKernelSwitch, position='104,351.5', min_x=100, max_x=150, min_y=350, max_y=425, dpid='2')
    s3 = net.addSwitch('s3', cls=OVSKernelSwitch, position='228,256', min_x=200, max_x=250, min_y=225, max_y=275, dpid='3')
    s4 = net.addSwitch('s4', cls=OVSKernelSwitch, position='348,147.5', min_x=300, max_x=350, min_y=75, max_y=150, dpid='4')
    s5 = net.addSwitch('s5', cls=OVSKernelSwitch, position='349.5,425', min_x=300, max_x=450, min_y=350, max_y=500, dpid='5')
    s6 = net.addSwitch('s6', cls=OVSKernelSwitch, position='468,76', min_x=450, max_x=500, min_y=50, max_y=150, dpid='6')
    s7 = net.addSwitch('s7', cls=OVSKernelSwitch, position='486,377.6', min_x=400, max_x=600, min_y=300, max_y=500, dpid='7')
    s8 = net.addSwitch('s8', cls=OVSKernelSwitch, position='589.3,238.5', min_x=550, max_x=600, min_y=150, max_y=250, dpid='8')
    s9 = net.addSwitch('s9', cls=OVSKernelSwitch, position='712,222.6', min_x=650, max_x=750, min_y=150, max_y=250, dpid='9')

    info( '*** Add hosts\n')
    h1 = net.addHost('h1', cls=Host, ip='10.0.0.1', position='86,123.5', defaultRoute=None)
    h2 = net.addHost('h2', cls=Host, ip='10.0.0.2', position='128.5,346.4', defaultRoute=None)
    h3 = net.addHost('h3', cls=Host, ip='10.0.0.3', position='686,223.5,0', defaultRoute=None)

    info( '*** Add links\n')
    #net.addLink(s1, s2)
    net.addLink(s2, h2)
    net.addLink(h1, s1)
    net.addLink(h3, s9)

    info( '*** Starting network\n')
    net.build()
    info( '*** Starting controllers\n')
    for controller in net.controllers:
        controller.start()

    info( '*** Starting switches\n')
    net.get('s1').start([c0])
    net.get('s2').start([c0])
    net.get('s3').start([c0])
    net.get('s4').start([c0])
    net.get('s5').start([c0])
    net.get('s6').start([c0])
    net.get('s7').start([c0])
    net.get('s8').start([c0])
    net.get('s9').start([c0])

    startMoniter = 4 

    th_check=threading.Thread(target=topoCheck,args=(net,))
    th_check.start()
    info( '*** Post configure switches and hosts\n')
 
    CLI(net)
    try:
        net.stop()
	os.system("sudo mn -c") 
    except Exception, e:
	print str(e)
    global startMoniter
    startMoniter = 0

def topoCheck(net):
    global startMoniter
    time.sleep(2)

    try:
	#code test field##
	print 'Network Start'
    except Exception, e:
	print str(e)

    while(startMoniter):
        time.sleep(2)
        try:
	
	    #define mobility model of switches node
	    for node in net.switches:
		new_x = -1
		new_y = -1
		while (new_x <= node.params['min_x'] or new_x >= node.params['max_x']) or (new_y <= node.params['min_y'] or new_y >= node.params['max_y']):
		    cita = random.randint(0,360)
		    dist = random.randint(-max_v/2,max_v)
		    if dist < 0:
		        dist = 0
		    new_x=float(node.params['position'].split(',')[0]) + dist * math.sin(math.radians(cita))
		    new_y=float(node.params['position'].split(',')[1]) + dist * math.cos(math.radians(cita))
		node.params['position'] = str(new_x) + ',' + str(new_y)
		#print('%s: %s' % ((node.name),node.params['position']))	
		
		#define mobility model of hosts node
		for list_switch_hosts in list_network:
		    if str(list_switch_hosts[0]) == str(node.name):
		        for host in list_switch_hosts:
			    if str(host)[0] == 'h':
			        node_host = net.get(str(host))
				new_x = -1000
		                new_y = -1000
				sw_x = float(node.params['position'].split(',')[0])
				sw_y = float(node.params['position'].split(',')[1])
				while getDistance(sw_x, sw_y, new_x, new_y) > aps_range:
				    cita = random.randint(0,360)
		                    dist = random.randint(-max_v/2,max_v)
		                    if dist < 0:
		                        dist = 0
		                    new_x=float(node_host.params['position'].split(',')[0]) + dist * math.sin(math.radians(cita))
		                    new_y=float(node_host.params['position'].split(',')[1]) + dist * math.cos(math.radians(cita))
				node_host.params['position'] = str(new_x) + ',' + str(new_y)
				#print('%s: %s' % ((node_host.name),node_host.params['position']))				  
			
	
	    #del links which may be linked
	    list_may_link = list(itertools.combinations(net.switches,2))  
	    for may_link in list_may_link:
		x1 = float(may_link[0].params['position'].split(',')[0])
		y1 = float(may_link[0].params['position'].split(',')[1])
		x2 = float(may_link[1].params['position'].split(',')[0])
		y2 = float(may_link[1].params['position'].split(',')[1])
		dist = getDistance(x1,y1,x2,y2)
		if dist <= 250 and isLinkExist(net,str(may_link[0]),str(may_link[1])):
		    net.addLink(may_link[0],may_link[1])
	
	    #deal the broken links
	    for net_link in net.links:
		node1_str = str(net_link.intf1).split('-')[0]
		node2_str = str(net_link.intf2).split('-')[0]
		n1 = net.get(node1_str)
		n2 = net.get(node2_str)
		if str(n1.name[0]) == 's' and str(n2.name[0]) == 's':
		    x1 = float(n1.params['position'].split(',')[0])
		    y1 = float(n1.params['position'].split(',')[1])
		    x2 = float(n2.params['position'].split(',')[0])
		    y2 = float(n2.params['position'].split(',')[1])
		    #print('x1= %d y1= %d x2= %d y2= %d' %(x1,y1,x2,y2))
		    dist = getDistance(x1,y1,x2,y2)
		    if dist > 250:
		        net.delLink(net_link)
		    else:
		        #set the status of links(bw,delay,loss...)
		        equationLoss = dist * 2 / 100
		        equationDelay = dist /20 + 1
		        #equationBw = eval('10.10*(1.01 ** -(dist/100))')	
		        #equationBw = 101.00
		        net_link.intf1.config(**{'delay':str(equationDelay)+'ms','loss':equationLoss})
		        net_link.intf2.config(**{'delay':str(equationDelay)+'ms','loss':equationLoss})	
            net.get('s1').start([net.get('c0')])
            net.get('s2').start([net.get('c0')])
            net.get('s3').start([net.get('c0')])
            net.get('s4').start([net.get('c0')])
            net.get('s5').start([net.get('c0')])
            net.get('s6').start([net.get('c0')])
            net.get('s7').start([net.get('c0')])
            net.get('s8').start([net.get('c0')])
            net.get('s9').start([net.get('c0')])
        except Exception, e:
	    print str(e)

def isLinkExist(net,n1,n2):
    for net_link in net.links:
	if type(net_link.intf1) == type(net_link.intf2):
	    n1_str = str(net_link.intf1).split('-')[0]
	    n2_str = str(net_link.intf2).split('-')[0]
	    if n1 == n1_str and n2 == n2_str:
	        return False
    return True

def getDistance(x1,y1,x2,y2):
    dx = abs(x1 - x2)
    dy = abs(y1 - y2)
    return math.sqrt(dx * dx + dy * dy)	

if __name__ == '__main__':
    setLogLevel( 'info' )
    myNetwork()

