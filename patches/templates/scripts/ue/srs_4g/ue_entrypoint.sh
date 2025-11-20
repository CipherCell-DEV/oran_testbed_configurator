#!/bin/bash
set -e

if ! ip netns list | grep -qw $1; then
    sudo ip netns add $1
fi

exec ./build_docker/srsue/src/srsue "configs/$1_zmq.conf"
