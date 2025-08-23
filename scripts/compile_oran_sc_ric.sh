#!/usr/bin/env bash
 (
  cd ../oran-sc-ric/ || { echo "Checkout ORAN SC first -> Run `git submodule update --init --recursive`"; exit 1; }
  docker compose build
)
