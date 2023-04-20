from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib import hub
import requests
import time
import random


#c0 = 52:54:00:eb:5e:22
#c1 = 52:54:00:64:08:8c
#c2 = 52:54:00:3c:60:5c




class MasterController(app_manager.RyuApp):
    def __init__(self, *args, **kwargs):
        super(MasterController, self).__init__(*args, **kwargs)

        self.sub_controllers = []
        self.connection_data = {}
        self.switch_connection_data = {}
        self.RR_INDEX=0
        self.LD_THRESHOLD=10
        self.controller_pools = [] # Static part of load balancing
        self.controller_mac = {}
        self.controller_load = {}
        self.controller_load_diff = {}
        self._setParameters(self._selectTopology())
        self.monitor_thread = hub.spawn(self._monitor)
        self.balance_load = hub.spawn(self._balance_load)


    def _selectTopology(self):
        
        print("\n\nEnter the topology number:\n1.Basic Tree Topology\n2.Dumbbell Topology\n3.Torus Topology")
        option = int(input())
        if option > 3 or option < 1:
            print("Error entering option. Exiting . .")
            exit(0)
        return option

    def _setParameters(self,option):
        if option==1:
            self.sub_controllers = [{'ip': '192.168.122.110', 'port': '8080'},
                {'ip': '192.168.122.111', 'port': '8080'},
                {'ip': '192.168.122.112', 'port': '8080'},]
            self.connection_data = {'192.168.122.110':{'192.168.122.110':[1,2],'192.168.122.111':[],'192.168.122.112':[]},
                                '192.168.122.111':{'192.168.122.110':[],'192.168.122.111':[3,4],'192.168.122.112':[]},
                                '192.168.122.112':{'192.168.122.110':[],'192.168.122.111':[],'192.168.122.112':[5,6]}}
            self.switch_connection_data = {1:self.sub_controllers[0],2:self.sub_controllers[0],3:self.sub_controllers[1],4:self.sub_controllers[1],5:self.sub_controllers[2],6:self.sub_controllers[2]}
            self.controller_pools = [self.sub_controllers]
            self.controller_mac = {self.sub_controllers[0]['ip']:'52:54:00:eb:5e:22',self.sub_controllers[1]['ip']:'52:54:00:64:08:8c',self.sub_controllers[2]['ip']:'52:54:00:3c:60:5c'}
            self.controller_load = {self.sub_controllers[0]['ip']:0,self.sub_controllers[1]['ip']:0,self.sub_controllers[2]['ip']:0}
            self.controller_load_diff = {self.sub_controllers[0]['ip']:0,self.sub_controllers[1]['ip']:0,self.sub_controllers[2]['ip']:0}
        
        elif option==2:
            self.sub_controllers = [{'ip': '192.168.122.110', 'port': '8080'},
                {'ip': '192.168.122.111', 'port': '8080'},]
            self.connection_data = {'192.168.122.110':{'192.168.122.110':[1,3,4],'192.168.122.111':[]},
                                '192.168.122.111':{'192.168.122.110':[],'192.168.122.111':[2,5,6]}}
            self.switch_connection_data = {1:self.sub_controllers[0],2:self.sub_controllers[1],3:self.sub_controllers[0],4:self.sub_controllers[0],5:self.sub_controllers[1],6:self.sub_controllers[1]}
            self.controller_pools = [self.sub_controllers]
            self.controller_mac = {self.sub_controllers[0]['ip']:'52:54:00:eb:5e:22',self.sub_controllers[1]['ip']:'52:54:00:64:08:8c'}
            self.controller_load = {self.sub_controllers[0]['ip']:0,self.sub_controllers[1]['ip']:0}
            self.controller_load_diff = {self.sub_controllers[0]['ip']:0,self.sub_controllers[1]['ip']:0}

        elif option==3:
            self.sub_controllers = [{'ip': '192.168.122.110', 'port': '8080'},
                {'ip': '192.168.122.111', 'port': '8080'},]
            self.connection_data = {'192.168.122.110':{'192.168.122.110':[1,2,3,4],'192.168.122.111':[]},
                                '192.168.122.111':{'192.168.122.110':[],'192.168.122.111':[5,6,7,8,9]}}
            self.switch_connection_data = {1:self.sub_controllers[0],2:self.sub_controllers[0],3:self.sub_controllers[0],4:self.sub_controllers[0],5:self.sub_controllers[1],6:self.sub_controllers[1],7:self.sub_controllers[1],8:self.sub_controllers[1]}
            self.controller_pools = [self.sub_controllers]
            self.controller_mac = {self.sub_controllers[0]['ip']:'52:54:00:eb:5e:22',self.sub_controllers[1]['ip']:'52:54:00:64:08:8c'}
            self.controller_load = {self.sub_controllers[0]['ip']:0,self.sub_controllers[1]['ip']:0}
            self.controller_load_diff = {self.sub_controllers[0]['ip']:0,self.sub_controllers[1]['ip']:0}

        else:
            exit(0)

    def _load_calculator(self,flag=False):

        for controller in self.sub_controllers:
            pkt_count = 0
            for inner_controller in self.sub_controllers:
                for dpid in self.connection_data[controller['ip']][inner_controller['ip']]:
                    #dpid = switch['dpid']
                    url = "http://{}:{}/stats/flow/{}".format(inner_controller['ip'],inner_controller['port'], int(dpid))
                    response = requests.get(url)
                    if response.ok:
                        flow_stats = response.json()[str(int(dpid))]
                        for flow in flow_stats:
                            pkt_count += flow['packet_count']
                                
            self.controller_load_diff[controller['ip']] = pkt_count - self.controller_load[controller['ip']]
            self.controller_load[controller['ip']] = pkt_count
            if flag:
                diff = self.controller_load_diff[controller['ip']]
                print("PACKET_COUNT_DIFFERENCE::",controller['ip'],": ",diff)


    def _monitor(self):
        while True:
            self.logger.info("CONTROLLER_STATUS::Monitoring status of controllers . .")
            for sub_controller in self.sub_controllers:
                url = "http://{}:{}/v1.0/topology/switches".format(sub_controller['ip'], sub_controller['port'])
                response = requests.get(url)
                if response.ok:
                    self.logger.info("CONTROLLER_STATUS::Controller at {}:{} is UP".format(sub_controller['ip'], sub_controller['port']))
                else:
                    self.logger.info("CONTROLLER_STATUS::Controller at {}:{} is DOWN".format(sub_controller['ip'], sub_controller['port']))

            hub.sleep(5)

    def _balance_load(self):
        while True:
            self.logger.info("LD_CALC::Load Calculation in progress . .")
            self._load_calculator()
            time.sleep(5)
            self._load_calculator(True)
            self.logger.info("LD_CALC::Load Calculation completed . .")
            for i in range(0, len(self.sub_controllers)):
                if self.controller_load_diff[self.sub_controllers[i]['ip']] < self.LD_THRESHOLD:
                    self.logger.info("THRESHOLD_STATUS::CONTROLLER %s : UNDER THRESHOLD",self.sub_controllers[i]['ip'])
                    continue

                #Algo Start
                
                server_pool = self.controller_pools[self.RR_INDEX]
                self.RR_INDEX = (self.RR_INDEX+1)%len(self.controller_pools)

                sorted_server_pool = sorted(server_pool, key=lambda x: self.controller_load_diff[x['ip']])
                if self.sub_controllers[i] in sorted_server_pool:
                    sorted_server_pool.remove(self.sub_controllers[i])

                if not len(sorted_server_pool):
                    continue

                selected_server = sorted_server_pool[0]

                #Algo End

                switches=[]
                for c_out in self.sub_controllers:
                    for switchx in self.connection_data[self.sub_controllers[i]['ip']][c_out['ip']]:
                        switches.append(switchx)

                for dpid in switches:
                    if random.randint(1,100) > 20:
                        continue
                    url = "http://{}:{}/stats/flow/{}".format(self.switch_connection_data[int(dpid)]['ip'],
                                                                  self.switch_connection_data[int(dpid)]['port'], int(dpid))
                    response = requests.get(url)
                    if response.ok:
                        flow_stats = response.json()[str(int(dpid))]
                        flow_stats.sort(key=lambda x: x['packet_count'], reverse=True)
                        if len(flow_stats) >= 2:
                            url = "http://{}:{}/stats/port/{}".format(self.sub_controllers[i]['ip'],
                                                                          self.sub_controllers[i]['port'], int(dpid))
                            response = requests.get(url)
                            if response.ok:
                                self.logger.info("LOAD_TRANSFER::Transferring load from {} to {}"
                                                     .format(self.sub_controllers[i]['ip'],
                                                             selected_server['ip']))
                                #print(dpid,self.sub_controllers[i]['ip'],self.switch_connection_data[int(dpid)]['ip'])
                                self.connection_data[self.sub_controllers[i]['ip']][self.switch_connection_data[int(dpid)]['ip']].remove(dpid)
                                self.connection_data[selected_server['ip']][self.switch_connection_data[int(dpid)]['ip']].append(dpid)
                                #print(self.connection_data)
                                url = "http://{}:{}/stats/flowentry/modify".format(self.sub_controllers[i]['ip'],
                                                                                        self.sub_controllers[i]['port'])
                                payload = {
                                        "dpid": str(int(dpid)),
                                        "cookie": 0,
                                        "cookie_mask": 0,
                                        "table_id": 0,
                                        "command": "mod",
                                        "priority": 1,
                                        "hard_timeout": 0,
                                        "idle_timeout": 0,
                                        "flags": 0,
                                        "match": {
                                            "in_port":"OFPP_CONTROLLER",
                                        },
                                        "actions": [
                                            {
                                                "type": "SET_FIELD",
                                                "field": "eth_dst",
                                                "value": str(self.controller_mac[selected_server['ip']])
                                            },
                                        ]
                                }
                                response = requests.post(url, json=payload)
