#!/usr/bin/env bash
 (
  cd ../srsRAN_Project/docker || { echo "Checkout srsRAN_Project first -> Run `git submodule update --init --recursive`"; exit 1; }
  docker compose build 5gc
)

