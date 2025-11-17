import ipaddress
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class ZMQProxyCfg:
    ip_addr: Optional[ipaddress.IPv4Address] = None
    slow_down_ratio: Optional[int] = 4
    component_proxy_cfgs: Optional[List['ComponenteProxyCfg']] = None

    def get_component_cfg(self, name: str) -> 'ComponenteProxyCfg':
        for cfg in self.component_proxy_cfgs:
            if cfg.name == name:
                return cfg
        else:
            cfg = ComponenteProxyCfg(name=name)
            self.component_proxy_cfgs.append(cfg)
            return cfg


@dataclass
class ComponenteProxyCfg:
    name: Optional[str] = None
    rx_port: Optional[int] = None
    tx_port: Optional[int] = None
    path_loss_db: Optional[int] = None
