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
        self.sub_controllers = [{'ip': '192.168.122.110', 'port': '8080'},
				{'ip': '192.168.122.111', 'port': '8080'},
				{'ip': '192.168.122.112', 'port': '8080'},]
        self.connection_data = {}
        self.RR_INDEX=0
        self.LD_THRESHOLD=100
        self.controller_pools = [self.sub_controllers] # Static part of load balancing
        self.controller_mac = {self.sub_controllers[0]['ip']:'52:54:00:eb:5e:22',self.sub_controllers[1]['ip']:'52:54:00:64:08:8c',self.sub_controllers[2]['ip']:'52:54:00:3c:60:5c'}
        self.controller_load = {self.sub_controllers[0]['ip']:0,self.sub_controllers[1]['ip']:0,self.sub_controllers[2]['ip']:0}
        self.controller_load_diff = {self.sub_controllers[0]['ip']:0,self.sub_controllers[1]['ip']:0,self.sub_controllers[2]['ip']:0}
        self.monitor_thread = hub.spawn(self._monitor)
        self.balance_load = hub.spawn(self._balance_load)
    
    
    def _initialize_connection_data(self):
        
        for sub_controller in self.sub_controllers:
            
            self.connection_data[sub_controller['ip']] = []
            url = "http://{}:{}/v1.0/topology/switches".format(self.sub_controller['ip'], self.sub_controller['port'])
            response = requests.get(url)
            if response.ok:
                switches = response.json()
                for switch in switches:
                    self.connection_data[sub_controller['ip']].append(switch)

    def _load_calculator(self,flag=False):
        for controller in self.sub_controllers:
            pkt_count=0;
            url = "http://{}:{}/v1.0/topology/switches".format(controller['ip'],controller['port'])
            response = requests.get(url)
            if response.ok:
                switches = response.json()
                for switch in switches:
                    dpid = switch['dpid']
                    url = "http://{}:{}/stats/flow/{}".format(controller['ip'],controller['port'], int(dpid))
                    response = requests.get(url)
                    if response.ok:
                        flow_stats = response.json()[str(int(dpid))]
                        for flow in flow_stats:
                            pkt_count += flow['packet_count']
                            #flow_stats.sort(key=lambda x: x['packet_count'], reverse=True)
            self.controller_load_diff[controller['ip']] = pkt_count - self.controller_load[controller['ip']]
            self.controller_load[controller['ip']] = pkt_count
            if flag:
                diff = self.controller_load_diff[controller['ip']]
                print("PACKET_COUNT_DIFFERENCE-",controller['ip'],": ",diff)

    def _monitor(self):
        while True:
            self.logger.info("Monitoring status of controllers . .")
            for sub_controller in self.sub_controllers:
                url = "http://{}:{}/v1.0/topology/switches".format(sub_controller['ip'], sub_controller['port'])
                response = requests.get(url)
                if response.ok:
                    self.logger.info("STATUS::Controller at {}:{} is UP".format(sub_controller['ip'], sub_controller['port']))
                else:
                    self.logger.info("STATUS::Controller at {}:{} is DOWN".format(sub_controller['ip'], sub_controller['port']))

            hub.sleep(5)
            break

    def _balance_load(self):
        while True:
            self.logger.info("Load Calculation in progress . .")
            self._load_calculator()
            time.sleep(5)
            self._load_calculator(True)
            self.logger.info("Load Calculation completed . .")
            for i in range(0, len(self.sub_controllers)):
                if self.controller_load_diff[self.sub_controllers[i]['ip']] < self.LD_THRESHOLD:
                    self.logger.info("CONTROLLER %s : UNDER THRESHOLD",self.sub_controllers[i]['ip'])
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

                url = "http://{}:{}/v1.0/topology/switches".format(self.sub_controllers[i]['ip'], self.sub_controllers[i]['port'])
                response = requests.get(url)
                if response.ok:
                    switches = response.json()
                    for switch in switches:
                        if random.randint(1,100) > 20:
                            continue
                        dpid = switch['dpid']
                        url = "http://{}:{}/stats/flow/{}".format(self.sub_controllers[i]['ip'],
                                                                  self.sub_controllers[i]['port'], int(dpid))
                        response = requests.get(url)
                        #self.logger.info("Reached just above flow stats")
                        if response.ok:
                            flow_stats = response.json()[str(int(dpid))]
                            flow_stats.sort(key=lambda x: x['packet_count'], reverse=True)
                            #self.logger.info("Length of flow stats: ",len(flow_stats))
                            if len(flow_stats) >= 2:
                                url = "http://{}:{}/stats/port/{}".format(self.sub_controllers[i]['ip'],
                                                                          self.sub_controllers[i]['port'], int(dpid))
                                response = requests.get(url)
                                if response.ok:
                                    port_stats = response.json()[str(int(dpid))]
                                    port_stats.sort(key=lambda x: x['rx_packets'], reverse=True)
                                    self.logger.info("Transferring load from {} to {}"
                                                     .format(self.sub_controllers[i]['ip'],
                                                             selected_server['ip']))
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
