import enum
import time
import yaml

rootpath = "/workspaces/srsrantestenvironment-ssh-vm1/"


def load_yaml(path):
    with open(path, 'r') as file:
        configuration = yaml.safe_load(file)
    return configuration

def save_config(path, config):
    with open(path , "w") as file:
        file.write("{}".format(yaml.safe_dump(config)))

def patch_volumes(configuration):
    for key, service in configuration["services"].items():
        if "volumes" in service:
            for index2,element in enumerate(service["volumes"]):
                if element.startswith("./"):
                    configuration["services"][key]["volumes"][index2] = rootpath + element[2:]
    return configuration

def patch_build(configuration):
    for key, service in configuration["services"].items():
        if "build" in service:
            if service["build"].startswith("./"):
                configuration["services"][key]["build"] = rootpath + service["build"][2:]
    return configuration

def add_image(config, registry, repo):
    for service in config["services"]:
        config["services"][service]["image"] = registry + "/" + repo + "/" + service + ":" + str(time.time())
    return config





if __name__ == "__main__":
    config = load_yaml("/workspaces/srsrantestenvironment-ssh-vm1/patches/patched/docker/gnb_ue.yml")
    config = patch_volumes(configuration=config)
    config = patch_build(config)
    config = add_image(config, "132.231.14.130:8080", "ciphercell/deployment")
    print(yaml.safe_dump(config))
    save_config("/workspaces/srsrantestenvironment-ssh-vm1/patches/patched/kubernetes/gnb_ue/patched/gnb_ue.yml", config)
