"""
LLM-based harmonization of sensor column names for wearable IMU data.

Maps heterogeneous column names (e.g., accelerometer_right_foot_x, P6_LF_acc_x)
to a unified format: SEGMENT_SENSOR_AXIS (e.g., R_FOOT_ACC_X).

Focus: Acceleration (ACC), Gyroscope (GYR), Magnetometer (MAG).

References:
- prelim_code_ea/regex_metadata_harmonizer.py: target schema and logic
- 01_metadata/s01-v5_harmonize_GPT.py: LLM calling patterns
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path

import pandas as pd
from tqdm import tqdm
from openai import OpenAI

# Ensure parent (course/) is on path for package imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    from sync_columns.config import (
        BLUE, GREEN, YELLOW, RED, RESET, SENSOR_TYPES, SENSOR_SEGMENTS,
        MAPPING_DIR, RAW_DIR, RAW_DIR_MARKER, SYNCED_DIR,
    )
except ImportError:
    from config import (
        BLUE, GREEN, YELLOW, RED, RESET, SENSOR_TYPES, SENSOR_SEGMENTS,
        MAPPING_DIR, RAW_DIR, RAW_DIR_MARKER, SYNCED_DIR,
    )

# --- OpenAI client ---
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY")) # you need to add this as your environment variable

TARGET_SCHEMA_DESC = """
Target format: SEGMENT_SENSOR_AXIS
- SEGMENT: L_FOOT, R_FOOT, L_SHANK, R_SHANK, L_THIGH, R_THIGH, PELVIS, TRUNK, L_ARM, R_ARM, L_HAND, R_HAND, HEAD
- SENSOR: ACC (accelerometer), GYR (gyroscope), MAG (magnetometer)
- AXIS: X, Y, Z (uppercase)
Examples: R_FOOT_ACC_X, L_THIGH_GYR_Z, PELVIS_MAG_Y
"""


def filter_sensor_columns(all_columns):
    """
    Keep only columns that appear to be inertial sensor data (ACC, GYR, MAG).
    Excludes marker trajectories (e.g., LFHD_x, LTHI_y), EMG, activity, etc.
    """
    sensor_keywords = ['acc', 'gyr', 'gyro', 'mag', 'accelerometer', 'gyroscope', 'magnetometer', 'magnometer']
    
    def looks_like_sensor(col):
        col_lower = col.lower()
        # Skip marker-style (LFHD_x, LTHI_y) - short code + single axis, no sensor keyword
        if re.match(r'^[A-Z]{2,5}_[xyz]$', col) and not any(kw in col_lower for kw in sensor_keywords):
            return False
        # Skip common non-sensor
        if any(skip in col_lower for skip in ['emg', 'activity', 'label', 'timestamp', 'time']):
            return False
        return any(kw in col_lower for kw in sensor_keywords)
    
    filtered = [c for c in all_columns if looks_like_sensor(c)]
    print(f"{YELLOW}[INFO] Filtered to {len(filtered)} sensor columns (from {len(all_columns)} total).{RESET}")
    return filtered


def get_mapping_via_llm(column_names):
    """
    Use GPT to map raw column names to standardized SEGMENT_SENSOR_AXIS format.
    Returns (mapping, reasoning): mapping is {raw: standard}, reasoning is {raw: thought_process}.
    """
    print(f"{BLUE}[LLM] Consulting GPT for sensor metadata harmonization...{RESET}")
    
    prompt = f"""
You are an expert in wearable sensor metadata for human movement. Map each raw column name to the canonical format SEGMENT_SENSOR_AXIS.

{TARGET_SCHEMA_DESC}

RULES:
1. Only map columns that contain ACC, GYR, or MAG data. If a column is not an inertial sensor, use standard "UNKNOWN:raw_name" and explain why.
2. Infer segment from keywords: foot, shin, thigh, pelvis, trunk, arm, hand, head. Use L_/R_ for left/right.
3. Infer sensor: acc/accelerometer → ACC; gyr/gyroscope → GYR; mag/magnetometer → MAG.
4. Axis must be X, Y, or Z (uppercase).
5. For each column, provide your reasoning (1-2 sentences) explaining how you inferred segment, sensor, and axis.
6. Return ONLY a JSON object. For each raw column name (as key), give an object with "standard" and "reasoning":
   {{ "raw_column_name": {{ "standard": "STANDARD_NAME", "reasoning": "Your thought process..." }}, ... }}

Raw column names to map:
{json.dumps(column_names)}
"""
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"},
        stream=True,
    )
    
    full_response = ""
    with tqdm(total=100, desc=f"{BLUE}[LLM] Mapping{RESET}", bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}') as pbar:
        for chunk in response:
            delta = chunk.choices[0].delta
            content = getattr(delta, 'content', None)
            if content:
                full_response += content
                if pbar.n < 99:
                    pbar.update(1)
        pbar.n = 100
        pbar.refresh()
    
    parsed = json.loads(full_response)
    # Handle both new format {raw: {standard, reasoning}} and legacy {standard: raw}
    mapping = {}
    reasoning = {}
    for key, val in parsed.items():
        if isinstance(val, dict):
            mapping[key] = val.get("standard", val)
            reasoning[key] = val.get("reasoning", "")
        else:
            # Legacy: val is the raw name, key is standard
            mapping[val] = key
            reasoning[val] = ""
    return mapping, reasoning


def _infer_segment_mapping(rename_map):
    """Infer raw segment terms → standard segment names (e.g., shin → SHANK, thigh → THIGH)."""
    raw_term_to_std = {}
    for raw, std in rename_map.items():
        parts = std.replace("_ACC_", "|").replace("_GYR_", "|").replace("_MAG_", "|").split("|")
        std_segment = parts[0] if parts else std  # e.g. R_FOOT, L_SHANK
        base_seg = std_segment.split("_")[-1] if "_" in std_segment else std_segment  # FOOT, SHANK
        raw_lower = raw.lower().replace("-", "_")
        for term in ["shin", "leg", "thigh", "foot", "pelvis", "sacrum", "trunk", "chest", "arm", "forearm", "hand", "head", "lf", "rf", "ls", "rs", "lt", "rt", "sa", "tr"]:
            if term in raw_lower:
                raw_term_to_std[term] = {"shin": "SHANK", "leg": "SHANK", "ls": "SHANK", "rs": "SHANK",
                                        "thigh": "THIGH", "lt": "THIGH", "rt": "THIGH",
                                        "foot": "FOOT", "lf": "FOOT", "rf": "FOOT",
                                        "pelvis": "PELVIS", "sacrum": "PELVIS", "sa": "PELVIS",
                                        "trunk": "TRUNK", "chest": "TRUNK", "tr": "TRUNK",
                                        "arm": "ARM", "forearm": "FOREARM", "hand": "HAND", "head": "HEAD"}.get(term, base_seg.upper())
                break
    return dict(sorted(raw_term_to_std.items()))


def _parse_mapped_column(std_name):
    """Parse SEGMENT_SENSOR_AXIS (e.g. R_FOOT_ACC_X) into (side, segment, sensor, axis)."""
    for sensor in ("ACC", "GYR", "MAG"):
        if f"_{sensor}_" in std_name:
            pre, axis = std_name.split(f"_{sensor}_", 1)
            pre_parts = pre.split("_")
            if len(pre_parts) >= 2 and pre_parts[0] in ("L", "R"):
                side, segment = pre_parts[0], "_".join(pre_parts[1:])
            else:
                side, segment = (None, pre) if pre else (None, "?")
            return (side or "—", segment or "?", sensor, axis.upper())
    return (None, "?", "?", "?")


MIDLINE_SEGMENTS = {"TRUNK", "PELVIS", "SACRUM"}


def _mapped_column_calculation(mapped_columns):
    """Compute breakdown: n_total = n_sides × n_axes × n_sensors × n_locations.
    Midline segments (trunk, pelvis, sacrum) factor side == 1.
    """
    sides, segments, sensors, axes = set(), set(), set(), set()
    for std in mapped_columns:
        side, seg, sens, ax = _parse_mapped_column(std)
        if side and side != "—":
            sides.add(side)
        if seg and seg != "?":
            segments.add(seg)
        if sens and sens != "?":
            sensors.add(sens)
        if ax:
            axes.add(ax)

    segments_bilateral = {s for s in segments if s.upper() not in MIDLINE_SEGMENTS}
    segments_midline = {s for s in segments if s.upper() in MIDLINE_SEGMENTS}
    n_axis = len(axes) if axes else 1
    n_sensor = len(sensors) if sensors else 1
    n_side_bilateral = len(sides) if sides else 1
    n_side_midline = 1  # trunk, pelvis, sacrum factor as side == 1
    calc = (n_side_bilateral * n_axis * n_sensor * len(segments_bilateral) +
            n_side_midline * n_axis * n_sensor * len(segments_midline))
    n_side_str = f"{n_side_bilateral}(bil)+1(mid)" if segments_midline and segments_bilateral else str(n_side_bilateral if segments_bilateral else n_side_midline)
    side_str = ", ".join(sorted(sides)) if sides else "— (midline)"
    formula = f"{len(mapped_columns)} total = {n_side_str} (side) × {n_axis} (axis X,Y,Z) × {n_sensor} (sensor) × {len(segments)} (location)"
    if calc != len(mapped_columns):
        formula += f"  [expected {calc}; diff {len(mapped_columns) - calc}]"
    formula += f"  →  calc = {calc}"
    return formula, {"sides": side_str, "segments": sorted(segments), "sensors": sorted(sensors), "axes": sorted(axes)}


def _print_summary(all_columns, sensor_columns, rename_map, unknown_map):
    """Print summary: original columns, mapped columns, segment mapping, unmapped, and counts."""
    mapped_columns = list(rename_map.values())
    unmapped_sensor = list(unknown_map.keys())
    non_sensor = [c for c in all_columns if c not in sensor_columns]
    unmapped_all = unmapped_sensor + non_sensor
    segment_mapping = _infer_segment_mapping(rename_map)
    calc_formula, breakdown = _mapped_column_calculation(mapped_columns)
    
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}SUMMARY{RESET}\n")
    
    print(f"Original column names ({len(all_columns)} total):")
    print(f"  {all_columns}\n")
    
    print(f"Mapped column names ({len(mapped_columns)} total):")
    print(f"  {mapped_columns}\n")
    print(f"  {BLUE}Calculation:{RESET} {calc_formula}")
    print(f"  {BLUE}Breakdown:{RESET} sides={breakdown['sides']}, axes={breakdown['axes']}, sensors={breakdown['sensors']}, locations={breakdown['segments']}\n")
    
    print(f"Sensor placement mapping (raw term → standard):")
    print(f"  {segment_mapping}\n")
    
    print(f"Columns left unmapped ({len(unmapped_all)} total):")
    print(f"  {unmapped_all}\n")
    
    print(f"{GREEN}Counts: {len(all_columns)} original | {len(mapped_columns)} mapped | {len(segment_mapping)} segment terms | {len(unmapped_all)} unmapped{RESET}\n")


def _get_dataset_name_from_path(input_path):
    """Extract DATASET_NAME from .../{RAW_DIR_MARKER}/{DATASET_NAME}/... and return uppercase."""
    path_str = os.path.normpath(input_path)
    if RAW_DIR_MARKER in path_str:
        parts = path_str.split(os.sep)
        try:
            idx = parts.index(RAW_DIR_MARKER)
            if idx + 1 < len(parts):
                return parts[idx + 1].upper()
        except (ValueError, IndexError):
            pass
    return Path(input_path).stem.upper()


def _ask_approve_and_save_mapping(rename_map, dataset_name):
    """Prompt user to approve mapping; if [y], save to {DATASET_NAME}_mapping.json."""
    try:
        reply = input(f"\n{YELLOW}Do you approve this mapping? [y/n]: {RESET}").strip().lower()
    except EOFError:
        reply = "n"
    if reply == "y" or reply == "yes":
        os.makedirs(MAPPING_DIR, exist_ok=True)
        out_path = os.path.join(MAPPING_DIR, f"{dataset_name}_mapping.json")
        with open(out_path, "w") as f:
            json.dump(rename_map, f, indent=2)
        print(f"{GREEN}[OK] Mapping saved to {out_path}{RESET}")
    else:
        print(f"{YELLOW}[SKIP] Mapping not saved.{RESET}")


def clean_llm_json(raw_text):
    """Extract valid JSON from LLM output (handles markdown, comments)."""
    try:
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if not match:
            return None
        content = match.group(0)
        content = re.sub(r'//.*', '', content)
        content = re.sub(r',\s*}', '}', content)
        return json.loads(content)
    except Exception as e:
        print(f"{RED}[CLEANUP] {e}{RESET}")
        return None


def harmonize_csv(input_path, output_path=None, inplace=False, index_col=None):
    """
    Harmonize sensor column names in a CSV file.
    Writes to output_path, or input_path with _harmonized suffix if not specified.
    """
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}HARMONIZING: {input_path}{RESET}")
    
    # "Unnamed: 0" = pandas auto-name when CSV has an empty first header (often row index).
    # We only rename columns with valid sensor mappings; all others (Unnamed: 0, EMG, activity, etc.) stay intact.
    read_kw = {} if index_col is None else {"index_col": index_col}
    df = pd.read_csv(input_path, **read_kw)
    all_columns = list(df.columns)
    sensor_columns = filter_sensor_columns(all_columns)
    
    if not sensor_columns:
        print(f"{YELLOW}[WARN] No sensor columns found. Nothing to harmonize.{RESET}")
        return df
    
    mapping, reasoning = get_mapping_via_llm(sensor_columns)
    
    # Build rename dict: only rename columns we have mapping for (exclude UNKNOWN)
    rename_map = {raw: std for raw, std in mapping.items() if not str(std).startswith("UNKNOWN")}
    
    df_harmonized = df.rename(columns=rename_map)
    
    # Columns the LLM marked UNKNOWN (kept as-is)
    unknown_map = {raw: std for raw, std in mapping.items() if str(std).startswith("UNKNOWN")}
    
    print(f"\n{GREEN}[OK] Mapped {len(rename_map)} columns (with thought process):{RESET}\n")
    for raw, std in rename_map.items():
        thought = reasoning.get(raw, "")
        print(f"  {raw}")
        print(f"    → {std}")
        if thought:
            print(f"    {BLUE}[reasoning]{RESET} {thought}")
        print()
    
    if unknown_map:
        print(f"{YELLOW}[Unmapped – kept as-is]:{RESET}\n")
        for raw, std in unknown_map.items():
            thought = reasoning.get(raw, "")
            print(f"  {raw}")
            print(f"    → {std}")
            if thought:
                print(f"    {BLUE}[reasoning]{RESET} {thought}")
            print()
    
    # --- SUMMARY ---
    _print_summary(
        all_columns=all_columns,
        sensor_columns=sensor_columns,
        rename_map=rename_map,
        unknown_map=unknown_map,
    )
    
    # --- APPROVAL & SAVE MAPPING ---
    dataset_name = _get_dataset_name_from_path(input_path)
    _ask_approve_and_save_mapping(rename_map, dataset_name)
    
    if output_path:
        out = output_path
    elif inplace:
        out = input_path
    else:
        input_norm = os.path.normpath(input_path)
        if input_norm.startswith(RAW_DIR):
            rel = os.path.relpath(input_norm, RAW_DIR)
            out = os.path.join(SYNCED_DIR, os.path.dirname(rel), Path(input_path).stem + "_harmonized.csv")
        else:
            out = input_path.replace('.csv', '_harmonized.csv')
    
    out_dir = os.path.dirname(out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    df_harmonized.to_csv(out, index=False)
    print(f"""{GREEN}[OK] Saved to "{out}"{RESET}""")
    return df_harmonized


def harmonize_columns(column_names):
    """
    Harmonize a list of column names (no CSV). Returns (mapping, reasoning) dicts.
    """
    sensor_cols = filter_sensor_columns(column_names)
    if not sensor_cols:
        return {}, {}
    return get_mapping_via_llm(sensor_cols)


def main():
    parser = argparse.ArgumentParser(
        description="Harmonize sensor column names using LLM (ACC, GYR, MAG)."
    )
    parser.add_argument(
        "input",
        type=str,
        help="Path to CSV file or '--columns' for list mode",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output CSV path (default: input_harmonized.csv)",
    )
    parser.add_argument(
        "--inplace",
        action="store_true",
        help="Overwrite input file",
    )
    parser.add_argument(
        "--columns",
        action="store_true",
        help="Treat input as comma-separated column names (no CSV)",
    )
    parser.add_argument(
        "--index-col",
        type=int,
        default=None,
        metavar="N",
        help="Use column N (0-based) as row index when reading CSV (avoids 'Unnamed: 0' for index columns)",
    )
    args = parser.parse_args()
    
    if args.columns:
        cols = [c.strip() for c in args.input.split(",")]
        mapping, reasoning = harmonize_columns(cols)
        for raw, std in mapping.items():
            print(f"{raw} → {std}")
            if reasoning.get(raw):
                print(f"  [reasoning] {reasoning[raw]}")
        return
    
    if not os.path.isfile(args.input):
        print(f"{RED}[ERROR] File not found: {args.input}{RESET}")
        sys.exit(1)
    
    harmonize_csv(args.input, output_path=args.output, inplace=args.inplace, index_col=args.index_col)


if __name__ == "__main__":
    main()
