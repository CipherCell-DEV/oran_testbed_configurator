import enum
import yaml

rootpath = "/workspaces/srsrantestenvironment-ssh-vm1/"


def load_yaml(path):
    with open(path, 'r') as file:
        configuration = yaml.safe_load(file)
    return configuration

def save_config(path, config):
    with open(path , "w") as file:
        file.write("{}".format(config))

def patch_volumes(configuration):
    for key, service in configuration["services"].items():
        if "volumes" in service:
            for index2,element in enumerate(service["volumes"]):
                if element.startswith("./"):
                    configuration["services"][key]["volumes"][index2] = rootpath + element[2:]
    output_yaml = yaml.safe_dump(configuration)
    return output_yaml





if __name__ == "__main__":
    config = load_yaml("/workspaces/srsrantestenvironment-ssh-vm1/patches/patched/docker/gnb_ue.yml")
    config = patch_volumes(configuration=config)
    print(config)
    save_config("/workspaces/srsrantestenvironment-ssh-vm1/patches/patched/kubernetes/gnb_ue/patched/gnb_ue.yml", config)
