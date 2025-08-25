#!/usr/bin/env bash
 (
  cd ../srsRAN_Project/ || { echo "Checkout srsRAN Project first -> Run `git submodule update --init --recursive`"; exit 1; }
  docker build --progress=plain -t srsran-gnb .
)
