"""
This module contains a collection of sample JSON payloads to test the API endpoint
"""

ue_list_payload = {
    "ip_range": "10.45.0.0",
    "gateway": "10.45.0.1",
    "ues": [
        {
            "name": "ue1",
            "implementation": "srs_4g",
            "repository": "https://github.com/srsran/srsRAN_4G.git",
            "commit": "1fab3df863f66fdb6c3b34f1b39e745dbcb12d5e",
            "build_type": "docker",
            "ip": "10.45.1.2",
            "srate": 11.52e6,
            "usim": {
                "mode": "soft",
                "algo": "milenage",
                "opc": "63bfa50ee6523365ff14c1f45f88737d",
                "key": "00112233445566778899aabbccddeeff",
                "imsi": "001010123456789",
                "imei": "353490069873319",
            },
            "gateway": {
                "netns": "ue1",
                "ip_devname": "tun_srsue",
                "ip_netmask": "255.255.255.0",
            },
        },
        {
            "name": "ue2",
            "implementation": "srs_4g",
            "repository": "https://github.com/srsran/srsRAN_4G.git",
            "commit": "1fab3df863f66fdb6c3b34f1b39e745dbcb12d5e",
            "build_type": "docker",
            "ip": "10.45.1.3",
            "srate": 11.52e6,
            "usim": {
                "mode": "soft",
                "algo": "milenage",
                "opc": "63bfa50ee6523365ff14c1f45f88737d",
                "key": "00112233445566778899aabbccddef00",
                "imsi": "001010123456790",
                "imei": "353490069873319",
            },
            "gateway": {
                "netns": "ue2",
                "ip_devname": "tun_srsue",
                "ip_netmask": "255.255.255.0",
            },
        },
        {
            "name": "ue3",
            "implementation": "srs_4g",
            "repository": "https://github.com/srsran/srsRAN_4G.git",
            "commit": "1fab3df863f66fdb6c3b34f1b39e745dbcb12d5e",
            "build_type": "docker",
            "ip": "10.45.1.4",
            "srate": 11.52e6,
            "usim": {
                "mode": "soft",
                "algo": "milenage",
                "opc": "63bfa50ee6523365ff14c1f45f88737d",
                "key": "00112233445566778899aabbccddef01",
                "imsi": "001010123456791",
                "imei": "353490069873319",
            },
            "gateway": {
                "netns": "ue3",
                "ip_devname": "tun_srsue",
                "ip_netmask": "255.255.255.0",
            },
        },
    ],
}

ric_payload = {
    "implementation": "oran_sc_ric",
    "repository": "https://github.com/srsran/oran-sc-ric.git",
    "commit": "e44a7ce239b3c908e842163f1d57cbb4ba43fd0a",
    "release": "i",
    "build_type": "docker",
    "ip_config": {
        "subnet": "10.0.2.0/24",
        "dbaas_ip": "10.0.2.12",
        "e2term_ip": "10.0.2.10",
        "e2mgr_ip": "10.0.2.11",
        "submgr_ip": "10.0.2.13",
        "appmgr_ip": "10.0.2.14",
        "rtmgr_sim_ip": "10.0.2.15",
        "xapp_runner_ip": "10.0.2.20",
    },
}

ue_payload = {
    "name": "ue4",
    "implementation": "srs_4g",
    "repository": "https://github.com/srsran/srsRAN_4G.git",
    "commit": "1fab3df863f66fdb6c3b34f1b39e745dbcb12d5e",
    "build_type": "docker",
    "ip": "10.45.1.5",
    "srate": 11.52e6,
    "usim": {
        "mode": "soft",
        "algo": "milenage",
        "opc": "63bfa50ee6523365ff14c1f45f88737d",
        "key": "00112233445566778899aabbccddef01",
        "imsi": "001010123456791",
        "imei": "353490069873319",
    },
    "gateway": {
        "netns": "ue4",
        "ip_devname": "tun_srsue",
        "ip_netmask": "255.255.255.0",
    },
}
