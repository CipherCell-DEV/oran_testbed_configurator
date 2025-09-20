#!/usr/bin/env bash

SESSION="srsRAN_Demo"

tmux has-session -t $SESSION 2>/dev/null
if [ $? -eq 0 ]; then
    echo "Session $SESSION already exists. Attaching..."
    tmux attach -t $SESSION
    exit 0
fi

tmux new-session -d -s $SESSION

tmux split-window -h
tmux select-pane -t 0
tmux split-window -v
tmux select-pane -t 2
tmux split-window -v
tmux select-pane -t 4
tmux split-window -h
tmux select-pane -t 5
tmux split-window -h

tmux select-layout tiled

tmux send-keys -t $SESSION:0.0 "python3 run/run_oran_sc_ric.py --log ../scripts/logs/run/run_oran_sc_ric.log" C-m
tmux send-keys -t $SESSION:0.1 "python3 run/run_core_network.py --log ../../scripts/logs/run/core_network.log" C-m
tmux send-keys -t $SESSION:0.2 "python3 run/run_gnb.py --log ../scripts/logs/run/gnb.log" C-m
tmux send-keys -t $SESSION:0.3 "ls" C-m
tmux send-keys -t $SESSION:0.4 "top" C-m
tmux send-keys -t $SESSION:0.5 "ls" C-m

tmux attach-session -t $SESSION