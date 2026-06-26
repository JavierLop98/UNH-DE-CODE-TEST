"""
03_parse_index_files.py
-----------------------
Parses downloaded UHC index JSON files into normalized analytical tables.

Output tables (Parquet):
  - index_files.parquet       — one row per parsed index file
  - reporting_entities.parquet — reporting entity metadata
  - plans.parquet              — plan-level detail
  - referenced_files.parquet   — in-network and allowed-amount file references
  - parse_log.csv              — success/failure status per file
"""
import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.io_utils import ensure_dir, safe_json_load


def as_list(value):
    """Normalize None / single dict / list to a list."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def parse_index_json(
    path: Path, index_file_id: int, file_name: str
) -> tuple[list, list, list, list]:
    """Parse a single index JSON file into four lists of row dicts."""
    payload = safe_json_load(path)
    parsed_at = datetime.now(timezone.utc).isoformat()

    # --- Index-level row ---
    index_rows = [{
        "index_file_id": index_file_id,
        "file_name": file_name,
        "local_path": str(path),
        "reporting_entity_name": payload.get("reporting_entity_name"),
        "reporting_entity_type": payload.get("reporting_entity_type"),
        "last_updated_on": payload.get("last_updated_on"),
        "version": payload.get("version"),
        "parsed_at": parsed_at,
    }]

    # --- Reporting entity row ---
    entity_rows = [{
        "index_file_id": index_file_id,
        "reporting_entity_name": payload.get("reporting_entity_name"),
        "reporting_entity_type": payload.get("reporting_entity_type"),
        "last_updated_on": payload.get("last_updated_on"),
        "version": payload.get("version"),
    }]

    # --- Plans and referenced files ---
    plan_rows = []
    ref_rows = []
    reporting_structure = as_list(payload.get("reporting_structure"))

    for struct_idx, struct in enumerate(reporting_structure):
        plans = as_list(struct.get("reporting_plans"))
        in_network_files = as_list(struct.get("in_network_files"))
        allowed_amount_files = as_list(struct.get("allowed_amount_file"))

        for plan_idx, plan in enumerate(plans):
            plan_key = f"{index_file_id}_{struct_idx}_{plan_idx}"
            plan_rows.append({
                "plan_key": plan_key,
                "index_file_id": index_file_id,
                "plan_name": plan.get("plan_name"),
                "plan_id": plan.get("plan_id"),
                "plan_id_type": plan.get("plan_id_type"),
                "plan_market_type": plan.get("plan_market_type"),
            })

            for file_type, files in [
                ("in_network", in_network_files),
                ("allowed_amount", allowed_amount_files),
            ]:
                for file_idx, f in enumerate(files):
                    if isinstance(f, dict):
                        ref_rows.append({
                            "referenced_file_key": f"{plan_key}_{file_type}_{file_idx}",
                            "plan_key": plan_key,
                            "index_file_id": index_file_id,
                            "file_type": file_type,
                            "description": f.get("description"),
                            "location_url": f.get("location"),
                        })

    return index_rows, entity_rows, plan_rows, ref_rows


def main():
    parser = argparse.ArgumentParser(
        description="Parse downloaded UHC index JSON files into Parquet tables."
    )
    parser.add_argument("--download-log", default="data/processed/download_log.csv")
    parser.add_argument("--output-dir", default="data/processed")
    args = parser.parse_args()

    ensure_dir(args.output_dir)
    log = pd.read_csv(args.download_log)
    successful = log[log["status"].isin(["downloaded", "already_exists"])]
    print(f"Parsing {len(successful):,} successfully downloaded files ...")

    all_indexes, all_entities, all_plans, all_refs, parse_logs = [], [], [], [], []

    for index_file_id, (_, row) in enumerate(successful.iterrows(), start=1):
        path = Path(row["local_path"])
        try:
            idx, ent, plans, refs = parse_index_json(
                path, index_file_id, row["file_name"]
            )
            all_indexes.extend(idx)
            all_entities.extend(ent)
            all_plans.extend(plans)
            all_refs.extend(refs)
            parse_logs.append({
                "file_name": row["file_name"],
                "parse_status": "parsed",
                "error_message": None,
            })
        except Exception as exc:
            parse_logs.append({
                "file_name": row["file_name"],
                "parse_status": "failed",
                "error_message": str(exc),
            })

    # Write output Parquet / CSV
    pd.DataFrame(all_indexes).to_parquet(
        f"{args.output_dir}/index_files.parquet", index=False
    )
    pd.DataFrame(all_entities).to_parquet(
        f"{args.output_dir}/reporting_entities.parquet", index=False
    )
    pd.DataFrame(all_plans).to_parquet(
        f"{args.output_dir}/plans.parquet", index=False
    )
    pd.DataFrame(all_refs).to_parquet(
        f"{args.output_dir}/referenced_files.parquet", index=False
    )
    pd.DataFrame(parse_logs).to_csv(
        f"{args.output_dir}/parse_log.csv", index=False
    )

    print(f"\nParsing complete:")
    print(f"  Index files:      {len(all_indexes):,}")
    print(f"  Entities:         {len(all_entities):,}")
    print(f"  Plans:            {len(all_plans):,}")
    print(f"  Referenced files: {len(all_refs):,}")

    failed = [p for p in parse_logs if p["parse_status"] == "failed"]
    if failed:
        print(f"  Parse failures:   {len(failed):,}")


if __name__ == "__main__":
    main()
