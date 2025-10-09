#!/bin/bash

export MINIMUM_PYTHON_VERSION_MAJOR=3
export MINIMUM_PYTHON_VERSION_MINOR=10
export MINIMUM_PYTHON_VERSION_PATCH=0

check_python_version() {
if ! hash python3; then
    echo "python is not installed"
    exit 1
fi

python_version=$(python3 -V 2>&1)

ver_major=$(echo "$python_version" | sed 's/.* \([0-9]\).[0-9]*.[0-9]*/\1/')
ver_minor=$(echo "$python_version" | sed 's/.* [0-9].\([0-9]*\).[0-9]*/\1/')
ver_patch=$(echo "$python_version" | sed 's/.* [0-9].[0-9]*.\([0-9]*\)/\1/')


if [ "$ver_major" -lt "$MINIMUM_PYTHON_VERSION_MAJOR" ] || \
   { [ "$ver_major" -eq "$MINIMUM_PYTHON_VERSION_MAJOR" ] && [ "$ver_minor" -lt "$MINIMUM_PYTHON_VERSION_MINOR" ]; } || \
   { [ "$ver_major" -eq "$MINIMUM_PYTHON_VERSION_MAJOR" ] && [ "$ver_minor" -eq "$MINIMUM_PYTHON_VERSION_MINOR" ] && [ "$ver_patch" -lt "$MINIMUM_PYTHON_VERSION_PATCH" ]; }; then
    echo "This script requires at least python ${MINIMUM_PYTHON_VERSION_MAJOR}.${MINIMUM_PYTHON_VERSION_MINOR}.${MINIMUM_PYTHON_VERSION_PATCH} current version ${ver_major}.${ver_minor}.${ver_patch}"
    exit 1
else
  echo "Detected matching python version ${ver_major}.${ver_minor}.${ver_patch}"

fi
}

echo -e "\n**************************************************"
echo -e "*****    Starting CipherCell Configurator     ****"
echo -e "**************************************************\n"

check_python_version

set -e

if [ ! -d ".venv" ]; then
  echo "Create new virtual environment"
  python3 -m venv .venv
fi

source .venv/bin/activate

echo "Install python dependencies"
pip3 install --upgrade pip --no-index
pip3 install -r scripts/src/requirements.txt

python3 scripts/src/main.py --supress_welcome_header --config_file=scripts/config/sample_configuration.yml