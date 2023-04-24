#!/usr/bin/env bash
set -euo pipefail

MCFGLPK=${MCFGLPK:-"mcfglpk"}
DATA_DIR=${DATA_DIR:-/data}
RESULTS_DIR=${RESULTS_DIR:-/results}

_run_problem() {
  _problem_file=$1
  _pivot_rule=$2

  _basename=$(basename -- "${_problem_file}")
  _filename=${_basename%.*}
  _extension="${_problem_file##*.}"
  _command="${MCFGLPK} ${_problem_file} \
    --${_extension} \
    --pivot ${_pivot_rule}  \
    --bits-only \
    --scale \
    --info-file ${RESULTS_DIR}/${_filename}.${_pivot_rule}.info \
    --obj-file ${RESULTS_DIR}/${_filename}.${_pivot_rule}.obj \
    --var-file ${RESULTS_DIR}/${_filename}.${_pivot_rule}.var"

  echo "${_command}"

  ${_command} 1>"${RESULTS_DIR}/${_filename}.${_pivot_rule}.out" 2>&1 \
    && touch "${RESULTS_DIR}/${_filename}.${_pivot_rule}.solved"

}

_collect_problems() {
  _data_dir=$1

  find "${_data_dir}" -type f -name "*.mps" -printf '%s\t%p\n' | sort -n | cut -f2-
  find "${_data_dir}" -type f -name "*.lp" -printf '%s\t%p\n' | sort -n | cut -f2-
}

if [ ! -d "${RESULTS_DIR}" ]; then
  mkdir -p "${RESULTS_DIR}"
fi

THREADS=${THREADS:-64}
while IFS= read -r _problem_file
do
  for _pivot_rule in "dantzig" "bland" "best" "random"; do
    (
      _run_problem "${_problem_file}" "${_pivot_rule}"
    ) &

    # allow to execute up to $N jobs in parallel
    if [[ $(jobs -r -p | wc -l) -ge ${THREADS} ]]; then
        # now there are ${THREADS} jobs already running, so wait here for any
        # job to be finished so there is a place to start next one.
        wait -n
    fi
  done
done <<< "$(_collect_problems "${DATA_DIR}")"

wait
