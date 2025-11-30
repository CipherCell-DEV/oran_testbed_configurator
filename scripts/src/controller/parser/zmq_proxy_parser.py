from model.zmq_proxy_config import ZMQProxyCfg


class ZMQProxyParser:
    @staticmethod
    def parse_zmq_proxy_cfg(elements: dict) -> ZMQProxyCfg:
        zmq_proxy_cfg = ZMQProxyCfg(ip_addr=elements['ip_addr'],
                                    slow_down_ratio=elements['slow_down_ratio'])

        zmq_proxy_cfg.component_proxy_cfgs = []
        for comp_name in elements['rx_ports'].keys():
            zmq_proxy_cfg.get_component_cfg(comp_name).rx_port = elements['rx_ports'][comp_name]
            zmq_proxy_cfg.get_component_cfg(comp_name).tx_port = elements['tx_ports'][comp_name]
            zmq_proxy_cfg.get_component_cfg(comp_name).path_loss_db = elements['path_losses_db'].get(comp_name, None)

        return zmq_proxy_cfg
