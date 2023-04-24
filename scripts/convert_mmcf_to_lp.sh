#!/usr/bin/env bash
set -euo pipefail

SCRIPT=${SCRIPT:-"construct_mmcf_problem.py"}
DATA_DIR=${DATA_DIR:-"/data"}

_collect_problems() {
  local _data_dir=$1

  find "${DATA_DIR}" -type f -name "*.json" -printf '%s\t%p\n' | sort -n | cut -f2-
}

_convert() {
  local _problem_file=$1
  local _filename=

  _filename=${_problem_file%.*}
  _out_file="${_filename}.lp"
  if [ -f "${_out_file}" ]; then
    echo "SKIPPING ${_problem_file}"
    return
  fi

  _cmd="python3 ${SCRIPT} ${_problem_file} -o ${_out_file}"

  echo "${_cmd}"
  ${_cmd}
}

THREADS=${THREADS:-8}
while IFS= read -r _problem_file
do
  (
    _convert "${_problem_file}"
  ) &

  # allow to execute up to $N jobs in parallel
  if [[ $(jobs -r -p | wc -l) -ge $THREADS ]]; then
      # now there are $N jobs already running, so wait here for any job
      # to be finished so there is a place to start next one.
      wait -n
  fi
done <<< "$(_collect_problems ${DATA_DIR})"

wait
