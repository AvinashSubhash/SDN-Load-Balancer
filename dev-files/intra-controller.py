from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib import hub
import requests


class MasterController(app_manager.RyuApp):
    def __init__(self, *args, **kwargs):
        super(MasterController, self).__init__(*args, **kwargs)
        self.sub_controllers = [{'ip': '192.168.122.110', 'port': '8080'},]

        self.monitor_thread = hub.spawn(self._monitor)

    def _monitor(self):
        while True:
            for sub_controller in self.sub_controllers:
                url = "http://{}:{}/stats/switches".format(sub_controller['ip'], sub_controller['port'])
                response = requests.get(url)
                self.logger.info(response)
                if response.ok:
                    self.logger.info("Controller at {}:{} is UP".format(sub_controller['ip'], sub_controller['port']))
                else:
                    self.logger.info("Controller at {}:{} is DOWN".format(sub_controller['ip'], sub_controller['port']))

            hub.sleep(5)

    def _balance_load(self):
        url = "http://{}:{}/stats/switches".format(self.sub_controllers[0]['ip'], self.sub_controllers[0]['port'])
        response = requests.get(url)
        if response.ok:
            switches = response.json()
            for switch in switches:
                dpid = switch['dpid']
                url = "http://{}:{}/stats/flow/{}".format(self.sub_controllers[0]['ip'],
                                                          self.sub_controllers[0]['port'], dpid)
                response = requests.get(url)
                if response.ok:
                    flow_stats = response.json()
                    flow_stats.sort(key=lambda x: x['packet_count'], reverse=True)
                    if len(flow_stats) >= 2:
                        url = "http://{}:{}/stats/port/{}".format(self.sub_controllers[0]['ip'],
                                                                  self.sub_controllers[0]['port'], dpid)
                        response = requests.get(url)
                        if response.ok:
                            port_stats = response.json()
                            port_stats.sort(key=lambda x: x['rx_packets'], reverse=True)
                            src_port = port_stats[0]['port_no']
                            dst_port = port_stats[1]['port_no']
                            self.logger.info("Transferring load from {}:{} to {}:{}"
                                             .format(self.sub_controllers[0]['ip'], src_port,
                                                     self.sub_controllers[0]['ip'], dst_port))
                            url = "http://{}:{}/stats/flowentry/modify".format(self.sub_controllers[0]['ip'],
                                                                                self.sub_controllers[0]['port'])
                            payload = {
                                "dpid": dpid,
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
                                        "port": dst_port
                                    }
                                ]
                            }
                            response = requests.post(url, json=payload)
                           
