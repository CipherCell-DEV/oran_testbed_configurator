import ipaddress
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class ZMQProxyCfg:
    ip_addr: Optional[ipaddress.IPv4Address] = None
    slow_down_ratio: Optional[int] = 4
    component_proxy_cfgs: Optional[List['ProxyComponentCfg']] = None

    def get_component_cfg(self, name: str) -> 'ProxyComponentCfg':
        if self.component_proxy_cfgs is None:
            self.component_proxy_cfgs = []
        for cfg in self.component_proxy_cfgs:
            if cfg.name == name:
                return cfg
        else:  # If no entry is found, create one with the correct name
            cfg = ProxyComponentCfg(name=name)
            self.component_proxy_cfgs.append(cfg)
            return cfg

    def get_component_data(self) -> dict:
        result = {}
        for component_proxy_cfg in self.component_proxy_cfgs:
            result[component_proxy_cfg.name] = {
                'path_loss_db': component_proxy_cfg.path_loss_db,
                'ip': None,
                'rx_port': component_proxy_cfg.rx_port,
                'tx_port': component_proxy_cfg.tx_port,
            }
        return result


@dataclass
class ProxyComponentCfg:
    name: Optional[str] = None
    rx_port: Optional[int] = None
    tx_port: Optional[int] = None
    path_loss_db: Optional[int] = None
