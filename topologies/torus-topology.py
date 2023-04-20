
from mininet.net import Mininet
from mininet.node import OVSBridge,RemoteController,Controller
from mininet.link import TCLink

def enableSTP( switches ):
    for switch in switches:
        switch.cmd( 'ovs-vsctl set bridge', switch, 'stp_enable=true' )
# Create a Mininet object
net = Mininet(controller=RemoteController('c0',ip='192.168.122.1',port=6633), switch=OVSBridge, link=TCLink)
c1 = net.addController('c1', controller=RemoteController, ip='192.168.122.110', port=6633)
c2 = net.addController('c2', controller=RemoteController, ip='192.168.122.111', port=6633)

# Create switches for the torus topology
s1 = net.addSwitch('s1',stp=True)
s2 = net.addSwitch('s2',stp=True)
s3 = net.addSwitch('s3',stp=True)
s4 = net.addSwitch('s4',stp=True)
s5 = net.addSwitch('s5',stp=True)
s6 = net.addSwitch('s6',stp=True)
s7 = net.addSwitch('s7',stp=True)
s8 = net.addSwitch('s8',stp=True)
s9 = net.addSwitch('s9',stp=True)

h1 = net.addHost('h1')
h2 = net.addHost('h2')
h3 = net.addHost('h3')
h4 = net.addHost('h4')
h5 = net.addHost('h5')
h6 = net.addHost('h6')
h7 = net.addHost('h7')
h8 = net.addHost('h8')
h9 = net.addHost('h9')

net.addLink(h1,s1)
net.addLink(h2,s2)
net.addLink(h3,s3)
net.addLink(h4,s4)
net.addLink(h5,s5)
net.addLink(h6,s6)
net.addLink(h7,s7)
net.addLink(h8,s8)
net.addLink(h9,s9)

# Connect switches in torus topology
net.addLink(s1, s2)
net.addLink(s2, s3)
net.addLink(s4, s5)
net.addLink(s5, s6)
net.addLink(s7, s8)
net.addLink(s8, s9)
net.addLink(s1, s4)
net.addLink(s2, s5)
net.addLink(s3, s6)
net.addLink(s4, s7)
net.addLink(s5, s8)
net.addLink(s6, s9)
net.addLink(s1, s5)
net.addLink(s2, s6)
net.addLink(s4, s8)
net.addLink(s5, s9)

enableSTP(net.switches)
# Start the network and run CLI
net.start()
for switch in net.switches:
    if switch.name in ['s1','s2','s3','s4']:
        switch.start([c1])
        print("Switch in controller 1")
    elif switch.name in ['s5','s6','s7','s8','s9']:
        switch.start([c2])
        print("Switch in controller 2")
net.interact()