import os

from controller.builder.build_runner import BuildRunner
from controller.component_checkout_manager import ComponentCheckoutManager
from controller.demo_runner import DemoRunner
from controller.patcher.firmware_patcher import FirmwarePatcher
from model.setup_configuration import SetupConfiguration
from model.utils_config import FILE_DIR
from view.live_console_view import LiveView


def patch_firmware(setup_cfg: SetupConfiguration):
    """
    Apply required firmware and Docker image patches for the demo environment.
    """
    print("\n***********Patch Components***********\n")
    fw_patcher = FirmwarePatcher(setup_configuration=setup_cfg,
                                 patch_file_path=os.path.join(FILE_DIR, "../..", "patches"))

    if not fw_patcher.patch_single_docker_compose():
        return False

    fw_patcher.copy_files_to_location()
    return True, fw_patcher.get_images_to_push()


def build_firmware(setup_cfg: SetupConfiguration, images_to_push: list[str]) -> bool:
    """
    Build all software components required for the demo (RIC, 5G Core, gNB/UE).
    """
    print("\n***********Build Components***********\n")
    build_runner = BuildRunner(setup_configuration=setup_cfg)

    if setup_cfg.dialog.build_near_rt_ric:
        if not build_runner.build_ric():
            return False

    if setup_cfg.dialog.build_core_net:
        if not build_runner.build_5g_core():
            return False

    if setup_cfg.dialog.build_gnb:
        if not build_runner.build_gnb():
            return False

    if setup_cfg.dialog.build_ue:
        if not build_runner.build_ues():
            return False

    if not build_runner.push_images(images_to_push):
        return False

    return True


def run_demo(setup_cfg: SetupConfiguration):
    """
    Start the demo environment and launch the live console viewer.
    """
    print("\n***********Run Demo***********\n")
    demo_runner = DemoRunner(setup_cfg)
    demo_runner.create_programs()
    view = LiveView(demo_runner)
    view.setup()
    view.start_programs()
    view.connect_view()


def checkout_repositories(setup_cfg: SetupConfiguration) -> tuple[bool, str]:
    """
    Clone (check out) all repositories required for the current setup configuration.
    """

    component_checkout_mgr = ComponentCheckoutManager(setup_config=setup_cfg)
    if not component_checkout_mgr.checkout_ric():
        return False, component_checkout_mgr.get_last_error()

    if not component_checkout_mgr.checkout_5g_core():
        return False, component_checkout_mgr.get_last_error()

    if not component_checkout_mgr.checkout_gnb():
        return False, component_checkout_mgr.get_last_error()

    if not component_checkout_mgr.checkout_ue():
        return False, component_checkout_mgr.get_last_error()

    return True, ""
