import os
from typing import Optional

import yaml
from fontTools.afmLib import componentRE
from jinja2 import Environment, FileSystemLoader

from controller.folder_manager import FolderManager
from controller.patcher.patcher_utils import PatcherUtils
from controller.patcher.single_patcher_base import SinglePatcherBase
from model.setup_configuration import SetupConfiguration


class ZMQProxyPatcher(SinglePatcherBase):

    def __init__(self, patch_file_path: str, setup_config: SetupConfiguration, patcher_utils: PatcherUtils):
        super().__init__(patch_file_path, setup_config, patcher_utils)

    def patch(self):
        template_path = os.path.join(self._patch_file_path, "templates", "scripts", "zmq-proxy")
        env = Environment(loader=FileSystemLoader(template_path))
        template = env.get_template("zmq_proxy.ini.j2")

        component_data = self._setup_cfg.zmq_proxy.get_component_data()
        for ue in self._setup_cfg.ue.ues:
            component_data[ue.name]['ip'] = str(ue.ip)
        component_data['gnb']['ip'] = str(self._setup_cfg.gnb.ip_config.ru_sdr)

        data = {
            'ue_data': component_data,
            'slow_down_ratio': self._setup_cfg.zmq_proxy.slow_down_ratio,
            'sample_rate': int(self._setup_cfg.gnb.srate * 1e6),  # Needed in Hz, not in MHz
        }

        rendered = template.render(**data)
        output_folder = os.path.join(self._setup_cfg.environment.build_dir, 'zmq-proxy')
        FolderManager.create_folder(output_folder, 'zmq-proxy')
        with open(os.path.join(output_folder, "zmq_proxy.py"), "w") as new_file:
            new_file.write(rendered)

    def patch_config_file(self):
        pass

    def patch_docker_compose(self) -> Optional[dict]:
        FolderManager.create_patch_folders(self._patch_file_path)
        template_path = os.path.join(self._patch_file_path, "templates", "docker", "zmq-proxy")
        env = Environment(loader=FileSystemLoader(template_path))
        template = env.get_template("docker-compose.ini.j2")
        rendered = template.render(
            image=f"{self._setup_cfg.environment.docker_registry}/zmq_proxy{self._patcher_utils.get_tag_or_empty_string(':')}",
            zmq_proxy_ip=self._setup_cfg.zmq_proxy.ip_addr,
            nr_of_ues=len(self._setup_cfg.ue.ues),
        )
        return yaml.safe_load(rendered)['services']

    def copy_config_files(self):
        FolderManager.create_folder(os.path.join(self._setup_cfg.environment.build_dir, 'zmq-proxy'), 'zmq-proxy')
        paths_src = [[self._patch_file_path, "templates", "docker", "zmq-proxy"]]
        paths_dst = [[self._setup_cfg.environment.build_dir, 'zmq-proxy']]
        file_names = ['Dockerfile']
        super().copy_helper(paths_src, file_names, paths_dst, file_names)
