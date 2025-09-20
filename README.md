## O-RAN Deployment Manager

<img src="doc/cipher_cell_configurator_logo.svg" alt="Logo" width="400"/>

The **O-RAN Deployment Manager** is an automated tool for configuring and managing all components in an O-RAN/5G testbed.  
It consists of the following components:  

- Near-Real-Time RIC  
- 5G Core  
- gNodeB  
- User Equipment (UE)

> ![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)  
> The environment is **fully containerized** with Docker, ensuring consistent behavior across systems and streamlining both setup and maintenance.

The implementation was tested on the following systems:

![Platform: Linux](https://img.shields.io/badge/Platform-Linux-lightgrey?logo=linux)
![Platform: macOS](https://img.shields.io/badge/Platform-macOS-lightgrey?logo=apple)


### Features

- **Centralized configuration** of all components, including:
  - Network configuration  
  - Build type (native or Docker)  
  - Definition of multiple UEs
  - Component-specific parameters (e.g., gain rates, eSIM settings)  


- Definition of specific Endpoints
  - To log data from different endpoints within the O-RAN ecosystem
  - Attach Security 

A detailed documentation can be find in our wiki:


[CipherCellWiki](https://florianfrank.github.io/CipherCellWiki/docs/category/setup-srsran-based-test-environment)