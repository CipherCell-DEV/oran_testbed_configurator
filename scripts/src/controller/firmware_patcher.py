import logging
import os
import shutil
import textwrap
from typing import Dict, Any

import yaml

from controller.folder_manager import FolderManager
from model.core_config import CoreImplementation
from model.ric_config import ORAN_SC_RIC_SERVICE_IP_MAP, RICImplementation
from model.setup_configuration import SetupConfiguration
from model.ue_config import USIMMode, USIMAlgo
from model.utils_config import BuildType


class FirmwarePatcher:
    """ Class to patch firmware configuration files based on the provided setup configuration.
    It supports patching for different components like RIC, 5G Core, gNB, and UE.
    """

    def __init__(self, setup_configuration: SetupConfiguration, patch_file_path: str):
        self._setup_cfg = setup_configuration
        self._patch_file_path = patch_file_path

    def patch_single_docker_compose(self) -> bool:
        """
        Combine RIC, 5G Core, and UE/gNB docker-compose fragments
        into a single docker-compose file.

        Returns:
            bool: True if the combined file was successfully created,
                  False otherwise.
        """
        try:
            ric_config: Dict[str, Any] = self.patch_ric_firmware()
            core_config: Dict[str, Any] = self.patch_5g_core()
            ue_gnb_config: Dict[str, Any] = self.patch_ue_gnb_docker()

            single_config: Dict[str, Any] = {
                "version": ric_config.get("version", "3.9"),
                "services": dict(ric_config.get("services", {})),
                "networks": dict(ric_config.get("networks", {}))
            }

            if self._setup_cfg.core_5g.implementation == CoreImplementation.SRS:
                if "volumes" in core_config:
                    single_config["volumes"] = dict(core_config["volumes"])
            else:
                logging.error(
                    "Currently only SRS RAN is supported for 5G Core implementation."
                )
                return False

            single_config["networks"].update(core_config.get("networks", {}))
            single_config["services"].update(core_config.get("services", {}))
            single_config["services"].update(ue_gnb_config.get("services", {}))

            if "networks" in ue_gnb_config and "internal_net" in ue_gnb_config["networks"]:
                single_config["networks"]["internal_net"] = ue_gnb_config["networks"]["internal_net"]

            combined_file_path = os.path.join(
                self._patch_file_path, "patched", "docker", "docker_combined.yml"
            )
            with open(combined_file_path, "w", encoding="utf-8") as new_file:
                yaml.safe_dump(
                    single_config,
                    new_file,
                    default_flow_style=False,
                    sort_keys=False,
                    indent=2
                )

            logging.info(f"Combined docker-compose written to {combined_file_path}")
            return True

        except Exception as e:
            logging.exception(f"Failed to patch single docker-compose: {e}")
            return False

    def _patch_oran_sc_docker_compose(self):
        FolderManager.create_patch_folders(self._patch_file_path)
        """ Patch the ORAN SC RIC docker-compose.yml file with custom IP addresses and subnet. """
        patch_file_path = os.path.join(self._patch_file_path, "templates", "docker", "oran_sc_docker.yml")

        try:
            with open(patch_file_path, "r") as patch_file:
                patch_content = yaml.safe_load(patch_file)

            logging.info("Patching ORAN SC RIC docker-compose.yml with custom IP addresses...")

            for service, (env_var, ip_attr) in ORAN_SC_RIC_SERVICE_IP_MAP.items():
                ip_value = getattr(self._setup_cfg.near_rt_ric.ip_config, ip_attr)
                patch_content["services"][service]["networks"]["ric_network"]["ipv4_address"] = (
                    f"${{{env_var}:-{ip_value}}}"
                )

            subnet_value = self._setup_cfg.near_rt_ric.ip_config.subnet
            patch_content["networks"]["ric_network"]["ipam"]["config"][0]["subnet"] = (
                f"{subnet_value}"
            )

            return patch_content

        except yaml.YAMLError as e:
            logging.error(f"Failed to parse YAML patch file: {e}")
            raise

    def _patch_srs_ran_sc_docker_compose(self):
        FolderManager.create_patch_folders(self._patch_file_path)
        patch_file_path = os.path.join(self._patch_file_path, "templates", "docker", "srs_ran_5gc.yml")

        # Force quotes on all strings
        def str_presenter(dumper, data):
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')

        # Optional: force inline lists for Docker Compose arrays
        def inline_list_presenter(dumper, data):
            return dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=True)

        yaml.add_representer(str, str_presenter)
        yaml.add_representer(list, inline_list_presenter)

        try:
            with open(patch_file_path, "r") as patch_file:
                patch_content = yaml.safe_load(patch_file)

                patch_content['services']['5gc']['networks']['ran'][
                    'ipv4_address'] = f"${{OPEN5GS_IP:-{self._setup_cfg.core_5g.ip}}}"

                patch_content['networks']['ran']['ipam']['config'][0][
                    'subnet'] = f"{self._setup_cfg.core_5g.network}"

                return patch_content

        except yaml.YAMLError as e:
            logging.error(f"Failed to parse YAML patch file: {e}")
            raise

    def _get_usim_mode(self):
        if self._setup_cfg.ue[0].usim.mode == USIMMode.HARD:
            return "hard"
        elif self._setup_cfg.ue[0].usim.mode == USIMMode.SOFT:
            return "soft"

    def _get_usim_algorithm(self):
        if self._setup_cfg.ue[0].usim.algo == USIMAlgo.XOR:
            return "xor" # NOT TESTED
        elif self._setup_cfg.ue[0].usim.algo == USIMAlgo.COMP:
            return "comp" # NOT TESTED
        elif self._setup_cfg.ue[0].usim.algo == USIMAlgo.MILENAGE:
            return "milenage"

    def _patch_gnb_docker(self, patch_content: dict):
        FolderManager.create_patch_folders(self._patch_file_path)
        pass  # TODO implement patching!!

    def _patch_ue_docker(self, patch_content: dict):
        FolderManager.create_patch_folders(self._patch_file_path)
        for i, ue in enumerate(self._setup_cfg.ue):
            ue_dict = {
                "services": {
                    f"{ue.name}": {
                        "build": "./srsRAN_4G",
                        "container_name": f"{ue.name}",
                        "platform": "linux/amd64",
                        "networks": {
                            "internal_net": {"ipv4_address": f"{ue.ip}"},
                        },
                        "user": "root",
                        "privileged": True,
                        "cap_add": ["NET_ADMIN"],
                        "volumes": [
                            "./srsRAN_4G/configs:/app/configs"
                        ],
                        "entrypoint": f"/app/ue_entrypoint.sh {ue.name}",
                        "stdin_open": True,
                        "tty": True,
                        "restart": "unless-stopped"
                    }
                }
            }
            patch_content['services'].update(ue_dict['services'])

    def _patch_ue_config(self):
        for i, ue in enumerate(self._setup_cfg.ue):
            ue_config = f"""
    [rf]
    freq_offset = 0
    tx_gain = 50
    rx_gain = 40
    srate = {ue.srate}
    nof_antennas = 1

    device_name = zmq
    device_args = tx_port=tcp://0.0.0.0:2001,rx_port=tcp://{self._setup_cfg.gnb.ip_config.ru_sdr}:2000,base_srate={ue.srate}

    [rat.eutra]
    dl_earfcn = 2850
    nof_carriers = 0

    [rat.nr]
    bands = 3
    nof_carriers = 1

    [pcap]
    enable = none
    mac_filename = /tmp/ue_mac.pcap
    mac_nr_filename = /tmp/ue_mac_nr.pcap
    nas_filename = /tmp/ue_nas.pcap

    [log]
    all_level = info
    phy_lib_level = none
    all_hex_limit = 32
    filename = /tmp/ue.log
    file_max_size = -1

    [usim]
    mode = {self._get_usim_mode()}
    algo = {self._get_usim_algorithm()}
    opc  = {ue.usim.opc}
    k    = {ue.usim.k}
    imsi = {ue.usim.imsi}
    imei = {ue.usim.imei}

    [rrc]
    release = 15
    ue_category = 4

    [nas]
    apn = srsapn
    apn_protocol = ipv4

    [gw]
    netns = {ue.gateway.netns}
    ip_devname = {ue.gateway.ip_devname}
    ip_netmask = {ue.gateway.ip_netmask.broadcast_address}

    [gui]
    enable = false
    """
            ue_config = textwrap.dedent(ue_config).lstrip("\n")

            out_path = os.path.join(
                self._patch_file_path, "patched", "config", f"{ue.name}_zmq.conf"
            )
            with open(out_path, "w") as new_file:
                new_file.write(ue_config)

    def _patch_gnb_config(self):
        patch_file_path = os.path.join(self._patch_file_path, "templates", "config", "gnb_zmq.yaml")
        new_file_path = os.path.join(self._patch_file_path, "patched", "config", "gnb_zmq.yaml")

        try:
            with open(patch_file_path, "r") as patch_file:
                patch_content = yaml.safe_load(patch_file)

                patch_content['cu_cp']['amf']['addr'] = f"{self._setup_cfg.core_5g.ip}"

                patch_content['cu_cp']['amf']['bind_addr'] = f"{self._setup_cfg.gnb.ip_config.cu_cp}"

                patch_content['ru_sdr']['device_args'] = (
                    f"tx_port=tcp://0.0.0.0:2000,"
                    f"rx_port=tcp://{self._setup_cfg.ue[0].ip}:2001,"  # TODO Allow multiple UEs
                    f"base_srate={self._setup_cfg.gnb.srate}"
                )

                patch_content['ru_sdr']['srate'] = float(self._setup_cfg.gnb.srate) / 1e6
                patch_content['ru_sdr']['tx_gain'] = self._setup_cfg.gnb.tx_gain
                patch_content['ru_sdr']['rx_gain'] = self._setup_cfg.gnb.rx_gain

                patch_content['e2']['bind_addr'] = f"{self._setup_cfg.gnb.ip_config.e2}"
                patch_content['e2']['addr'] = f"{self._setup_cfg.near_rt_ric.ip_config.e2term_ip}"

                with open(new_file_path, "w") as new_file:
                    yaml.safe_dump(
                        patch_content,
                        new_file,
                        default_flow_style=False,
                        sort_keys=False
                    )

        except yaml.YAMLError as e:
            logging.error(f"Failed to parse YAML patch file: {e}")
            raise

    def _patch_gnb_ue_docker(self):
        patch_file_path = os.path.join(self._patch_file_path, "templates", "docker", "gnb_ue.yml")

        try:
            with open(patch_file_path, "r") as patch_file:
                patch_content = yaml.safe_load(patch_file)

                self._patch_gnb_docker(patch_content)
                self._patch_ue_docker(patch_content)

                self._patch_ue_config()
                self._patch_gnb_config()

                return patch_content

        except yaml.YAMLError as e:
            logging.error(f"Failed to parse YAML patch file: {e}")
            raise

    def copy_files_to_location(self):
        logging.info("Copying patched files to build directory...")
        FolderManager.create_project_config_folders(self._setup_cfg)

        file_mappings = [
            (
                os.path.join(self._patch_file_path, "patched", "config", "gnb_zmq.yaml"),
                os.path.join(self._setup_cfg.environment.build_dir, "srsRAN_Project", "configs", "gnb_zmq.yaml"),
            ),
            (
                os.path.join(self._patch_file_path, "patched", "docker", "docker_combined.yml"),
                os.path.join(self._setup_cfg.environment.build_dir, "docker-compose.yml"),
            ),
            (
                os.path.join(self._patch_file_path, "templates", "docker", "dockerfile_ue"),
                os.path.join(self._setup_cfg.environment.build_dir, "srsRAN_4G", "Dockerfile"),
            ),
            (
                os.path.join(self._patch_file_path, "templates", "config", "ue_entrypoint.sh"),
                os.path.join(self._setup_cfg.environment.build_dir, "srsRAN_4G", "ue_entrypoint.sh"),
            ),
            (
                os.path.join(self._patch_file_path, "templates", "docker", "dockerfile_gnb"),
                os.path.join(self._setup_cfg.environment.build_dir, "srsRAN_Project", "Dockerfile"),
            ),
            (
                os.path.join(self._patch_file_path, "templates", "config", ".env"),
                os.path.join(self._setup_cfg.environment.build_dir, ".env"),
            )
        ]

        # Allow dynamic adding of additional ue configurations
        for ue in self._setup_cfg.ue:
            file_mappings.append((
                os.path.join(self._patch_file_path, "patched", "config", f"{ue.name}_zmq.conf"),
                os.path.join(self._setup_cfg.environment.build_dir, "srsRAN_4G", "configs", f"{ue.name}_zmq.conf"),
            ))

        for src, dst in file_mappings:
            try:
                shutil.copy(src, dst)
                src = src.replace(f'{self._patch_file_path}' + '/', '')
                dst = dst.replace(f'{self._setup_cfg.environment.build_dir}' + '/', '')
                logging.info("Copied file from %s to %s", src, dst)
            except FileNotFoundError as e:
                logging.error("Source file not found: %s", src)
                raise
            except PermissionError as e:
                logging.error("Permission denied while copying %s to %s", src, dst)
                raise
            except Exception as e:
                logging.exception("Unexpected error while copying %s to %s", src, dst)
                raise

    def _patch_oran_sc(self):
        if self._setup_cfg.environment.build_type == BuildType.DOCKER:
            return self._patch_oran_sc_docker_compose()
        else:
            logging.warning("Native build patching for ORAN SC RIC is not implemented yet.")

    def patch_5g_core(self):
        if self._setup_cfg.environment.build_type == BuildType.DOCKER:
            return self._patch_srs_ran_sc_docker_compose()
        else:
            logging.warning("Native build patching for srsRAN 5G core is not implemented yet.")

    def patch_ric_firmware(self):
        logging.info("Patching RIC firmware...")
        if os.path.exists(self._patch_file_path):
            if self._setup_cfg.near_rt_ric.type == RICImplementation.ORAN_SC_RIC:
                return self._patch_oran_sc()
        else:
            raise FileNotFoundError(f"Patch-Datei nicht gefunden: {self._patch_file_path}")

    def patch_ue_gnb_docker(self):
        logging.info("Patching gNB and UE firmware...")
        if os.path.exists(self._patch_file_path):
            if self._setup_cfg.gnb is not None:
                return self._patch_gnb_ue_docker()
        else:
            raise FileNotFoundError(f"Patch-Datei nicht gefunden: {self._patch_file_path}")
