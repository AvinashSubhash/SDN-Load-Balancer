from mininet.net import Mininet
from mininet.topo import Topo
from mininet.node import OVSSwitch, RemoteController, Controller
from mininet.link import TCLink

class MyTopo(Topo):
    def build(self):

        # Add two switches to the topology
        switch1 = self.addSwitch('s1', mac='00:00:00:00:00:01',cls=OVSSwitch)
        switch2 = self.addSwitch('s2', mac='00:00:00:00:00:02',cls=OVSSwitch)
        switch3 = self.addSwitch('s3', mac='00:00:00:00:00:03',cls=OVSSwitch)
        switch4 = self.addSwitch('s4', mac='00:00:00:00:00:04',cls=OVSSwitch)
        switch5 = self.addSwitch('s5', mac='00:00:00:00:00:05',cls=OVSSwitch)
        switch6 = self.addSwitch('s6', mac='00:00:00:00:00:06',cls=OVSSwitch)
        
        # Add three inter-controller switches
        #icswitch01 = self.addSwitch('is01',cls=OVSSwitch)
        #icswitch12 = self.addSwitch('is12',cls=OVSSwitch)
        #icswitch02 = self.addSwitch('is02',cls=OVSSwitch)

        # Add hosts
        host1 = self.addHost('h1',ip='10.0.0.1')
        host2 = self.addHost('h2',ip='10.0.0.2')
        host3 = self.addHost('h3',ip='10.0.0.3')
        host4 = self.addHost('h4',ip='10.0.0.4')
        host5 = self.addHost('h5',ip='10.0.0.5')
        host6 = self.addHost('h6',ip='10.0.0.6')
        host7 = self.addHost('h7',ip='10.0.0.7')
        host8 = self.addHost('h8',ip='10.0.0.8')
        host9 = self.addHost('h9', ip='10.0.0.9')
        host10 = self.addHost('h10',ip='10.0.0.10')
        host11 = self.addHost('h11',ip='10.0.0.11')
        host12 = self.addHost('h12',ip='10.0.0.12')
        
        # Linking the hosts to the switches
        self.addLink(host1, switch1)
        self.addLink(host2, switch1)
        self.addLink(host3, switch2)
        self.addLink(host4, switch2)
        self.addLink(host5, switch3)
        self.addLink(host6, switch3)
        self.addLink(host7, switch4)
        self.addLink(host8, switch4)
        self.addLink(host9, switch5)
        self.addLink(host10,switch5)
        self.addLink(host11,switch6)
        self.addLink(host12,switch6)
        
        # Linking all switches
        self.addLink(switch1,switch2)
        self.addLink(switch2,switch3)
        self.addLink(switch3,switch4)
        self.addLink(switch4,switch5)
        self.addLink(switch5,switch6)


topo = MyTopo()
net = Mininet(topo=topo,controller=RemoteController('c0',ip='192.168.122.1',port=6633),link=TCLink)

# Connect to multiple Floodlight controllers

c1 = net.addController('c1', controller=RemoteController, ip='192.168.122.110', port=6633)
c2 = net.addController('c2', controller=RemoteController, ip='192.168.122.111', port=6633)
c3 = net.addController('c3', controller=RemoteController, ip='192.168.122.112', port=6633)

print("No. of Controllers in this topology: ",len(net.controllers))

#main_controller=[]
#for i in net.controllers:
#    if i.name=='c0':
#        main_controller.append(i)

#switch5 = net.addSwitch('s5',cls=OVSSwitch)
#host9 = net.addHost('h9',ip='10.0.0.9')
#net.addLink(host9,switch5)
#net.addLink(main_controller[0],switch5)

# Start the network
net.start()
# Set the controller for each switch

for switch in net.switches:
    if switch.name in ['s1','s2']:
        #net.addLink(switch,c1)
        switch.start([c1])
    elif switch.name in ['s3','s4']:
        switch.start([c2])
    elif switch.name in ['s5','s6']:
        switch.start([c3])
    elif switch.name in ['is01']:
        switch.start([c1,c2])
    elif switch.name in ['is02']:
        switch.start([c1,c3])
    elif switch.name in ['is12']:
        switch.start([c2,c3])

#net.pingAll()
# Start the CLI
net.interact()
