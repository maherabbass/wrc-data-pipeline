# Launches Dagster with settings that can't live in .env:
# - PYTHONLEGACYWINDOWSSTDIO must be set before Python starts, so it can't be loaded from .env.
# - DAGSTER_HOME must be an absolute path, which .env.example can't portably hardcode.
$env:DAGSTER_HOME = Join-Path $PSScriptRoot ".dagster_home"
$env:PYTHONLEGACYWINDOWSSTDIO = "1"

dagster dev
