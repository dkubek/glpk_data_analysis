#!/usr/bin/env bash
set -euo pipefail

mkdir -p "$SCRATCHDIR/tmp"
export SINGULARITY_TMPDIR=$SCRATCHDIR/cache

mkdir -p "$SCRATCHDIR/cache"
export SINGULARITY_CACHEDIR=$SCRATCHDIR/cache

cd "$SCRATCHDIR"
