<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./doc/cipher_cell_configurator_logo.svg">
    <img alt="Ciphercell logo" src="./doc/cipher_cell_configurator_logo_black.svg" width="300">
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

Full setup and usage instructions are available in the [CipherCell Wiki](https://florianfrank.github.io/CipherCellWiki/docs/category/ciphercell-configurator).