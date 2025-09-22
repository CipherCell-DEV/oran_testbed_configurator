<img src="doc/cipher_cell_configurator_logo.svg" alt="Logo" width="400"/>

## Overview

> 🛠 
> **O-RAN/5G testbed deployment made simple — platform-independent, centrally configured, and fully adjustable.** 

This repository provides an automated tool for configuring and managing all components in an O-RAN/5G testbed.  
It consists of the following components:  

- Near-Real-Time RIC  
- 5G Core  
- gNodeB  
- User Equipment (UE)

> ![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)  
> The environment is **fully containerized** with Docker, ensuring consistency across systems and simplifying setup and maintenance.

The implementation was tested on the following systems:

![Platform: Linux](https://img.shields.io/badge/Platform-Linux-lightgrey?logo=linux)
![Platform: macOS](https://img.shields.io/badge/Platform-macOS-lightgrey?logo=apple)


### Features

- **Centralized configuration** of all components, including:
  - Network configuration  
  - Build type (native or Docker)  
  - Definition of multiple UEs
  - Component-specific parameters (e.g., gain rates, eSIM settings)

A detailed documentation can be find in our wiki:

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
cd oran-deploy-manager
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

Full setup and usage instructions are available in the [CipherCell Wiki](https://florianfrank.github.io/CipherCellWiki/docs/category/setup-srsran-based-test-environment).