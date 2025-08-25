#!/usr/bin/env python3
import os
import subprocess
import sys
import argparse

parser = argparse.ArgumentParser(description="Build srsRAN_4G docker compose")
parser.add_argument(
    "--log",
    help="Path to log file. If provided, output will be saved there.",
    type=str,
)
args = parser.parse_args()

target_dir = os.path.join("..", "srsRAN_4G")

if not os.path.isdir(target_dir):
    print("Checkout srsRAN_4G -> Run `git submodule update --init --recursive`")
    sys.exit(1)

os.chdir(target_dir)

cmd = ["docker", "compose", "build"]

try:
    if args.log:
        with open(args.log, "w") as log_file:
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
            # Stream output to both console and log file
            for line in process.stdout:
                print(line, end="")
                log_file.write(line)
            process.wait()
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, cmd)
        print(f"\nBuild output saved to {args.log}")
    else:
        subprocess.run(cmd, check=True)
        sys.exit(0)
except subprocess.CalledProcessError as e:
    print(f"Error during docker compose build: {e}")
    sys.exit(1)
