"""
Apply saved column mappings to ALL CSV files in a dataset.

Usage:
  python main.py HUGADB
  python main.py YARETA --dry-run
  python main.py HUGADB --index-col 0
"""

import os
import sys
import json
import argparse
from pathlib import Path

import pandas as pd
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    from sync_columns.config import (
        BLUE, GREEN, YELLOW, RED, RESET,
        RAW_DIR, SYNCED_DIR, MAPPING_DIR, DATASET_ROOTS,
    )
except ImportError:
    from config import (
        BLUE, GREEN, YELLOW, RED, RESET,
        RAW_DIR, SYNCED_DIR, MAPPING_DIR, DATASET_ROOTS,
    )


def get_dataset_root(dataset_name):
    """Return the root directory for the dataset (where to find raw CSVs)."""
    key = dataset_name.upper()
    if key in DATASET_ROOTS:
        return DATASET_ROOTS[key]
    return os.path.join(RAW_DIR, dataset_name)


def find_csv_files(root_dir):
    """Recursively find all CSV files under root_dir."""
    csv_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for f in filenames:
            if f.lower().endswith(".csv"):
                csv_files.append(os.path.join(dirpath, f))
    return sorted(csv_files)


def apply_mapping_to_csv(
    input_path,
    mapping,
    output_path,
    index_col=None,
):
    """Read CSV, rename columns using mapping, save to output_path."""
    read_kw = {} if index_col is None else {"index_col": index_col}
    df = pd.read_csv(input_path, **read_kw)
    # Only rename columns that exist in the dataframe and in the mapping
    rename_map = {c: mapping[c] for c in df.columns if c in mapping}
    df_renamed = df.rename(columns=rename_map)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    df_renamed.to_csv(output_path, index=False)
    return len(rename_map)


def convert_dataset(
    dataset_name,
    index_col=None,
    dry_run=False,
):
    """Convert columns of ALL CSV files in the dataset using saved mapping."""
    dataset_key = dataset_name.upper()
    mapping_path = os.path.join(MAPPING_DIR, f"{dataset_key}_mapping.json")

    if not os.path.isfile(mapping_path):
        print(f"{RED}[ERROR] Mapping not found: {mapping_path}{RESET}")
        print(f"  Run get_mapping.py on a sample file first, approve the mapping, then run this.")
        sys.exit(1)

    with open(mapping_path) as f:
        mapping = json.load(f)

    root = get_dataset_root(dataset_name)
    if not os.path.isdir(root):
        print(f"{RED}[ERROR] Dataset root not found: {root}{RESET}")
        sys.exit(1)

    csv_files = find_csv_files(root)
    if not csv_files:
        print(f"{YELLOW}[WARN] No CSV files found under {root}{RESET}")
        return

    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}CONVERTING: {dataset_key} ({len(csv_files)} files){RESET}")
    print(f"  Mapping: {mapping_path}")
    print(f"  Root: {root}")
    print(f"  Output: {SYNCED_DIR}")
    if dry_run:
        print(f"  {YELLOW}[DRY RUN] No files will be written{RESET}")
    print()

    n_original = len(csv_files)
    n_converted = 0
    total_mapped = 0
    for inp in tqdm(csv_files, desc=f"{BLUE}Converting{RESET}", colour="blue"):
        rel = os.path.relpath(inp, root)
        out = os.path.join(SYNCED_DIR, dataset_key, os.path.dirname(rel), Path(inp).stem + ".csv")

        if dry_run:
            tqdm.write(f"  {rel} → {out}")
            n_converted += 1
            continue

        try:
            n = apply_mapping_to_csv(inp, mapping, out, index_col=index_col)
            total_mapped += n
            n_converted += 1
        except Exception as e:
            tqdm.write(f"{RED}[FAIL] {inp}: {e}{RESET}")

    print(f"\n{BLUE}SUMMARY{RESET}: original ({n_original}) files, converted ({n_converted}) files")


def main():
    parser = argparse.ArgumentParser(
        description="Apply saved column mapping to ALL CSV files in a dataset.",
    )
    parser.add_argument(
        "dataset",
        type=str,
        help="Dataset name (e.g., HUGADB, YARETA)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files that would be converted without writing",
    )
    parser.add_argument(
        "--index-col",
        type=int,
        default=None,
        metavar="N",
        help="Use column N (0-based) as row index when reading CSV",
    )
    args = parser.parse_args()

    convert_dataset(
        args.dataset,
        index_col=args.index_col,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
