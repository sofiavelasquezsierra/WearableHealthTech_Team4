"""
Transform NEWBEE sensor data to a standard body-segment-aligned orientation.

After column syncing, NEWBEE data has:
  - ACC from sensorFreeAcceleration (sensor frame, gravity-free)
  - GYR from angularVelocity (global frame -- needs rotation to sensor frame)
  - MAG from sensorMagneticField (sensor frame)

This script:
  1. Rotates GYR from Xsens global frame to sensor frame using sensorOrientation
  2. Detects a quasi-static window per trial to extract mean sensor orientation
  3. Computes a per-sensor correction rotation to the target body frame
  4. Applies the correction to all ACC, GYR, MAG channels

Target convention (static standing pose):
  Non-foot: Y-up, X-forward, Z-right
  Foot:     X-up, Y-backward, Z-right

Usage:
  python transform_orientation.py                # process all subjects
  python transform_orientation.py --dry-run      # show what would be done
  python transform_orientation.py --subject id01 # single subject
"""

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    from sync_columns.config import RAW_DIR, SYNCED_DIR, COORDS_SYNCED_DIR, SENSOR_TYPES
except ImportError:
    from config import RAW_DIR, SYNCED_DIR, COORDS_SYNCED_DIR, SENSOR_TYPES

NEWBEE_RAW_XSENS = os.path.join(
    RAW_DIR, "NEWBEE", "multi_modal_gait_database", "data_set_only_xsens"
)
NEWBEE_SYNCED = os.path.join(SYNCED_DIR, "NEWBEE")
NEWBEE_COORDS = os.path.join(COORDS_SYNCED_DIR, "NEWBEE")

# Mapping from synced segment name to Xsens raw segment name
SEGMENT_TO_XSENS = {
    "PELVIS": "Pelvis",
    "TRUNK": "T8",
    "HEAD": "Head",
    "R_ARM": "RightUpperArm",
    "L_ARM": "LeftUpperArm",
    "R_FOREARM": "RightForeArm",
    "L_FOREARM": "LeftForeArm",
    "R_HAND": "RightHand",
    "L_HAND": "LeftHand",
    "R_THIGH": "RightUpperLeg",
    "L_THIGH": "LeftUpperLeg",
    "R_SHANK": "RightLowerLeg",
    "L_SHANK": "LeftLowerLeg",
    "R_FOOT": "RightFoot",
    "L_FOOT": "LeftFoot",
}

FOOT_SEGMENTS = {"R_FOOT", "L_FOOT"}


def quat_cols(xsens_seg):
    """Return the 4 sensorOrientation column names for a given Xsens segment."""
    return [f"sensorOrientation_{xsens_seg}_{q}" for q in ("q1", "qi", "qj", "qk")]


def load_quaternions(raw_df, xsens_seg):
    """Extract sensorOrientation quaternions as scipy Rotation array.
    Xsens convention: q1=w, qi=x, qj=y, qk=z.  scipy wants [x,y,z,w]."""
    cols = quat_cols(xsens_seg)
    q = raw_df[cols].values  # [w, x, y, z]
    return R.from_quat(np.column_stack([q[:, 1], q[:, 2], q[:, 3], q[:, 0]]))


def find_static_window(raw_df, xsens_seg, window_sec=1.0, fs=60.0):
    """Find the lowest-motion window in sensorFreeAcceleration.
    Returns (start_idx, end_idx) of the quietest window."""
    acc_cols = [f"sensorFreeAcceleration_{xsens_seg}_{a}" for a in ("x", "y", "z")]
    if not all(c in raw_df.columns for c in acc_cols):
        return 0, min(int(fs * window_sec), len(raw_df))
    acc = raw_df[acc_cols].values
    mag = np.sqrt(np.sum(acc ** 2, axis=1))
    win = max(int(fs * window_sec), 1)
    if len(mag) <= win:
        return 0, len(mag)
    # Rolling mean of acceleration magnitude -- lowest = most static
    cumsum = np.cumsum(mag)
    rolling = (cumsum[win:] - cumsum[:-win]) / win
    best_start = int(np.argmin(rolling))
    return best_start, best_start + win


def mean_quaternion(rotations):
    """Average quaternion via eigenvalue method on the quaternion outer-product matrix."""
    quats = rotations.as_quat()  # [x,y,z,w]
    M = quats.T @ quats
    eigvals, eigvecs = np.linalg.eigh(M)
    return R.from_quat(eigvecs[:, -1])


def compute_correction_rotation(R_sensor_to_global, segment_name):
    """Compute the rotation from sensor frame to the target body-segment frame.

    Target frames (columns of R_target_to_global):
      Non-foot: X=forward, Y=up,   Z=right  (right-handed)
      Foot:     X=up,      Y=-fwd, Z=right  (right-handed)

    We derive "forward" from the sensor's own orientation projected onto the
    ground plane (global XY), and "up" = global +Z.
    """
    mat = R_sensor_to_global.as_matrix()  # columns = sensor axes in global

    # Global up
    up = np.array([0.0, 0.0, 1.0])

    # Determine forward: project sensor's Y-axis (non-foot) or -Y-axis (foot)
    # onto the horizontal plane. For a standing person this roughly points forward.
    # Use the sensor axis that is most horizontal (least aligned with Z).
    sensor_axes_global = mat.T  # rows = sensor x,y,z in global coords
    horiz_proj = sensor_axes_global.copy()
    horiz_proj[:, 2] = 0  # zero out vertical component
    horiz_norms = np.linalg.norm(horiz_proj, axis=1)

    if segment_name in FOOT_SEGMENTS:
        # For feet: use the axis with largest horizontal component as forward proxy
        best_horiz = int(np.argmax(horiz_norms))
        fwd_raw = horiz_proj[best_horiz]
        fwd_raw /= np.linalg.norm(fwd_raw) + 1e-12
        # Determine sign: use pelvis forward as reference (caller can override).
        # For now, pick the direction that has a positive dot with global +X (rough heading).
        forward = fwd_raw if fwd_raw[0] >= 0 else -fwd_raw
    else:
        # For non-foot: use the most horizontal axis as forward
        best_horiz = int(np.argmax(horiz_norms))
        fwd_raw = horiz_proj[best_horiz]
        fwd_raw /= np.linalg.norm(fwd_raw) + 1e-12
        forward = fwd_raw if fwd_raw[0] >= 0 else -fwd_raw

    # Right = forward x up (right-handed)
    right = np.cross(forward, up)
    right /= np.linalg.norm(right) + 1e-12

    # Re-orthogonalize forward
    forward = np.cross(up, right)
    forward /= np.linalg.norm(forward) + 1e-12

    if segment_name in FOOT_SEGMENTS:
        # Target: X=up, Y=-forward, Z=right
        R_target = np.column_stack([up, -forward, right])
    else:
        # Target: X=forward, Y=up, Z=right
        R_target = np.column_stack([forward, up, right])

    R_target_rot = R.from_matrix(R_target)
    R_correction = R_target_rot.inv() * R_sensor_to_global
    return R_correction


def derive_forward_from_pelvis(raw_df):
    """Get the forward direction in global frame from the pelvis sensor orientation
    during the static window. Returns a unit vector in the XY plane."""
    rots = load_quaternions(raw_df, "Pelvis")
    start, end = find_static_window(raw_df, "Pelvis")
    R_mean = mean_quaternion(rots[start:end])
    mat = R_mean.as_matrix()
    # Sensor axes in global
    sensor_axes_global = mat.T  # rows = sensor x,y,z in global
    # Find the most horizontal axis
    horiz = sensor_axes_global.copy()
    horiz[:, 2] = 0
    norms = np.linalg.norm(horiz, axis=1)
    best = int(np.argmax(norms))
    fwd = horiz[best]
    fwd /= np.linalg.norm(fwd) + 1e-12
    return fwd


def compute_correction_with_heading(R_sensor_to_global, segment_name, heading_fwd):
    """Compute correction rotation using a known forward heading direction."""
    up = np.array([0.0, 0.0, 1.0])
    forward = heading_fwd.copy()
    forward[2] = 0  # project to horizontal
    forward /= np.linalg.norm(forward) + 1e-12

    right = np.cross(forward, up)
    right /= np.linalg.norm(right) + 1e-12
    forward = np.cross(up, right)
    forward /= np.linalg.norm(forward) + 1e-12

    if segment_name in FOOT_SEGMENTS:
        R_target = np.column_stack([up, -forward, right])
    else:
        R_target = np.column_stack([forward, up, right])

    R_target_rot = R.from_matrix(R_target)
    R_correction = R_target_rot.inv() * R_sensor_to_global
    return R_correction


def find_matching_raw_csv(synced_csv_path):
    """Given a synced CSV path, find the corresponding raw xsens CSV
    in data_set_only_xsens with matching course/subject structure."""
    rel = os.path.relpath(synced_csv_path, NEWBEE_SYNCED)
    parts = Path(rel).parts  # e.g. ('courseA', 'id01', 'xsens.csv')
    raw_path = os.path.join(NEWBEE_RAW_XSENS, *parts)
    if os.path.isfile(raw_path):
        return raw_path
    return None


def transform_synced_df(synced_df, raw_df):
    """
    Apply coordinate alignment to synced dataframe in memory using raw_df (with quaternions).
    Returns (success, coords_df, message). coords_df is a copy of synced_df with rotations applied.
    """
    if len(synced_df) != len(raw_df):
        return False, None, f"row count mismatch: synced={len(synced_df)}, raw={len(raw_df)}"

    coords_df = synced_df.copy()
    heading_fwd = derive_forward_from_pelvis(raw_df)

    for seg, xsens_seg in SEGMENT_TO_XSENS.items():
        qcols = quat_cols(xsens_seg)
        if not all(c in raw_df.columns for c in qcols):
            continue

        rots = load_quaternions(raw_df, xsens_seg)

        gyr_cols = [f"{seg}_GYR_{ax}" for ax in ("X", "Y", "Z")]
        if all(c in coords_df.columns for c in gyr_cols):
            gyr_global = coords_df[gyr_cols].values
            gyr_sensor = rots.inv().apply(gyr_global)
            coords_df[gyr_cols] = gyr_sensor

        start, end = find_static_window(raw_df, xsens_seg)
        R_mean = mean_quaternion(rots[start:end])
        R_corr = compute_correction_with_heading(R_mean, seg, heading_fwd)

        det = np.linalg.det(R_corr.as_matrix())
        if abs(det - 1.0) > 0.01:
            return False, None, f"bad determinant for {seg}: {det:.4f}"

        for sensor_type in SENSOR_TYPES:
            cols = [f"{seg}_{sensor_type}_{ax}" for ax in ("X", "Y", "Z")]
            if all(c in coords_df.columns for c in cols):
                data = coords_df[cols].values
                coords_df[cols] = R_corr.apply(data)

    return True, coords_df, "ok"


def process_one_file(synced_path, dry_run=False):
    """Process a single synced CSV: rotate GYR to sensor frame,
    then apply body-frame correction to all channels."""
    raw_path = find_matching_raw_csv(synced_path)
    if not raw_path:
        return False, "no matching raw file"

    synced_df = pd.read_csv(synced_path)
    raw_df = pd.read_csv(raw_path)

    if len(synced_df) != len(raw_df):
        return False, f"row count mismatch: synced={len(synced_df)}, raw={len(raw_df)}"

    if dry_run:
        return True, "would process"

    success, coords_df, msg = transform_synced_df(synced_df, raw_df)
    if not success:
        return False, msg

    rel = os.path.relpath(synced_path, NEWBEE_SYNCED)
    out_path = os.path.join(NEWBEE_COORDS, rel)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    coords_df.to_csv(out_path, index=False)
    return True, "ok"


def collect_synced_csvs(subject_filter=None):
    """Find all synced NEWBEE CSV files, optionally filtered by subject ID."""
    csvs = []
    for dp, _, files in os.walk(NEWBEE_SYNCED):
        for f in sorted(files):
            if not f.lower().endswith(".csv"):
                continue
            path = os.path.join(dp, f)
            if subject_filter:
                if subject_filter not in path:
                    continue
            csvs.append(path)
    return csvs


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without writing")
    parser.add_argument("--subject", type=str, default=None,
                        help="Process only this subject ID (e.g. id01)")
    args = parser.parse_args()

    csvs = collect_synced_csvs(args.subject)
    print(f"Found {len(csvs)} synced CSV files")
    if not csvs:
        return

    ok, fail = 0, 0
    for path in csvs:
        rel = os.path.relpath(path, NEWBEE_SYNCED)
        success, msg = process_one_file(path, dry_run=args.dry_run)
        if success:
            ok += 1
        else:
            fail += 1
            print(f"  SKIP {rel}: {msg}")

    print(f"\nDone: {ok} processed, {fail} skipped")


if __name__ == "__main__":
    main()
