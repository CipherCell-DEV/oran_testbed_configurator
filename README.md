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
 3. Start the Near-Real-Time RIC, 5G Core, gNB, and UE in the correct order as defined in the [Demo Configuration File](scripts/config/demo_configuration.yml)

All components run in a fully Dockerized environment, ready for immediate experimentation.

> ⚠️ **Note:** Compiling the gNB and UE within the Docker environment can take **up to one hour**. Please be patient!

### Documentation

Full setup and usage instructions are available in the [CipherCell Wiki](https://florianfrank.github.io/CipherCellWiki/docs/ciphercell_configurator/configurator-overview/).

#### Demo Configuration file

The (run_all.sh)[run_all.sh] script builds all containers and binaries. To freely configure the programs to be run afterwards the [Demo Configuration File](scripts/config/demo_configuration.yml) can be adjusted. 

All Program output will be logged to the [logs/run_logs](logs/run_logs), unless otherwise specified in the demo config.

> ⚠️ **Note:** If the programs are started by tmux (see section Output Mode), they will pipe the entire pane output and input to the log file. (See tmux documentation for [tmux pipe-pane](https://man7.org/linux/man-pages/man1/tmux.1.html)).

##### Output Mode

The demo programs are either run by Python (as [subprocesses](https://docs.python.org/3/library/subprocess.html)) or are started inside dedicated [tmux](https://man7.org/linux/man-pages/man1/tmux.1.html) sessions, depending on the configuration. 

Each program may depend on other programs to be running first, which can be specifid in the programs dependency list.
A program is running if:
  - If a program has no `state_transitions` parameters, then a program is considered running as soon as it has been started
  - Sometimes a program may be more complex and may take a while to start up. For this, we implemented `state_transitions`, which are triggered by the programs output:
    - A stopped/not yet running program printing the line defined in `stop_to_init` will be considered "initializing"
    - An initializing program printing the line defined in `init_to_running` will be considered running.

In Python mode, a Python [Live Display](https://rich.readthedocs.io/en/latest/live.html) will show the output of all programs on screen. 

> ⚠️ **Note:** If the output data is too large to fit on a single screen, it will not show all output data. You can adjust the amount of output lines shown per program in the [Demo Configuration File](scripts/config/demo_configuration.yml)

In tmux mode, each program is started as a tmux pane. For better visibility, the amount of panes per session can be configured in the [Demo Configuration File](scripts/config/demo_configuration.yml). The run script will generate as many sessions as needed to accomodate all programs. 

After all programs have been started, the run script will ask to open the generated sessions using the terminal configured in the [Demo Configuration File](scripts/config/demo_configuration.yml). If declined, the tmux sessions will keep running in the background until the script is stopped.

##### Terminal configuration
To automatically open tmux session windows, the hosts terminal needs to be configured. Since this may differ vastly between (Linux-) distributions, you can add/configure custom terminals as follows in the [Demo Configuration File](scripts/config/demo_configuration.yml):

```yaml
used_terminal: "my-own-terminal"
terminals:
  - gnome-terminal:
      subprocess_prefix: ["gnome-terminal", "--", "bash", "-c"]
      subprocess_postfix: []
  - my-own-terminal:
      subprocess_prefix: ["my-own-terminal", "[....]", "[bash, sh, ...]", "[bash, sh, ... flags]"]
      subprocess_postfix: ["[....]"]
```
The prefix/postfix systax is used to wrap the underlying python subprocess call `subprocess.run([prefix|tmux attach-session -t ... | postfix])`. We hope that this approach allows to cover most kinds of terminals. 

If this solution does not work for you, you can connect to the running tmux sessions at any time using your own systems using `tmux attach-session -t [session_name]`. You can list all active sessions using `tmux ls`.

##### Program Configuration
You can easily configure the programs to be run in the [Demo Configuration File](scripts/config/demo_configuration.yml).

A individual program has the following structure:
```yaml
name: "name"
depends_on: [...]
command: ["...", "..."]
working_directory: ""
state_transitions:
  stop_to_init: "..."
  init_to_running: "..."
```

All program names must be unique. Use the `depends_on` to list program names, which must run before this program can be started. The actual program command to be sent to tmux/called by a python subprocess is defined in `command`. The state transitions are optional and can be used to handle long startup times. A state transition (Stopped -> Initializing -> Running) is triggered by the programs output.

> ⚠️ **Note:** Make sure the programs match the prevoious build step

There are 5 logical groups of programs. Each group shares a restart timeout, which causes a program to restart if it is stuck in the "initializing" state for too long
  - run_core: The 5g Core programs. Only the first program in the program list is executed
  - run_ric: The near real time ric. Only the first program in the program list is executed
  - run_gnb: The base station. Only the first program in the program list is executed
  - run_ue: User Endpoints. Support for muttilpe UEs is currently WIP
  - run_misc: Here user defined programs can be defined. They may depend on previous programs. All programs in the program list are executed

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
