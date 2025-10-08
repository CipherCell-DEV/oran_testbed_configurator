import logging
import os

import yaml

from controller.folder_manager import FolderManager
from controller.patcher.patcher_utils import PatcherUtils
from controller.patcher.single_patcher_base import SinglePatcherBase
from model.core_config import CoreImplementation
from model.setup_configuration import SetupConfiguration
from model.utils_config import BuildType

from jinja2 import Environment, FileSystemLoader


class Core5GPatcher(SinglePatcherBase):
    """
     Patcher for 5G Core network configurations.

     Handles patching of docker-compose files and environment files for various
     5G core implementations (currently only 5GC with srsRAN is supported!).
     """

    def __init__(self, patch_file_path: str, setup_cfg: SetupConfiguration, patcher_utils: PatcherUtils):
        super().__init__(patch_file_path, setup_cfg, patcher_utils)

    def patch(self):
        if self._setup_cfg.core_5g.build_type == BuildType.DOCKER:
            self.patch_config_file()
            return self.patch_docker_compose()
        else:
            logging.error("Native build patching for srsRAN 5G core is not implemented yet. -> Exit Program")
            exit(1)

    def patch_docker_compose(self):
        if self._setup_cfg.core_5g.implementation == CoreImplementation.OPEN5GS_SRS:
            return self._open5gs_5gc_srs_patch_docker_compose()
        elif self._setup_cfg.core_5g.implementation == CoreImplementation.OPEN5GS:
            return self._open5gs_5gc_patch_docker_compose()
        else:
            logging.error("Unsupported 5G core implementation for docker patching.")
            exit(1)

    def _patch_open5gs_endpoint_script(self):
        template_path = os.path.join(self._patch_file_path, "templates", "config", "ran",
                                     str(self._setup_cfg.core_5g.implementation.value))
        env = Environment(loader=FileSystemLoader(template_path))
        template = env.get_template("open5gs_entrypoint.ini.j2")

        # TODO handle multiple UEs
        data = {
            'ue': {
                "ip_range": self._setup_cfg.ue.ip_range,
                "gateway": self._setup_cfg.ue.gateway,
                "imsi": self._setup_cfg.ue.ues[0].usim.imsi,
                "key": self._setup_cfg.ue.ues[0].usim.k,
                "opc": self._setup_cfg.ue.ues[0].usim.opc,
                "ip": self._setup_cfg.ue.ues[0].ip
            },
            'ran': {
                'mongodb_ip': self._setup_cfg.core_5g.network.mongodb_ip
            }
        }

        rendered = template.render(**data)
        out_path = os.path.join(FolderManager.add_config_folder(self._patch_file_path, "ran",
                                                                str(self._setup_cfg.core_5g.implementation.value)),
                                "open5gs_entrypoint.sh")
        with open(out_path, "w") as new_file:
            new_file.write(rendered)

    def _patch_open5gs_config_file(self):
        template_path = os.path.join(self._patch_file_path, "templates", "config", "ran",
                                     str(self._setup_cfg.core_5g.implementation.value))
        env = Environment(loader=FileSystemLoader(template_path))
        template = env.get_template("open5gs-5gc.ini.j2")

        data = {
            "ran": {
                "mongodb_ip": self._setup_cfg.core_5g.network.mongodb_ip,
            }
        }

        rendered = template.render(**data)

        out_path = os.path.join(FolderManager.add_config_folder(self._patch_file_path, "ran",
                                                                str(self._setup_cfg.core_5g.implementation.value)),
                                "open5gs-5gc.yml")
        with open(out_path, "w") as new_file:
            new_file.write(rendered)

    def patch_config_file(self):
        if self._setup_cfg.core_5g.implementation == CoreImplementation.OPEN5GS:
            self._patch_open5gs_endpoint_script()
            self._patch_open5gs_config_file()

    def patch_env_file(self, env_dict: dict) -> dict:
        if self._setup_cfg.core_5g.implementation == CoreImplementation.OPEN5GS_SRS:
            return self._open5gs_5gc_srs_patch_env_file(env_dict)
        else:
            logging.warning("Unsupported 5G core implementation for env file patching. Returning original env_dict.")
        return env_dict

    # *****************************************
    # **** Implementation Specific Methods ****
    # *****************************************
    def _open5gs_5gc_srs_patch_docker_compose(self):
        """
        Patch the docker-compose file for Open5GS 5G core with custom IP addresses and subnet.
        """
        FolderManager.create_patch_folders(self._patch_file_path)
        patch_file_path = os.path.join(self._patch_file_path, "templates", "docker", "ran",
                                       str(self._setup_cfg.core_5g.implementation.value), "srs_ran_5gc.yml")

        def str_presenter(dumper, data):
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')

        def inline_list_presenter(dumper, data):
            return dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=True)

        yaml.add_representer(str, str_presenter)
        yaml.add_representer(list, inline_list_presenter)

        try:
            with open(patch_file_path, "r") as patch_file:
                patch_content = yaml.safe_load(patch_file)

                patch_content['services']['5gc']['networks']['ran'][
                    'ipv4_address'] = f"${{OPEN5GS_IP:-{self._setup_cfg.core_5g.network.ip}}}"

                patch_content['networks']['ran']['ipam']['config'][0][
                    'subnet'] = f"{self._setup_cfg.core_5g.network.subnet}"

                patch_content['services']['5gc']['image'] = self._patcher_utils.replace_tag_and_image(
                    patch_content['services']['5gc']['image'])

                return patch_content

        except yaml.YAMLError as e:
            logging.error(f"Failed to parse YAML patch file: {e}")
            raise

    def _open5gs_5gc_patch_docker_compose(self):
        FolderManager.create_patch_folders(self._patch_file_path)
        patch_file_path = os.path.join(self._patch_file_path, "templates", "docker", "ran",
                                       str(self._setup_cfg.core_5g.implementation.value),
                                       "docker_compose_open5gs_5gc.yml")

        def str_presenter(dumper, data):
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')

        def inline_list_presenter(dumper, data):
            return dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=True)

        yaml.add_representer(str, str_presenter)
        yaml.add_representer(list, inline_list_presenter)

        try:
            with open(patch_file_path, "r") as patch_file:
                patch_content = yaml.safe_load(patch_file)

                patch_content['services']['mongodb']['networks']['ran'][
                    'ipv4_address'] = f'{self._setup_cfg.core_5g.network.mongodb_ip}'

                patch_content['services']['5gc']['networks']['ran'][
                    'ipv4_address'] = f'{self._setup_cfg.core_5g.network.ip}'

                patch_content['services']['5gc']['image'] = self._patcher_utils.replace_tag_and_image(
                    patch_content['services']['5gc']['image'])

                return patch_content

        except yaml.YAMLError as e:
            logging.error(f"Failed to parse YAML patch file: {e}")
            raise

    def _open5gs_5gc_srs_patch_env_file(self, env_dict: dict):
        """
        Patch environment file with UE IP base configuration for Open5GS 5G core.

        Validates that all UE IP addresses share the same /24 subnet prefix
        (first three octets) and sets the UE_IP_BASE environment variable accordingly.

        Args:
            env_dict: Existing environment variables dictionary.

        Returns:
            dict: Merged dictionary with original env_dict and 5GC-specific variables.
        """

        patch_file_path = os.path.join(self._patch_file_path, "templates", "config", "ran",
                                       str(self._setup_cfg.core_5g.implementation.value),
                                       "5gc_srsran_env")
        env_dict_5gc = PatcherUtils.load_env_file_helper(patch_file_path)

        # Check if there are any UEs
        if not self._setup_cfg.ue:
            raise ValueError("No UEs configured in setup configuration")

        base_ip = None
        for i, ue in enumerate(self._setup_cfg.ue.ues):
            # Validate UE has an IP
            if not hasattr(ue, 'ip') or ue.ip is None:
                raise ValueError(f"UE at index {i} has no IP address configured")

            ip_parts = str(ue.ip).split('.')
            if len(ip_parts) != 4:
                raise ValueError(f"Invalid IP format for UE {i}: {ue.ip}")

            if i == 0:
                base_ip = ip_parts
                env_dict_5gc['UE_IP_BASE'] = f"{base_ip[0]}.{base_ip[1]}.{base_ip[2]}"
            else:
                if ip_parts[0] != base_ip[0] or ip_parts[1] != base_ip[1] or ip_parts[2] != base_ip[2]:
                    raise ValueError(
                        f"UE IP {ue.ip} does not match base IP prefix "
                        f"{base_ip[0]}.{base_ip[1]}.{base_ip[2]}"
                    )

        return env_dict | env_dict_5gc

    def copy_config_files(self):
        if self._setup_cfg.core_5g.implementation == CoreImplementation.OPEN5GS:
            FolderManager.create_folder(os.path.join(self._setup_cfg.environment.build_dir, 'open5gs', 'config'),
                                        'open5gs')
            src_dirs = [
                [self._patch_file_path, "patched", "config", "ran", self._setup_cfg.core_5g.implementation.value],
                [self._patch_file_path, "patched", "config", "ran", self._setup_cfg.core_5g.implementation.value],

                [self._patch_file_path, "templates", "config", "ran", self._setup_cfg.core_5g.implementation.value],
                [self._patch_file_path, "templates", "config", "ran", self._setup_cfg.core_5g.implementation.value],

                [self._patch_file_path, "templates", "config", "ran", self._setup_cfg.core_5g.implementation.value],

                [self._patch_file_path, "templates", "docker", "ran", self._setup_cfg.core_5g.implementation.value]]

            dest_dirs = [[self._setup_cfg.environment.build_dir, "open5gs", "config"],
                         [self._setup_cfg.environment.build_dir, "open5gs", "config"],
                         [self._setup_cfg.environment.build_dir, "open5gs", "config"],
                         [self._setup_cfg.environment.build_dir, "open5gs", "config"],
                         [self._setup_cfg.environment.build_dir, "open5gs", "config"],
                         [self._setup_cfg.environment.build_dir, "open5gs"]]

            file_names = ["open5gs-5gc.yml", "open5gs_entrypoint.sh", 'add_users.py', 'setup_tun.py',
                          'subscriber_db.csv.example', 'Dockerfile']

            super().copy_helper(src_dirs, file_names, dest_dirs, file_names)
