#!/bin/bash
set -e

if ! ip netns list | grep -qw "ue1"; then
    sudo ip netns add ue1
fi

# TODO: Only create one namespace per UE and not the ue1 namespace additionally. Currently, the ue1 namespace is needed
# in every container in order to send traffic.
if ! ip netns list | grep -qw "ue2"; then
    sudo ip netns add ue2
fi

if ! ip netns list | grep -qw "ue3"; then
    sudo ip netns add ue3
fi

exec ./build_docker/srsue/src/srsue "configs/$1_zmq.conf"
