import logging
import os
from typing import Optional

import yaml
from jinja2 import Environment, FileSystemLoader

from controller.folder_manager import FolderManager
from controller.patcher.patcher_utils import PatcherUtils
from controller.patcher.single_patcher_base import SinglePatcherBase
from model.ric_config import RICImplementation, ORAN_SC_RIC_SERVICE_IP_MAP
from model.setup_configuration import SetupConfiguration
from model.utils_config import BuildType


class NearRTRICPatcher(SinglePatcherBase):

    def __init__(self, patch_file_path: str, setup_config: SetupConfiguration, patcher_utils: PatcherUtils):
        super().__init__(patch_file_path, setup_config, patcher_utils)
        self._patch_file_path = patch_file_path
        self._setup_cfg = setup_config
        self._patcher_utils = patcher_utils

    def patch(self):
        logging.info("Patching RIC firmware...")
        if os.path.exists(self._patch_file_path):
            if self._setup_cfg.near_rt_ric.implementation == RICImplementation.ORAN_SC_RIC or \
                    self._setup_cfg.near_rt_ric.implementation == RICImplementation.FLEX_RIC:
                if self._setup_cfg.near_rt_ric.build_type == BuildType.DOCKER:
                    self.patch_config_file()
                    return self.patch_docker_compose()
                else:
                    logging.error("Native build patching for ORAN SC RIC and Flexric not supported")
                    exit(1)
        else:
            raise FileNotFoundError(f"Patch file not found: {self._patch_file_path}")

    def patch_config_file(self):
        if self._setup_cfg.near_rt_ric.implementation == RICImplementation.FLEX_RIC:
            patched_file = os.path.join(FolderManager.
                                        add_config_folder(self._patch_file_path, "ric",
                                                          str(self._setup_cfg.near_rt_ric.implementation.value)),
                                        "flexric.ini.j2")
            template_path = os.path.join(self._patch_file_path, "templates", "config", "ric",
                                         str(self._setup_cfg.near_rt_ric.implementation.value))
            env = Environment(loader=FileSystemLoader(template_path))
            template = env.get_template("flexric.ini.j2")
            config = {'e2term': {
                "ip": getattr(self._setup_cfg.near_rt_ric.ip_config, 'e2term_ip')
            }}

            rendered = template.render(**config)
            with open(patched_file, "w") as new_file:
                new_file.write(rendered)

    def patch_docker_compose(self) -> Optional[dict]:
        FolderManager.create_patch_folders(self._patch_file_path)

        if self._setup_cfg.near_rt_ric.implementation == RICImplementation.ORAN_SC_RIC:
            """ Patch the ORAN SC RIC docker-compose.yml file with custom IP addresses and subnet. """

            config = {
                'dbaas': {
                    "image": "nexus3.o-ran-sc.org:10002/o-ran-sc/ric-plt-dbaas:${DBAAS_VER}",
                    "ip": "${DBAAS_IP:-dummy}"
                },
                'rtmgr_sim': {
                    "image": "localhost:4000/rtmgr_sim:${SC_RIC_VERSION}-selftag",
                    "ip": "${RTMGR_SIM_IP:-dummy}"
                },
                'submgr': {
                    "image": "localhost:4000/ric-plt-submgr:${SUBMGR_VER}-selftag",
                    "ip": "${SUBMGR_IP:-dummy}"
                },
                'e2term': {
                    "image": "localhost:4000/ric-plt-e2:${E2TERM_VER}-selftag",
                    "ip": "${E2TERM_IP:-dummy}"
                },
                'appmgr': {
                    "image": "localhost:4000/ric-plt-appmgr:${APPMGR_VER}-selftag",
                    "ip": "${APPMGR_IP:-dummy}"
                },
                'e2mgr': {
                    "image": "localhost:4000/ric-plt-e2mgr:${E2MGR_VER}-selftag",
                    "ip": "${E2MGR_IP:-dummy}"
                },
                'python_xapp_runner': {
                    "image": "localhost:4000/python_xapp_runner:${SC_RIC_VERSION}-selftag",
                    "ip": "${XAPP_PY_RUNNER_IP:-dummy}"
                },
                'ric': {
                    "subnet": self._setup_cfg.near_rt_ric.ip_config.subnet
                }
            }

            for service, (env_var, ip_attr) in ORAN_SC_RIC_SERVICE_IP_MAP.items():
                ip_value = getattr(self._setup_cfg.near_rt_ric.ip_config, ip_attr)
                config[service]['ip'] = config[service]['ip'].replace('dummy', str(ip_value))
                config[service]['image'] = self._patcher_utils.replace_tag_and_image(config[service]['image'])

        elif self._setup_cfg.near_rt_ric.implementation == RICImplementation.FLEX_RIC:
            config = {'e2term': {
                "ip": getattr(self._setup_cfg.near_rt_ric.ip_config, 'e2term_ip')
            }, 'ric': {
                "subnet": self._setup_cfg.near_rt_ric.ip_config.subnet
            }}
        else:
            logging.error("Cannot patch unsupported RIC implementation!")
            exit(1)
        template_path = os.path.join(self._patch_file_path, "templates", "docker", "ric",
                                     str(self._setup_cfg.near_rt_ric.implementation.value))
        env = Environment(loader=FileSystemLoader(template_path))
        template = env.get_template("docker_compose.ini.j2")
        return yaml.safe_load(template.render(**config))

    def copy_config_files(self):
        if self._setup_cfg.near_rt_ric.implementation == RICImplementation.ORAN_SC_RIC:
            docker_files = ["dockerfile_appmgr", "dockerfile_submgr", "dockerfile_e2term", "dockerfile_rtmgr_sim",
                            "dockerfile_e2mgr", "dockerfile_ric-plt-xapp-frame-py"]
            src_paths = [[self._patch_file_path, "templates", "docker", "ric",
                          str(self._setup_cfg.near_rt_ric.implementation.value)] for _ in docker_files]
            dst_paths = [[self._setup_cfg.environment.build_dir, "oran-sc-ric", "ric", "images",
                          file.replace("dockerfile_", "")] for file in docker_files]

            super().copy_helper(src_paths, docker_files, dst_paths, ["Dockerfile" for _ in docker_files])
        elif self._setup_cfg.near_rt_ric.implementation == RICImplementation.FLEX_RIC:
            flex_ric_config_folder_patched = [self._patch_file_path, "patched", "config", "ric",
                                              self._setup_cfg.near_rt_ric.implementation.value]
            flex_ric_config_folder_template = [self._patch_file_path, "templates", "config", "ric",
                                               self._setup_cfg.near_rt_ric.implementation.value]
            flex_ric_docker_folder = [self._patch_file_path, "templates", "docker", "ric",
                                      self._setup_cfg.near_rt_ric.implementation.value]
            dest_dir = [self._setup_cfg.environment.build_dir, "flexric"]
            src_file_names = ["flexric.ini.j2", "flexric_entrypoint.sh", "Dockerfile"]
            file_names = ["flexric.conf", "flexric_entrypoint.sh", "Dockerfile"]
            super().copy_helper(
                [flex_ric_config_folder_patched, flex_ric_config_folder_template, flex_ric_docker_folder],
                src_file_names, [dest_dir, dest_dir, dest_dir], file_names)
        else:
            logging.error(f"{str(self._setup_cfg.near_rt_ric.implementation.value)} is not implemented yet.")
            exit(1)

    def patch_env_file(self, env_dict: dict) -> dict:
        if self._setup_cfg.near_rt_ric.implementation == RICImplementation.ORAN_SC_RIC:
            template_path = os.path.join(self._patch_file_path, "templates", "config", "ric",
                                         str(self._setup_cfg.near_rt_ric.implementation.value), )

            env = Environment(loader=FileSystemLoader(template_path))
            template = env.get_template("oran_sc_ric_env.ini.j2")
            rendered = template.render(
                near_rt_ric=self._setup_cfg.near_rt_ric)

            env_dict_oran_sc_ric = PatcherUtils.load_env_file_str_helper(rendered.split('\n'))
            return env_dict | env_dict_oran_sc_ric
        if self._setup_cfg.near_rt_ric.implementation == RICImplementation.FLEX_RIC:
            logging.info("No .env file required for Flexric")
            return env_dict
        else:
            logging.error("Unsupported RIC Implementation")
            exit(1)
