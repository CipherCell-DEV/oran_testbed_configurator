<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./doc/cipher_cell_configurator_logo.svg">
    <img alt="Ciphercell logo" src="./doc/cipher_cell_configurator_logo_black.svg" width="500">
  </picture>
</p>

## Overview

> 🛠 
> **O-RAN/5G testbed deployment made simple — platform-independent, centrally configured, and fully adjustable.** 

This repository provides an automated tool for configuring and managing all components in an O-RAN/5G testbed.  
It consists of the following components:  

- Near-Real-Time RIC  
- 5G Core  
- gNodeB  
- User Equipment (UE)

### Features

>![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)  
> Supports a fully **fully containerized** environment, ensuring consistency across systems and simplifying setup and maintenance.  
>
> **Tested platforms:** </br>![Linux](https://img.shields.io/badge/Platform-Linux-lightgrey?logo=linux) ![macOS](https://img.shields.io/badge/Platform-macOS-lightgrey?logo=apple)


- **Centralized configuration** of all components, including:
  - Network configuration  
  - Build type (native or Docker)  
  - Definition of multiple UEs
  - Component-specific parameters (e.g., gain rates, eSIM settings)

### Quick Start

Set up a simple **Dockerized O-RAN test environment** in just two commands.

**Prerequisites:**  
- Git  
- Python 3
- docker
- docker compose

**1. Clone the repository:**  
```bash
git clone git@github.com:CipherCell-DEV/oran-deploy-manager.git
cd oran-deploy-manager[README.md](README.md)
```

2. Start the environment:

```bash
./run_all.sh
```

 This command will:  
 1. Create a virtual Python environment and install all required Python packages  
 2. Set up the Docker containers  
 3. Start the Near-Real-Time RIC, 5G Core, gNB, and UE in the correct order  

All components run in a fully Dockerized environment, ready for immediate experimentation.

> ⚠️ **Note:** Compiling the gNB and UE within the Docker environment can take **up to one hour**. Please be patient!

### Documentation

Full setup and usage instructions are available in the [CipherCell Wiki](https://florianfrank.github.io/CipherCellWiki/docs/ciphercell_configurator/configurator-overview/).


### Interface Monitoring

The srsran gNB can generate `.pcap` files for various interfaces. 
Those files are stored in the [log](logs/) directory, which is defined in the [setup configuration](scripts/config/sample_configuration.yml). Traffic logging can be de-/activated by modifying the `pcap` section the the [srsran gNB configuration file](repositories/srsRAN_Project/configs/gnb_zmq.yaml). 

See the [official documantation](https://docs.srsran.com/projects/project/en/latest/user_manuals/source/config_ref.html) for further information.

If you want to inspect the using wireshark you need to apply the following settings first (as described in the [official documentation](https://docs.srsran.com/projects/project/en/latest/user_manuals/source/outputs.html)). Make sure your installation of wireshark is up to date.

#### Enable Protocols:
- Analyze -> Enabled Protocols -> MAC-NR: mac_nr_udp
- Edit->Preferences->Protocols->MAC-NR: Enable both checkboxes “Attempt to…”; Set LCID->DRB mapping to “From configuration protocol”

- Analyze -> Enabled Protocols -> RLC-NR: rlc_nr_udp

- Edit->Preferences->Protocols->NAS-5GS and enable “Try to detect and decode 5G-EA0 ciphered messages”.



#### Set DLT_USER
Go to Edit->Preferences->Protocols->DLT_USER->Edit and set the following values:

| DLT | protocol |
| --- | -------- |
|149| udp |
|152| ngap |
|153| e1ap |
|154| f1ap |
|155| e2ap |
|156| gtp |
|157| mac-nr-framed |
