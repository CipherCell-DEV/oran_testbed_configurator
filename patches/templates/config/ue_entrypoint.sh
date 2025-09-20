#!/bin/bash
set -e

if ! ip netns list | grep -qw "ue1"; then
    sudo ip netns add ue1
fi

exec ./build/srsue/src/srsue "configs/$1_zmq.conf"
