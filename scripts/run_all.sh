#!/usr/bin/env bash

echo "**************************************************"
echo "***** Start Building srsRAN test environment *****"
echo "*****             CipherCell                 *****"
echo "**************************************************"
echo ""


compile_sc_ric() {
    local build_type="$1"
    local os_type="$2"

    echo "Compile SRC RIC of build type: $build_type"

    if [[ "$BUILD_SRC_RIC" == "y" ]]; then
        echo "Patching sc-ric docker-compose.yml for macOS systems"
        
        cp "../docker/oran-sc-ric/macos/docker-compose.yml" "../oran-sc-ric/" || {
            echo "Failed to copy docker-compose.yml"
            exit 1
        }
    fi

    source ./compile_oran_sc_ric.sh "$build_type" "$os_type"
}

compile_core_network() {
    local build_type="$1"
    local os_type="$2"

    echo "Compile Core Network"
    source ./compile_core_network.sh "$build_type" "$os_type"
}

compile_gnb() {
    local build_type="$1"
    local os_type="$2"

    cp "../docker/gnb/macos/Dockerfile" "../srsRAN_Project/" || {
        echo "Failed to copy Dockerfile"
        exit 1
    }

    mkdir -p "../srsRAN_Project/configs"
    cp "../oran-sc-ric/e2-agents/srsRAN/gnb_zmq.yaml"  "../srsRAN_Project/configs" || {
        echo "Failed to copy gnb_zmq.yaml"
        exit 1
    }

    echo "Compile gnb"
    source ./compile_gnb.sh "$build_type" "$os_type"
}

compile_srsran_4g() {
    local build_type="$1"
    local os_type="$2"

    cp "../docker/srsran_4g/Dockerfile" "../srsRAN_4G/" || {
        echo "Failed to copy Dockerfile"
        exit 1
    }

    echo "Compile srsRAN_4G"
    python3 compile/compile_srsran_4g.py
}


if [[ "$OSTYPE" == "darwin"* ]]; then
    OS_NAME=$(sw_vers -productName)
    OS_VERSION=$(sw_vers -productVersion)
elif [[ -f /etc/os-release ]]; then
    OS_NAME=$(grep '^NAME=' /etc/os-release | cut -d= -f2 | tr -d '"')
    OS_VERSION=$(grep '^VERSION=' /etc/os-release | cut -d= -f2 | tr -d '"')
else
    OS_NAME=$(uname -s)
    OS_VERSION=$(uname -r)
fi

check_docker() {
    if command -v docker >/dev/null 2>&1; then
        echo "available"
    else
        echo "not available"
    fi
}

DOCKER_AVAIL=$(check_docker)

echo "Docker-based compilation is $DOCKER_AVAIL for your system: $OS_NAME $OS_VERSION."

echo "Choose your build type:"

echo -e "1: Docker\n2: Native"

read -p "Enter choice (1 or 2): " BUILD_CHOICE


case "$BUILD_CHOICE" in
    1)
        echo "You chose Docker build."

        if [[ "$DOCKER_AVAIL" == "not available" ]]; then
            echo "Docker is not available!"
            exit 1
        fi
        ;;
    2)
        echo "You chose Native build."
        ;;
    *)
        echo "Invalid choice. Please run the script again and select 1 or 2. -> Exit"
        exit 1
        ;;
esac

echo "Compile all components?"

read -p "Enter choice (y or n): " COMPILE_ALL

case "$COMPILE_ALL" in
    'y')
        echo "Start Compiling all components"

        compile_sc_ric $BUILD_CHOICE $OS_NAME
        compile_core_network $BUILD_CHOICE $OS_NAME
        compile_gnb $BUILD_CHOICE $OS_NAME

        ;;
    'n')
        echo "Compile sc ric?"
        read -p "Enter choice (y or n): " BUILD_SRC_RIC

        echo "Compile core network?"
        read -p "Enter choice (y or n): " BUILD_CORE_NETWORK

        echo "Compile gnb network?"
        read -p "Enter choice (y or n): " BUILD_GNB

        echo "Compile srs ran 4G?"
        read -p "Enter choice (y or n): " BUILD_SRS_RAN_4G

        if [[ "$BUILD_SRC_RIC" == "y" ]]; then
            compile_sc_ric $BUILD_CHOICE $OS_NAME
        fi

        if [[ "$BUILD_CORE_NETWORK" == "y" ]]; then
            compile_core_network $BUILD_CHOICE $OS_NAME
        fi

        if [[ "$BUILD_GNB" == "y" ]]; then
            compile_gnb $BUILD_CHOICE $OS_NAME
        fi

        if [[ "$BUILD_SRS_RAN_4G" == "y" ]]; then
            compile_srsran_4g $BUILD_CHOICE $OS_NAME
        fi

        ;;
    *)
        echo "Invalid choice. Please run the script again and select 1 or 2. -> Exit"
        exit 1
        ;;
esac