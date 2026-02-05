import unittest

from controller.parser.ue_config_parser import UEConfigParser
from model.ue_config import USIMMode, USIMAlgo, UEGatewayCfg, UEInstCfg, UECfg
from model.ue_config import DefaultValuesUE, UEFieldIdentifiers

class TestUEConfigParser(unittest.TestCase):

    def setUp(self):
        # Example of minimal valid UE config
        self.valid_ue_dict = {
            "ues": [
                {
                    "UE1": {
                        "build_type": "docker",
                        "implementation": "srs_4g",
                        "repository": "http://github.com/ue-reo.git",
                        "commit": "latest",
                        UEFieldIdentifiers.IP_ADDR: "192.168.1.10",
                        UEFieldIdentifiers.SRATE: 10,
                        UEFieldIdentifiers.USIM: {
                            UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.MODE: "soft",
                            UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.ALGO: "milenage",
                            UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.OPC: "opc_val",
                            UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.KEY: "key_val",
                            UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.IMSI: "imsi_val",
                            UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.IMEI: "imei_val",
                        },
                        UEFieldIdentifiers.GATEWAY: {
                            UEFieldIdentifiers.GATEWAY_IDENTIFIERS.IP_NETMASK: "192.168.1.0/24"
                        },
                    }
                }
            ],
            "network": {
                UEFieldIdentifiers.IP_RANGE: "192.168.1.0/24",
                UEFieldIdentifiers.GATEWAY: "192.168.1.1",
            },
        }

    def test_parse_valid_config(self):
        cfg: UECfg = UEConfigParser.parse_ue_cfg(self.valid_ue_dict)
        self.assertEqual(len(cfg.ues), 1)
        ue: UEInstCfg = cfg.ues[0]
        self.assertEqual(ue.name, "UE1")
        self.assertEqual(str(ue.ip), "192.168.1.10")
        self.assertEqual(ue.srate, 10)
        self.assertEqual(ue.usim.mode, USIMMode.SOFT)
        self.assertEqual(ue.usim.algo, USIMAlgo.MILENAGE)
        self.assertEqual(str(cfg.ip_range), "192.168.1.0/24")
        self.assertEqual(str(cfg.gateway), "192.168.1.1")
        self.assertIsInstance(ue.gateway, UEGatewayCfg)
        self.assertEqual(str(ue.gateway.ip_netmask), "192.168.1.0/24")

    def test_missing_ues_key(self):
        with self.assertRaises(KeyError):
            UEConfigParser.parse_ue_cfg({})

    def test_multiple_ue_names(self):
        invalid_dict = {
            "ues": [
                {
                    "UE1": {}, "UE2": {}
                }
            ]
        }
        with self.assertRaises(ValueError):
            UEConfigParser.parse_ue_cfg(invalid_dict)

    def test_missing_ip(self):
        invalid_dict = {
            "ues": [
                {
                    "UE1": {
                        UEFieldIdentifiers.USIM: {
                            UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.MODE: "soft",
                            UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.ALGO: "milenage",
                            UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.OPC: "opc_val",
                            UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.KEY: "key_val",
                            UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.IMSI: "imsi_val",
                            UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.IMEI: "imei_val"
                        }
                    }
                }
            ]
        }
        with self.assertRaises(KeyError):
            UEConfigParser.parse_ue_cfg(invalid_dict)

    def test_invalid_ip(self):
        invalid_dict = {
            "ues": [
                {
                    "UE1": {
                        'build_type': 'docker',
                        'implementation': 'srs_4g',
                        'repository': 'http://github.com/ue-reo.git',
                        'commit': 'latest',
                        UEFieldIdentifiers.IP_ADDR: "300.0.0.1",
                        UEFieldIdentifiers.USIM: {
                            UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.MODE: "soft",
                            UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.ALGO: "milenage",
                            UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.OPC: "opc_val",
                            UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.KEY: "key_val",
                            UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.IMSI: "imsi_val",
                            UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.IMEI: "imei_val"
                        }
                    }
                }
            ]
        }
        with self.assertRaises(ValueError):
            UEConfigParser.parse_ue_cfg(invalid_dict)

    def test_missing_usim_field(self):
        invalid_dict = {
            "ues": [
                {
                    "UE1": {
                        UEFieldIdentifiers.IP_ADDR: "192.168.1.10",
                        UEFieldIdentifiers.USIM: {
                            # Missing MODE
                            UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.ALGO: "milenage",
                            UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.OPC: "opc_val",
                            UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.KEY: "key_val",
                            UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.IMSI: "imsi_val",
                            UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.IMEI: "imei_val"
                        }
                    }
                }
            ]
        }
        with self.assertRaises(KeyError):
            UEConfigParser.parse_ue_cfg(invalid_dict)