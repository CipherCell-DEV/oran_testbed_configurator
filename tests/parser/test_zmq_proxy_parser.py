from controller.parser.zmq_proxy_parser import ZMQProxyParser
from model.zmq_proxy_config import ZMQProxyCfg


class TestZMQProxyParser:
    def test_parse_zmq_proxy_cfg_valid(self):
        elements = {
            "ip_addr": "127.0.0.1",
            "slow_down_ratio": 2,
            "rx_ports": {
                "gnb": 2100,
                "ue": 2200,
            },
            "tx_ports": {
                "gnb": 3100,
                "ue": 3200,
            },
            "path_losses_db": {
                "gnb": 80,
            },
        }

        cfg = ZMQProxyParser.parse_zmq_proxy_cfg(elements)

        assert isinstance(cfg, ZMQProxyCfg)
        assert cfg.ip_addr == "127.0.0.1"
        assert cfg.slow_down_ratio == 2

        gnb_cfg = cfg.get_component_cfg("gnb")
        assert gnb_cfg.rx_port == 2100
        assert gnb_cfg.tx_port == 3100
        assert gnb_cfg.path_loss_db == 80

        ue_cfg = cfg.get_component_cfg("ue")
        assert ue_cfg.rx_port == 2200
        assert ue_cfg.tx_port == 3200
        assert ue_cfg.path_loss_db is None

    def test_parse_zmq_proxy_cfg_missing_path_losses(self):
        elements = {
            "ip_addr": "192.168.1.10",
            "slow_down_ratio": 1,
            "rx_ports": {
                "core": 4000,
            },
            "tx_ports": {
                "core": 5000,
            },
            "path_losses_db": {},
        }

        cfg = ZMQProxyParser.parse_zmq_proxy_cfg(elements)

        core_cfg = cfg.get_component_cfg("core")
        assert core_cfg.path_loss_db is None
