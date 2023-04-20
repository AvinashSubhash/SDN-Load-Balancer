from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib import hub
import requests


#c0 = 52:54:00:eb:5e:22
#c1 = 52:54:00:64:08:8c
#c2 = 52:54:00:3c:60:5c

class MasterController(app_manager.RyuApp):
    def __init__(self, *args, **kwargs):
        super(MasterController, self).__init__(*args, **kwargs)
        self.sub_controllers = [{'ip': '192.168.122.110', 'port': '8080'},
				{'ip': '192.168.122.111', 'port': '8080'},
				{'ip': '192.168.122.112', 'port': '8080'},]

        self.monitor_thread = hub.spawn(self._monitor)
        self.balance_load = hub.spawn(self._balance_load)
        self.controller_id = hub.spawn(self._show_controller_id)
    def _show_controller_id(self):
        controllers = manager.get_manager().list_managers()
        for controller in controllers:
            #if controller.target == "tcp:<controller C's IP address>:<port>":
            self.logger.info(controller.addr,": ",controller.id)

    def _monitor(self):
        while True:
            for sub_controller in self.sub_controllers:
                url = "http://{}:{}/v1.0/topology/switches".format(sub_controller['ip'], sub_controller['port'])
                response = requests.get(url)
                if response.ok:
                    self.logger.info("Controller at {}:{} is UP".format(sub_controller['ip'], sub_controller['port']))
                else:
                    self.logger.info("Controller at {}:{} is DOWN".format(sub_controller['ip'], sub_controller['port']))

            hub.sleep(5)
            break

    def _balance_load(self):
        for i in range(0, len(self.sub_controllers)):
            url = "http://{}:{}/v1.0/topology/switches".format(self.sub_controllers[i]['ip'], self.sub_controllers[i]['port'])
            response = requests.get(url)
            if response.ok:
                switches = response.json()
                for switch in switches:
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
                                src_port = port_stats[0]['port_no']
                                dst_port = port_stats[1]['port_no']
                                dst_ip = self.sub_controllers[0]['ip']
                                self.logger.info("Transferring load from {}:{} to {}:{}"
                                                 .format(self.sub_controllers[i]['ip'], src_port,
                                                         dst_ip, dst_port))
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
                                        "in_port": src_port
                                    },
                                    "actions": [
                                        {
                                            "type": "OUTPUT",
                                            "port": "OFPP_CONTROLLER",
                                        },
                                    ]
                                }
                                response = requests.post(url, json=payload)
