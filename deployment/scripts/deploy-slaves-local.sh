#!/bin/bash

source scripts/global-vars.sh

# Kill all children of this script when exiting
trap "$trap_exit_command" EXIT

# Get root directory of the deployment data
exp_data_dir=$1
shift

# For each tuple given on the command line
while [ -n "$1" ]; do

  # Read arguments
  trigger=$1
  n=$2
  tag=$3
  machine_template=$4
  shift 4

  echo "Deploy params: $trigger, $n, $tag, $machine_template"

  # Wait for trigger. We interpret the master status (a number)
  # reaching (or exceeding) the value of $trigger as a trigger.
  master_status=$(cat $exp_data_dir/$local_master_status_file)
  # bash >= 5.2 compat: `$((10#-1))` is an "invalid integer constant" there, and the
  # resulting error aborts the whole enclosing `while` construct -- no slaves are ever
  # launched and the deployment hangs forever waiting for them. Strip the sign before
  # applying the 10# base prefix, and guard the status with a regex before converting it,
  # so that zero-padded values (0008, 0018, ...) are still read as decimal and not octal.
  if [[ "$trigger" =~ ^-?[0-9]+$ ]]; then
    trigger_dec=$((10#${trigger#-}))
    [[ "$trigger" == -* ]] && trigger_dec=$((0 - trigger_dec))
  else
    trigger_dec=-1
  fi
  while [[ "$trigger_dec" -ge 0 ]] && { [[ ! "$master_status" =~ ^[0-9]+$ ]] || [[ "$((10#$master_status))" -lt "$trigger_dec" ]]; }; do
    sleep $machine_status_poll_period
    master_status=$(cat $exp_data_dir/$local_master_status_file)
  done

  # Deploy slave nodes.
  echo "Changing directory to $exp_data_dir"
  initial_directory=$(pwd)
  cd $exp_data_dir || exit 1
  echo "Starting local slaves: $n $tag"
  for i in $(seq 1 $n); do
    echo discoveryslave $tag $local_public_ip:$master_port $local_public_ip $local_private_ip
    discoveryslave $tag $local_public_ip:$master_port $local_public_ip $local_private_ip > slave-$i.log 2>&1 &
  done
  echo "Changing directory back to $initial_directory"
  cd $initial_directory || exit 1

done
wait

echo "Local slave deployment finished."
