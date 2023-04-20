from mininet.net import Mininet
from mininet.topo import Topo
from mininet.node import OVSSwitch, RemoteController, Controller
from mininet.link import TCLink

class MyTopo(Topo):
    def build(self):
        # Add two switches to the topology
        switch1 = self.addSwitch('s1', cls=OVSSwitch)
        switch2 = self.addSwitch('s2', cls=OVSSwitch)
        switch3 = self.addSwitch('s3', cls=OVSSwitch)
        switch4 = self.addSwitch('s4', cls=OVSSwitch)
        switch5 = self.addSwitch('s5', cls=OVSSwitch)
        switch6 = self.addSwitch('s6', cls=OVSSwitch)

        # Add hosts
        host1 = self.addHost('h1', ip='10.0.0.1')
        host2 = self.addHost('h2', ip='10.0.0.2')
        host3 = self.addHost('h3', ip='10.0.0.3')
        host4 = self.addHost('h4', ip='10.0.0.4')
        host5 = self.addHost('h5', ip='10.0.0.5')
        host6 = self.addHost('h6', ip='10.0.0.6')
        host7 = self.addHost('h7', ip='10.0.0.7')
        host8 = self.addHost('h8', ip='10.0.0.8')
        host9 = self.addHost('h9', ip='10.0.0.9')
        host10 = self.addHost('h10', ip='10.0.0.10')
        
        #Add links between hosts and switches
        self.addLink(host1, switch3)
        self.addLink(host2, switch3)
        self.addLink(host3, switch4)
        self.addLink(host4, switch4)
        self.addLink(host5, switch4)
        self.addLink(host6, switch5)
        self.addLink(host7, switch5)
        self.addLink(host8, switch6)
        self.addLink(host9, switch6)
        self.addLink(host10, switch6)

        #Add links between switches
        self.addLink(switch1, switch2)
        self.addLink(switch1, switch3)
        self.addLink(switch1, switch4)
        self.addLink(switch2, switch5)
        self.addLink(switch2, switch6)

topo = MyTopo()
net = Mininet(topo=topo,controller=RemoteController('c0',ip='192.168.122.1',port=6633), link=TCLink)

# Connect to multiple Floodlight controllers
c1 = net.addController('c1', controller=RemoteController, ip='192.168.122.110', port=6633)
c2 = net.addController('c2', controller=RemoteController, ip='192.168.122.111', port=6633)

print("No. of controllers in topology: ",len(net.controllers))

# Start the network
net.start()
# Set the controller for each switch
for switch in net.switches:
    if switch.name in ['s1','s3','s4']:
        switch.start([c1])
    elif switch.name in ['s2','s5','s6']:
        switch.start([c2])

#net.pingAll()
# Start the CLI
net.interact()
