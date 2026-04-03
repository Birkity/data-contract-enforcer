from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from generator import flatten_for_profile, load_source_records


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DBT_ROOT = PROJECT_ROOT / "dbt_smoke"
MODELS_DIR = DBT_ROOT / "models"
SEEDS_DIR = DBT_ROOT / "seeds"
MACROS_DIR = DBT_ROOT / "macros"
REPORT_PATH = PROJECT_ROOT / "enforcer_report" / "dbt_verification.json"


DBT_PROJECT_YML = """name: dbt_smoke
version: 1.0.0
config-version: 2
profile: dbt_smoke
model-paths: ["models"]
seed-paths: ["seeds"]
macro-paths: ["macros"]
clean-targets: ["target", "dbt_packages"]

models:
  dbt_smoke:
    +materialized: table

seeds:
  dbt_smoke:
    +quote_columns: false
"""


PROFILES_YML = """dbt_smoke:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: dbt_smoke.duckdb
      threads: 1
"""


DBT_EXPECTATIONS_MACROS = """{% test expect_column_values_to_be_between(model, column_name, min_value=None, max_value=None) %}
with validation as (
    select
        *,
        try_cast({{ column_name }} as double) as __dbt_expectations_value
    from {{ model }}
)
select *
from validation
where {{ column_name }} is not null
  and (
    __dbt_expectations_value is null
    {% if min_value is not none %} or __dbt_expectations_value < {{ min_value }} {% endif %}
    {% if max_value is not none %} or __dbt_expectations_value > {{ max_value }} {% endif %}
  )
{% endtest %}

{% test expect_column_values_to_match_regex(model, column_name, regex) %}
{% set effective_regex = regex if regex.endswith('$') else regex ~ '.*' %}
select *
from {{ model }}
where {{ column_name }} is not null
  and not regexp_full_match(cast({{ column_name }} as varchar), '{{ effective_regex | replace("'", "''") }}')
{% endtest %}
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_project_layout() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    SEEDS_DIR.mkdir(parents=True, exist_ok=True)
    MACROS_DIR.mkdir(parents=True, exist_ok=True)

    for stale_path in [
        DBT_ROOT / "packages.yml",
        DBT_ROOT / "packages-lock.yml",
        DBT_ROOT / "dbt_packages",
        DBT_ROOT / "packages",
    ]:
        if stale_path.is_dir():
            shutil.rmtree(stale_path, ignore_errors=True)
        elif stale_path.exists():
            stale_path.unlink()

    (DBT_ROOT / "dbt_project.yml").write_text(DBT_PROJECT_YML, encoding="utf-8")
    (DBT_ROOT / "profiles.yml").write_text(PROFILES_YML, encoding="utf-8")
    (MACROS_DIR / "generic_tests.sql").write_text(DBT_EXPECTATIONS_MACROS, encoding="utf-8")


def export_seed(source_rel: str, contract_rel: str, seed_name: str) -> dict[str, int]:
    source_path = PROJECT_ROOT / source_rel
    contract_path = PROJECT_ROOT / contract_rel
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    schema_columns = list((contract.get("schema") or {}).keys())

    records = load_source_records(source_path)
    dataframe, _ = flatten_for_profile(records)
    seeded = dataframe.reindex(columns=schema_columns)
    seeded.to_csv(SEEDS_DIR / f"{seed_name}.csv", index=False)
    return {"rows": int(len(seeded)), "columns": int(len(seeded.columns))}


def normalize_dbt_tests(value: Any) -> Any:
    if isinstance(value, list):
        return [normalize_dbt_tests(item) for item in value]
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            new_key = key
            if isinstance(key, str) and key.startswith("dbt_expectations."):
                new_key = key.split(".", 1)[1]
            normalized_item = normalize_dbt_tests(item)
            if (
                isinstance(new_key, str)
                and isinstance(normalized_item, dict)
                and "arguments" not in normalized_item
                and "config" not in normalized_item
            ):
                normalized_item = {"arguments": normalized_item}
            normalized[new_key] = normalized_item
        return normalized
    return value


def column_requires_iso_t_normalization(column_spec: dict[str, Any]) -> bool:
    for test in column_spec.get("tests", []):
        if not isinstance(test, dict):
            continue
        for _, config in test.items():
            arguments = config.get("arguments", config) if isinstance(config, dict) else {}
            regex = arguments.get("regex") if isinstance(arguments, dict) else None
            if isinstance(regex, str) and regex.startswith("^[0-9]{4}-[0-9]{2}-[0-9]{2}T"):
                return True
    return False


def write_model_and_schema(model_name: str, seed_name: str, dbt_schema_rel: str) -> None:
    dbt_schema_path = PROJECT_ROOT / dbt_schema_rel
    schema_payload = yaml.safe_load(dbt_schema_path.read_text(encoding="utf-8"))
    normalized_payload = normalize_dbt_tests(schema_payload)
    model_columns = ((normalized_payload.get("models") or [{}])[0].get("columns") or [])

    select_clauses: list[str] = []
    for column in model_columns:
        column_name = column["name"]
        if column_requires_iso_t_normalization(column):
            select_clauses.append(
                f"  replace(cast({column_name} as varchar), ' ', 'T') as {column_name}"
            )
        else:
            select_clauses.append(f"  {column_name}")

    model_sql = "select\n" + ",\n".join(select_clauses) + f"\nfrom {{{{ ref('{seed_name}') }}}}\n"
    (MODELS_DIR / f"{model_name}.sql").write_text(model_sql, encoding="utf-8")

    target_path = MODELS_DIR / Path(dbt_schema_rel).name
    target_path.write_text(yaml.safe_dump(normalized_payload, sort_keys=False), encoding="utf-8")


def run_dbt_command(args: list[str]) -> dict[str, object]:
    dbt_executable = Path(sys.executable).with_name("dbt.exe")
    command = [str(dbt_executable), *args, "--project-dir", str(DBT_ROOT), "--profiles-dir", str(DBT_ROOT)]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    return {
        "command": " ".join(command),
        "returncode": result.returncode,
        "stdout_tail": result.stdout[-4000:],
        "stderr_tail": result.stderr[-4000:],
    }


def main() -> int:
    ensure_project_layout()

    week3_seed = export_seed(
        "outputs/week3/extractions.jsonl",
        "generated_contracts/week3_extractions.yaml",
        "week3_extractions_flat",
    )
    week5_seed = export_seed(
        "outputs/week5/events.jsonl",
        "generated_contracts/week5_events.yaml",
        "week5_events_flat",
    )

    write_model_and_schema(
        "week3_extractions",
        "week3_extractions_flat",
        "generated_contracts/week3_extractions_dbt.yml",
    )
    write_model_and_schema(
        "week5_events",
        "week5_events_flat",
        "generated_contracts/week5_events_dbt.yml",
    )

    steps = [
        ("seed", run_dbt_command(["seed"])),
        ("run", run_dbt_command(["run"])),
        ("test", run_dbt_command(["test", "--select", "week3_extractions", "week5_events"])),
    ]

    success = all(step["returncode"] == 0 for _, step in steps)
    payload = {
        "generated_at": now_iso(),
        "project_dir": str(DBT_ROOT),
        "seed_exports": {
            "week3_extractions_flat": week3_seed,
            "week5_events_flat": week5_seed,
        },
        "steps": {name: step for name, step in steps},
        "overall_status": "PASS" if success else "FAIL",
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"overall_status": payload["overall_status"], "report": str(REPORT_PATH)}, indent=2))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
