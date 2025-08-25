#!/usr/bin/env python3
import os
import subprocess
import sys
import argparse

# ANSI escape codes for colors
RED = "\033[31m"
GREEN = "\033[32m"
RESET = "\033[0m"

parser = argparse.ArgumentParser(description="Build oran-sc-ric docker compose")
parser.add_argument(
    "--log",
    help="Path to log file. If provided, output will be saved there.",
    type=str,
)
args = parser.parse_args()

target_dir = os.path.join("..", "oran-sc-ric")

if not os.path.isdir(target_dir):
    print(f"{RED}Checkout oran-sc-ric -> Run `git submodule update --init --recursive`{RESET}")
    sys.exit(1)

os.chdir(target_dir)

cmd = ["docker", "compose", "build"]

try:
    if args.log:
        with open(args.log, "w") as log_file:
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
            for line in process.stdout:
                # Detect error keywords and print in red
                if "ERROR" in line or "failed" in line.lower():
                    print(f"{RED}{line}{RESET}", end="")
                else:
                    print(line, end="")
                log_file.write(line)
            process.wait()
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, cmd)
        print(f"\n{GREEN}Build output saved to {args.log}{RESET}")
    else:
        result = subprocess.run(cmd, text=True, capture_output=True)
        if result.returncode != 0:
            print(f"{RED}Docker compose build failed with exit code {result.returncode}{RESET}")
            print(f"{RED}{result.stdout}{RESET}")
            sys.exit(result.returncode)
        print(f"{GREEN}Docker compose build succeeded!{RESET}")
except subprocess.CalledProcessError as e:
    print(f"{RED}Error during docker compose build: {e}{RESET}")
    sys.exit(e.returncode if hasattr(e, 'returncode') else 1)
