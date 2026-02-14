#!/bin/bash

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
echo -e "*****       Starting Traffic Generation       ****"
echo -e "**************************************************\n"

check_python_version

set -e

if [ ! -d ".trafficker_venv" ]; then
  echo "Create new virtual environment"
  python3 -m venv .trafficker_venv
fi

source .trafficker_venv/bin/activate
echo "Install python dependencies"
pip3 install --upgrade pip
pip3 install -r requirements.txt

python3 src/trafficker.py "$@"