#!/bin/sh
# Launches Dagster with DAGSTER_HOME set to an absolute path, which Dagster requires and
# which can't be portably hardcoded in .env.example since it's a per-machine path.
# (Unlike Windows, PYTHONLEGACYWINDOWSSTDIO isn't needed here -- that variable, and the
# compute-log-capture problem it works around, are both Windows-specific.)
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
export DAGSTER_HOME="$SCRIPT_DIR/.dagster_home"

dagster dev
