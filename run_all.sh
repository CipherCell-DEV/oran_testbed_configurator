#!/bin/sh

set -e

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate

pip3 install --upgrade pip
pip3 install -r scripts/src/requirements.txt

python3 scripts/src/main.py --config_file=scripts/config/sample_configuration.yml