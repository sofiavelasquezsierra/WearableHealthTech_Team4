#!/usr/bin/env python3
"""
One-shot interactive dataset restructurer.

Walks a source directory of CSV datasets and renames/restructures each file
into a standardized format:  p-{pid}_s-{session}_a-{activity}.csv

For each dataset folder, the script:
  1. Shows you sample paths and CSV column headers
  2. Asks where pid, session, and activity each come from — you pick from:
       - A directory name in the file's folder path
       - The filename/stem (whole, split by delimiter, or regex)
       - A column value inside the CSV itself
       - A fixed literal value (same for all files)
  3. Optionally applies transforms (strip prefix/suffix, regex capture, zero-pad)
  4. Restructures and writes output immediately (or previews with --dry-run)

Always run with --dry-run first to verify filenames before writing.

Usage:
  python restructure.py                          # all datasets, interactive
  python restructure.py --dataset HUGADB         # one dataset only
  python restructure.py --dataset HUGADB --dry-run
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import shutil
import sys
from pathlib import Path

DEFAULT_BASE = "/Users/sofiavelasquez/Library/CloudStorage/Box-Box/WHT Datasets"
DEFAULT_SRC = os.path.join(DEFAULT_BASE, "04_freq_unit_synced")
DEFAULT_DST = os.path.join(DEFAULT_BASE, "05_restruc")


# ── Helpers ─────────────────────────────────────────────────────────────

def collect_csvs(root: str) -> list[str]:
    out = []
    for dp, _, fnames in os.walk(root):
        for f in sorted(fnames):
            if f.lower().endswith(".csv"):
                out.append(os.path.join(dp, f))
    return sorted(out)


def peek_headers(fpath: str) -> list[str]:
    try:
        with open(fpath, "r", newline="", errors="replace") as f:
            return next(csv.reader(f), [])
    except Exception:
        return []


def prompt_choice(msg: str, options: list[str]) -> int:
    for i, o in enumerate(options, 1):
        print(f"    [{i}] {o}")
    while True:
        v = input(msg).strip()
        try:
            n = int(v)
            if 1 <= n <= len(options):
                return n - 1
        except ValueError:
            pass
        print(f"    Enter 1-{len(options)}")


def prompt_int(msg: str, lo: int, hi: int) -> int:
    while True:
        v = input(msg).strip()
        try:
            n = int(v)
            if lo <= n <= hi:
                return n
        except ValueError:
            pass
        print(f"    Enter {lo}-{hi}")


def prompt_yn(msg: str) -> bool:
    while True:
        v = input(msg).strip().lower()
        if v in ("y", "yes"):
            return True
        if v in ("n", "no"):
            return False


# ── Build one field spec interactively ──────────────────────────────────

def build_spec(label: str, dirs: list[str], stem: str, headers: list[str]) -> dict:
    print(f"\n  Where does {label} come from?")
    sources = ["Directory name (from folder path)",
               "Filename (from the .csv name)",
               "Column inside the CSV",
               "Fixed value (same for every file)"]
    choice = prompt_choice(f"  {label}: ", sources)

    spec: dict = {}

    if choice == 0:  # path
        spec["source"] = "path"
        print(f"\n    Path parts:")
        for i, d in enumerate(dirs):
            print(f"      [{i}] {d}")
        spec["index"] = prompt_int(f"    Which? [0-{len(dirs)-1}]: ", 0, len(dirs) - 1)
        raw = dirs[spec["index"]]
        _ask_transforms(spec, raw)

    elif choice == 1:  # filename
        spec["source"] = "filename"
        print(f"\n    Stem: {stem}")
        how = prompt_choice("    Use how? ",
                            ["Whole stem", "Split and pick a token", "Regex capture"])
        if how == 0:
            raw = stem
        elif how == 1:
            delim = input("    Delimiter [default '_']: ").strip() or "_"
            tokens = stem.split(delim)
            print(f"    Tokens: {tokens}")
            idx = prompt_int(f"    Which? [0-{len(tokens)-1}]: ", 0, len(tokens) - 1)
            spec["delim"] = delim
            spec["tok"] = idx
            raw = tokens[idx]
        else:
            spec["regex"] = input("    Regex (group 1 captured): ").strip()
            m = re.search(spec["regex"], stem)
            raw = m.group(1) if m else stem
        _ask_transforms(spec, raw)

    elif choice == 2:  # column
        spec["source"] = "column"
        if headers:
            print(f"\n    Columns: {headers[:20]}")
            spec["col"] = headers[prompt_int(
                f"    Which? [0-{len(headers)-1}]: ", 0, len(headers) - 1)]
        else:
            spec["col"] = input("    Column name: ").strip()

    elif choice == 3:  # literal
        spec["source"] = "literal"
        spec["val"] = input(f"    Value for {label}: ").strip()

    return spec


def _ask_transforms(spec: dict, sample: str):
    print(f"    Sample value: '{sample}'")
    while prompt_yn("    Add a transform? [y/n]: "):
        t = prompt_choice("    ",
                          ["Strip prefix", "Strip suffix",
                           "Regex capture", "Zero-pad"])
        if t == 0:
            p = input("      Prefix: ")
            spec.setdefault("transforms", []).append(("prefix", p))
            if sample.startswith(p):
                sample = sample[len(p):]
        elif t == 1:
            s = input("      Suffix: ")
            spec.setdefault("transforms", []).append(("suffix", s))
            if sample.endswith(s):
                sample = sample[:-len(s)]
        elif t == 2:
            r = input("      Regex: ")
            spec.setdefault("transforms", []).append(("regex", r))
            m = re.search(r, sample)
            if m:
                sample = m.group(1)
        elif t == 3:
            w = prompt_int("      Width: ", 1, 10)
            spec.setdefault("transforms", []).append(("zfill", w))
            if sample.isdigit():
                sample = sample.zfill(w)
        print(f"      → '{sample}'")


# ── Extract a field value ───────────────────────────────────────────────

def extract(spec: dict, dirs: list[str], stem: str) -> str | None:
    src = spec["source"]

    if src == "literal":
        return spec["val"]

    elif src == "path":
        if spec["index"] >= len(dirs):
            return None
        raw = dirs[spec["index"]]

    elif src == "filename":
        raw = stem
        if "delim" in spec:
            tokens = raw.split(spec["delim"])
            if abs(spec["tok"]) >= len(tokens):
                return None
            raw = tokens[spec["tok"]]
        if "regex" in spec:
            m = re.search(spec["regex"], raw)
            if not m:
                return None
            raw = m.group(1)

    else:
        return None

    for kind, val in spec.get("transforms", []):
        if kind == "prefix" and raw.startswith(val):
            raw = raw[len(val):]
        elif kind == "suffix" and raw.endswith(val):
            raw = raw[:-len(val)]
        elif kind == "regex":
            m = re.search(val, raw)
            if m:
                raw = m.group(1)
        elif kind == "zfill" and raw.isdigit():
            raw = raw.zfill(val)

    return raw


# ── Process one dataset ─────────────────────────────────────────────────

def process_dataset(dataset: str, src_root: str, dst_root: str, dry_run: bool):
    src_dir = os.path.join(src_root, dataset)
    dst_dir = os.path.join(dst_root, dataset)
    csvs = collect_csvs(src_dir)

    if not csvs:
        print(f"  No CSVs in {dataset}, skipping.")
        return

    print(f"\n{'=' * 60}")
    print(f"{dataset}: {len(csvs)} CSV files\n")

    # Show samples
    print("  Sample paths:")
    for c in csvs[:6]:
        print(f"    {os.path.relpath(c, src_dir)}")
    if len(csvs) > 6:
        print(f"    ... and {len(csvs) - 6} more")

    sample = csvs[0]
    rel = os.path.relpath(sample, src_dir)
    parts = list(Path(rel).parts)
    dirs, stem = parts[:-1], Path(rel).stem
    headers = peek_headers(sample)

    print(f"\n  Working from: {rel}")
    print(f"  Dirs:  {dirs}")
    print(f"  Stem:  {stem}")
    if headers:
        print(f"  CSV columns: {headers[:15]}{'...' if len(headers) > 15 else ''}")

    # Optional file filter
    file_filter = None
    filter_on = None
    if prompt_yn("\n  Filter which CSVs to include? [y/n]: "):
        filter_on = "name" if prompt_choice(
            "  Filter on: ", ["Filename", "Full relative path"]) == 0 else "path"
        file_filter = input("  Regex: ").strip()

    # Define fields
    pid_spec = build_spec("pid", dirs, stem, headers)
    session_spec = build_spec("session", dirs, stem, headers)
    activity_spec = build_spec("activity", dirs, stem, headers)

    has_column = any(s["source"] == "column"
                     for s in (pid_spec, session_spec, activity_spec))

    # ── Execute ──
    seen: dict[str, str] = {}
    ok, skip, existed = 0, 0, 0

    for fpath in csvs:
        rel = os.path.relpath(fpath, src_dir)
        parts = list(Path(rel).parts)
        dirs_i, stem_i = parts[:-1], Path(rel).stem

        # Filter
        if file_filter:
            target = parts[-1] if filter_on == "name" else rel
            if not re.search(file_filter, target):
                skip += 1
                continue

        # Extract non-column fields
        pid = extract(pid_spec, dirs_i, stem_i) if pid_spec["source"] != "column" else None
        sess = extract(session_spec, dirs_i, stem_i) if session_spec["source"] != "column" else None
        act = extract(activity_spec, dirs_i, stem_i) if activity_spec["source"] != "column" else None

        if not has_column:
            if not all((pid, sess, act)):
                skip += 1
                continue
            entries = [{"pid": pid, "session": sess, "activity": act, "rows": None}]
        else:
            entries = _split_by_columns(fpath, pid_spec, session_spec, activity_spec,
                                        pid, sess, act)
            if not entries:
                skip += 1
                continue

        for e in entries:
            name = f"p-{e['pid']}_s-{e['session']}_a-{e['activity']}.csv"

            if name in seen:
                print(f"  WARN duplicate: {name}  (prev: {seen[name]}, curr: {rel})")
            seen[name] = rel

            dst_path = os.path.join(dst_dir, name)

            if not dry_run and os.path.isfile(dst_path):
                existed += 1
                continue

            if dry_run:
                print(f"  {rel}  →  {name}")
            else:
                os.makedirs(dst_dir, exist_ok=True)
                if e["rows"] is not None:
                    _write_rows(dst_path, e["headers"], e["rows"])
                else:
                    shutil.copy2(fpath, dst_path)
            ok += 1

    print(f"\n  Done: {ok} written, {skip} skipped, {existed} already existed")


def _split_by_columns(fpath, pid_spec, sess_spec, act_spec,
                       pid_val, sess_val, act_val) -> list[dict]:
    col_fields = {}
    for name, spec, static in [("pid", pid_spec, pid_val),
                                ("session", sess_spec, sess_val),
                                ("activity", act_spec, act_val)]:
        if spec["source"] == "column":
            col_fields[name] = spec["col"]

    try:
        with open(fpath, "r", newline="", errors="replace") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            buckets: dict[tuple, list] = {}
            for row in reader:
                key = tuple(row.get(col_fields[fn], "").strip()
                            for fn in sorted(col_fields))
                if all(key):
                    buckets.setdefault(key, []).append(row)
    except Exception:
        return []

    entries = []
    for key, rows in sorted(buckets.items()):
        vals = dict(zip(sorted(col_fields), key))
        entries.append({
            "pid": vals.get("pid", pid_val),
            "session": vals.get("session", sess_val),
            "activity": vals.get("activity", act_val),
            "headers": headers,
            "rows": rows,
        })
    return entries


def _write_rows(dst_path, headers, rows):
    with open(dst_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(rows)


# ── Main ────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", type=str, help="Process only this dataset")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--src", default=DEFAULT_SRC)
    ap.add_argument("--dst", default=DEFAULT_DST)
    args = ap.parse_args()

    if args.dataset:
        datasets = [args.dataset]
    else:
        datasets = sorted(d for d in os.listdir(args.src)
                          if os.path.isdir(os.path.join(args.src, d)))

    for ds in datasets:
        process_dataset(ds, args.src, args.dst, args.dry_run)


if __name__ == "__main__":
    main()
