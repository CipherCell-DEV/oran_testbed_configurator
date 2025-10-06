#!/bin/bash

# ===================================== Configuration =====================================================

# reference session by name
SESSION_NAME="oran_deploy_manager"

# max. number of panes per window created by this script
# for our own sanity, cap at 10
MAX_NUM_PANES_PER_WINDOW=4

# relative path to command config
COMMAND_CONFIG_PATH="scripts/config/"

# The user may specify the used terminal here (e.g. gnome-terminal, konsole, xterm, ...)
# If kept empty this script will try to look for the terminal itself.
TERMINAL_NAME=""

# We want to open the initial tmux 
# This script assumes the following syntax structure:
# [terminal name] [optional: some flags/indicators] [command to be executed in ]

# ===================================== Global Variables =================================================

# session windows are identified by numbers (starting from 0)
num_windows=0
# window paned are referenced by numbers (staring from 0)
# ! Caution: The reference number of a specific pane changes if e.g. a previous pane is split.
# ! As such the creation and splitting of panes must be well managed to not
# ! lose accurate pane references. 
num_panes=0

# Example - Reference to a specific pane -> session_name:window_number:pane_number
#           demo:0.0: First pane of first window of session "demo"
#           demo:1.0: First pane of second window of session "demo"

# We need to find out which terminal is installed.
used_terminal=""

# ===================================== Function Definitions =============================================

# Trying to unintentional avoid bugs
sanity_check() {
    sane=true
    if [ -z $used_terminal ]; then echo "Either "
    if [ $MAX_NUM_PANES_PER_WINDOW -gt 10 ]; then sane=false fi
    if [ $MAX_NUM_PANES_PER_WINDOW -lt 1 ]; then sane=false fi 
    if [ -n $($SESSION_NAME | grep "(attached)") ]; then sane=false fi
    if [ "$sane" = false ];
        echo "MAX_NUM_PANES_PER_WINDOW must be between 1 and 10 (inclusive). The session name must not have '(attached)' as a substring."
        exit 1
    fi
}

# create a new session in the background. Automatically creates an unattached window with one pane
close_and_recreate_session() {
	tmux has-session -t ${SESSION_NAME}
	found=$?
	if [ $found -eq 0 ];
	then
		# session already exists -> we probably do not want multiple instances of our containers, so we destroy existing stuff
		echo -e "The tmux session ${SESSION_NAME} already exists. Do you want to \e[1mkill the existing session\e[0m and close all its associated windows?"
		select reply in "yes" "no"; do
			case "$reply" in
				yes) echo "Killing session ${SESSION_NAME}..."; tmux kill-session -t ${SESSION_NAME}; break;;
				no) echo "Exiting..."; exit; break;;
				* | "") echo "Please enter 1 or 2!"; 
			esac
		done
		
	else
		# session does not exist 
		echo "Creating detached tmux session ${SESSION_NAME}"
		tmux new-session -d -s ${SESSION_NAME}
		# account for initial window and pane (are hidden at first)
		num_windows=1
	fi
}

# Splits the sceen of the current window and starts the entered command.
# Creates new windows if necessary
# Param $1: readible command name. Must be unique and must not contain a whitespace
# Params $2 - Rest: command string to be executed (with parameters)
create_pane_for_command() {
    has_window=$(tmux ls | grep -w "${SESSION_NAME}: ${num_windows}")
	if [ -n $has_window ];
	then
	    echo "Launching tmux pane $1: "
	    if [ $num_panes -eq 0 ]; 
	    then
	        # If initial window is not attached, attach
	        is_attached=$("${has_window}" | grep "(attached)")
	        if [ -z $is_attached ]
	        # First screen does not need to be split
	    else
	    fi        
	    # Comupte next pane reference like this: num_panes/num_windows = x * num_windows + y 
	    # Next pane = session_name:x:y
	then
	else
	    echo "No active session ${SESSION_NAME}. Exiting ..."
	    exit;
	fi  
}

# ===================================== Program Script =============================================

sanity_check
close_and_recreate_session
create_pane_for_command "first" echo "1"
create_pane_for_command "second" echo "2"
create_pane_for_command "third" echo "3"
create_pane_for_command "fourth" echo "4"
create_pane_for_command "fith" echo "5"
create_pane_for_command "sixth" echo "6"
create_pane_for_command "seventh" echo "7"
create_pane_for_command "eighth" echo "8"
create_pane_for_command "ninth" echo "9"
create_pane_for_command "tenth" echo "10"
create_pane_for_command "eleventh" echo "10"

