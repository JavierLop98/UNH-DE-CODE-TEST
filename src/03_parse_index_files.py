import argparse
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

from utils.io_utils import ensure_dir, safe_json_load


def as_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def parse_index_json(path: Path, index_file_id: int, file_name: str) -> tuple[list, list, list, list]:
    payload = safe_json_load(path)
    parsed_at = datetime.now(timezone.utc).isoformat()

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

    entity_rows = [{
        "index_file_id": index_file_id,
        "reporting_entity_name": payload.get("reporting_entity_name"),
        "reporting_entity_type": payload.get("reporting_entity_type"),
        "last_updated_on": payload.get("last_updated_on"),
        "version": payload.get("version"),
    }]

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

            for file_type, files in [("in_network", in_network_files), ("allowed_amount", allowed_amount_files)]:
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--download-log", default="data/processed/download_log.csv")
    parser.add_argument("--output-dir", default="data/processed")
    args = parser.parse_args()

    ensure_dir(args.output_dir)
    log = pd.read_csv(args.download_log)
    successful = log[log["status"].isin(["downloaded", "already_exists"])]

    all_indexes, all_entities, all_plans, all_refs, parse_logs = [], [], [], [], []

    for index_file_id, (_, row) in enumerate(successful.iterrows(), start=1):
        path = Path(row["local_path"])
        try:
            idx, ent, plans, refs = parse_index_json(path, index_file_id, row["file_name"])
            all_indexes.extend(idx)
            all_entities.extend(ent)
            all_plans.extend(plans)
            all_refs.extend(refs)
            parse_logs.append({"file_name": row["file_name"], "parse_status": "parsed", "error_message": None})
        except Exception as exc:
            parse_logs.append({"file_name": row["file_name"], "parse_status": "failed", "error_message": str(exc)})

    pd.DataFrame(all_indexes).to_parquet(f"{args.output_dir}/index_files.parquet", index=False)
    pd.DataFrame(all_entities).to_parquet(f"{args.output_dir}/reporting_entities.parquet", index=False)
    pd.DataFrame(all_plans).to_parquet(f"{args.output_dir}/plans.parquet", index=False)
    pd.DataFrame(all_refs).to_parquet(f"{args.output_dir}/referenced_files.parquet", index=False)
    pd.DataFrame(parse_logs).to_csv(f"{args.output_dir}/parse_log.csv", index=False)

    print("Parsing complete")
    print(f"Index files: {len(all_indexes)} | Plans: {len(all_plans)} | Referenced files: {len(all_refs)}")


if __name__ == "__main__":
    main()
