from dagster import Definitions

from orchestration.assets import landing_zone, transformed_zone

defs = Definitions(assets=[landing_zone, transformed_zone])
