#!/usr/bin/env bash
set -euo pipefail

_mcfglpk="../mcfglpk/cmake-build-debug/mcfglpk"

get_info() {
  local _output=

  for _problem in "$@"; do
    _extension="${_problem##*.}"
    _output=$(
      ${_mcfglpk} --info --"${_extension}" --pivot best "${_problem}" | 
        tail -3 |
        sed "s/.*: \(.*\)/\1/" |
        tr $'\n' $'\t'
    )

    read -r _nrows _ncols _nonzero <<<"${_output}"

    printf "%d\t%d\t%d\t%s\n" "${_nrows}" "${_ncols}" "${_nonzero}" "${_problem}"
  done
}

run_problem() {
  _line=$1

  read -r _nrows _ncols _nonzeros _problem <<< "${_line}"
  _extension="${_problem##*.}"
  _command="${_mcfglpk} --${_extension} --pivot best ${_problem}"
  _time_output=$({ command time -f "%U %M" -- ${_command} 1>/dev/null ;} 2>&1)

  read -r _runtime _memory <<< "${_time_output}"

  printf "%d\t%d\t%d\t%s\t%s\t%d\n" \
    "${_nonzeros}" "${_nrows}" "${_ncols}" "${_problem}" "${_runtime}" "${_memory}"
}

N=8
while IFS= read -r _line
do
  (
    run_problem "${_line}"
  ) &

  # allow to execute up to $N jobs in parallel
  if [[ $(jobs -r -p | wc -l) -ge $N ]]; then
      # now there are $N jobs already running, so wait here for any job
      # to be finished so there is a place to start next one.
      wait -n
  fi
done <<< "$(get_info "$@" | sort -k 1 -n)"

wait
