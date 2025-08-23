#!/usr/bin/env bash
 (
  cd ../srsRAN_4G/ || { echo "Checkout srsRAN_4G -> Run `git submodule update --init --recursive`"; exit 1; }
  docker build --progress=plain -t srsran-4g .
)
