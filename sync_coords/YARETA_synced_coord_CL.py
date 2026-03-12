"""
batch_synced_coord_CL.py
------------------------
Runs the synced_coord_CL pipeline on every CSV found (recursively) under
INPUT_ROOT, preserves the sub-folder structure under OUTPUT_ROOT, and saves:
  - <original_name>_isb.csv   — rotated data
  - <original_name>_validation.png  — bar-chart + time-series (cell 5b)
  - <original_name>_frames_3d.png   — 3-D coordinate frames (cell 5c)

Edit the two paths at the top before running.
"""

# ── EDIT THESE TWO PATHS ──────────────────────────────────────────────────────
INPUT_ROOT  = "/Users/sofiavelasquez/Library/CloudStorage/Box-Box/WHT Datasets/01_columns_synced/YARETA/P10_S01/SYNC_DATA"
OUTPUT_ROOT = "/Users/sofiavelasquez/Library/CloudStorage/Box-Box/WHT Datasets/02_coords_synced/YARETA/P10_S01/SYNC_DATA_ISB"
# ─────────────────────────────────────────────────────────────────────────────

import os
import sys
import traceback
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")          # non-interactive backend (no display needed)
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D   # noqa: F401 – needed for 3-D projection
from matplotlib.lines import Line2D


# ══════════════════════════════════════════════════════════════════════════════
# Helper functions  (identical to notebook)
# ══════════════════════════════════════════════════════════════════════════════

G0 = 9.80665

COL_PATTERNS = dict(
    acc=("{p}_ACC_X", "{p}_ACC_Y", "{p}_ACC_Z"),
    gyr=("{p}_GYR_X", "{p}_GYR_Y", "{p}_GYR_Z"),
)


def build_sensors_from_prefixes(df, prefixes, patterns):
    cols = set(df.columns)
    sensors = {}
    for p in prefixes:
        acc_cols = tuple(s.format(p=p) for s in patterns["acc"])
        if not all(c in cols for c in acc_cols):
            continue
        gyr_cols = tuple(s.format(p=p) for s in patterns.get("gyr", ()))
        gyr_ok = len(gyr_cols) == 3 and all(c in cols for c in gyr_cols)
        sensors[p] = {"acc": acc_cols, "gyr": gyr_cols if gyr_ok else None}
    return sensors


def find_static_window(acc, gyr=None, win=300, step=50):
    acc = np.asarray(acc, float)
    N = len(acc)
    if N <= win:
        return 0, N

    def acc_stability(a):
        return float(np.mean(np.std(a, axis=0)))

    if gyr is not None:
        gyr = np.asarray(gyr, float)
        gyr_mag = np.linalg.norm(gyr, axis=1)
        def score(s, e):
            return float(np.mean(gyr_mag[s:e]) + 0.5 * acc_stability(acc[s:e]))
    else:
        def score(s, e):
            return float(acc_stability(acc[s:e]))

    best = (np.inf, 0, win)
    for s in range(0, N - win + 1, step):
        e = s + win
        sc = score(s, e)
        if sc < best[0]:
            best = (sc, s, e)
    return best[1], best[2]


def detect_accel_units_and_scale(acc_static):
    acc_static = np.asarray(acc_static, float)
    mag = np.linalg.norm(acc_static, axis=1)
    med = float(np.median(mag))
    if 0.3 <= med <= 2.5:
        return {"unit_label": "g", "scale_to_g": 1.0, "median_mag": med}
    if 6.0 <= med <= 14.0:
        return {"unit_label": "m/s^2", "scale_to_g": 1.0 / G0, "median_mag": med}
    counts_per_g = med
    return {"unit_label": "raw", "scale_to_g": 1.0 / counts_per_g,
            "median_mag": med, "counts_per_g_est": counts_per_g}


def normalize(v, eps=1e-12):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    if n < eps:
        raise ValueError("Cannot normalize near-zero vector")
    return v / n


def rot_between(a, b):
    a = normalize(a); b = normalize(b)
    v = np.cross(a, b)
    c = float(np.clip(np.dot(a, b), -1.0, 1.0))
    s = np.linalg.norm(v)
    if s < 1e-12:
        if c > 0:
            return np.eye(3)
        tmp = np.array([1, 0, 0]) if abs(a[0]) < 0.9 else np.array([0, 1, 0])
        axis = normalize(np.cross(a, tmp))
        K = np.array([[0, -axis[2], axis[1]],
                      [axis[2], 0, -axis[0]],
                      [-axis[1], axis[0], 0]])
        return np.eye(3) + 2 * (K @ K)
    K = np.array([[0, -v[2], v[1]],
                  [v[2], 0, -v[0]],
                  [-v[1], v[0], 0]])
    return np.eye(3) + K + (K @ K) * ((1 - c) / (s ** 2))


def rotate_series(R, V):
    return (R @ np.asarray(V, float).T).T


def angle_deg(u, v):
    u = normalize(u); v = normalize(v)
    c = float(np.clip(np.dot(u, v), -1.0, 1.0))
    return float(np.degrees(np.arccos(c)))


def is_foot(sensor_name):
    return "FOOT" in sensor_name.upper()


# Fixed analytic rotation matrices (from HuGaDB documentation)
R_body = np.array([[ 0,  0, -1],
                   [ 1,  0,  0],
                   [ 0, -1,  0]], dtype=float)

R_foot = np.array([[ 0,  0, -1],
                   [ 1,  0,  0],
                   [ 0, -1,  0]], dtype=float)

# foot-target → ISB
R_ft2isb = np.array([[0, -1, 0],
                     [1,  0, 0],
                     [0,  0, 1]], dtype=float)

STATIC_WIN  = 300
STATIC_STEP = 50
ISB_DOWN    = np.array([0., -1., 0.])

AXIS_COLORS = ["#e74c3c", "#27ae60", "#3498db"]
AXIS_NAMES  = ["X", "Y", "Z"]


# ══════════════════════════════════════════════════════════════════════════════
# Core processing
# ══════════════════════════════════════════════════════════════════════════════

def process_file(csv_path, out_dir, dataset_name):
    """
    Process one CSV file.  Saves:
      <out_dir>/<dataset_name>_isb.csv
      <out_dir>/<dataset_name>_validation.png
      <out_dir>/<dataset_name>_frames_3d.png
    """
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()

    prefixes = sorted({c.replace("_ACC_X", "") for c in df.columns if c.endswith("_ACC_X")})
    SENSORS = build_sensors_from_prefixes(df, prefixes, COL_PATTERNS)
    if not SENSORS:
        print(f"  [SKIP] No IMU columns detected in {csv_path}")
        return

    df_out   = df.copy()
    report   = []
    rotations = {}

    for _s, _m in SENSORS.items():
        for _col in _m["acc"]:
            df_out[_col] = df_out[_col].astype("float64")
        if _m.get("gyr") is not None:
            for _col in _m["gyr"]:
                df_out[_col] = df_out[_col].astype("float64")

    for s, m in SENSORS.items():
        acc_cols = m["acc"]
        gyr_cols = m["gyr"]

        acc_raw = df.loc[:, acc_cols].to_numpy(float)
        gyr_raw = df.loc[:, gyr_cols].to_numpy(float) if gyr_cols is not None else None

        ws, we = find_static_window(acc_raw, gyr=gyr_raw,
                                    win=min(STATIC_WIN, len(df)), step=STATIC_STEP)
        info  = detect_accel_units_and_scale(acc_raw[ws:we])
        scale = float(info["scale_to_g"])
        acc_g = acc_raw * scale

        R = R_foot if is_foot(s) else R_body
        rotations[s] = R

        acc_isb = rotate_series(R, acc_g)
        df_out.loc[:, acc_cols[0]] = acc_isb[:, 0]
        df_out.loc[:, acc_cols[1]] = acc_isb[:, 1]
        df_out.loc[:, acc_cols[2]] = acc_isb[:, 2]

        if gyr_raw is not None:
            gyr_isb = rotate_series(R, gyr_raw)
            df_out.loc[:, gyr_cols[0]] = gyr_isb[:, 0]
            df_out.loc[:, gyr_cols[1]] = gyr_isb[:, 1]
            df_out.loc[:, gyr_cols[2]] = gyr_isb[:, 2]

        g_after   = np.mean(acc_isb[ws:we], axis=0)
        ang_after = angle_deg(g_after, ISB_DOWN)

        report.append({
            "sensor":                   s,
            "static_start":             ws,
            "static_end":               we,
            "detected_unit":            info["unit_label"],
            "scale_to_g":               scale,
            "gravity_angle_after_deg":  ang_after,
        })

    report_df = pd.DataFrame(report).sort_values("sensor")

    # ── Save CSV ──────────────────────────────────────────────────────────────
    os.makedirs(out_dir, exist_ok=True)
    csv_out = os.path.join(out_dir, f"{dataset_name}_isb.csv")
    df_out.to_csv(csv_out, index=False)

    # ── Plot 1: Validation (bar chart + time series) — cell 5b ───────────────
    sensors_list = report_df["sensor"].tolist()
    axes_labels  = ["X", "Y", "Z"]
    colors       = AXIS_COLORS

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(14, 5), dpi=150)
    fig.suptitle(dataset_name, fontsize=11, fontweight="bold")

    mean_before = np.zeros((len(sensors_list), 3))
    mean_after  = np.zeros((len(sensors_list), 3))
    for i, s in enumerate(sensors_list):
        row  = report_df[report_df["sensor"] == s].iloc[0]
        ws2  = int(row["static_start"]); we2 = int(row["static_end"])
        scl  = float(row["scale_to_g"])
        acols = SENSORS[s]["acc"]
        mean_before[i] = (df.loc[ws2:we2 - 1, acols].to_numpy(float) * scl).mean(axis=0)
        mean_after[i]  = df_out.loc[ws2:we2 - 1, acols].to_numpy(float).mean(axis=0)

    x = np.arange(len(sensors_list))
    w = 0.25
    for j, (ax_name, jcol) in enumerate(zip(axes_labels, [0, 1, 2])):
        ax1.bar(x + (j - 1) * w, mean_before[:, jcol], w,
                label=ax_name, alpha=0.85, color=colors[j])
    ax1.axhline(0,  color="gray",  linewidth=0.5)
    ax1.axhline(-1, color="green", linestyle="--", linewidth=0.7, alpha=0.7)
    ax1.set_xticks(x); ax1.set_xticklabels(sensors_list, rotation=45, ha="right")
    ax1.set_ylabel("Mean accel (g)")
    ax1.set_title("Before (sensor frame, g)")
    ax1.legend(loc="upper right", fontsize=8)
    ax1.set_ylim(-1.5, 1.5)

    for j, (ax_name, jcol) in enumerate(zip(axes_labels, [0, 1, 2])):
        ax2.bar(x + (j - 1) * w, mean_after[:, jcol], w,
                label=ax_name, alpha=0.85, color=colors[j])
    ax2.axhline(0,  color="gray",  linewidth=0.5)
    ax2.axhline(-1, color="green", linestyle="--", linewidth=0.7, alpha=0.7)
    ax2.set_xticks(x); ax2.set_xticklabels(sensors_list, rotation=45, ha="right")
    ax2.set_ylabel("Mean accel (g)")
    ax2.set_title("After (ISB);  Y ≈ -1 g")
    ax2.legend(loc="upper right", fontsize=8)
    ax2.set_ylim(-1.5, 1.5)

    example_sensor = sensors_list[0]
    row2 = report_df[report_df["sensor"] == example_sensor].iloc[0]
    ws2  = int(row2["static_start"]); we2 = int(row2["static_end"])
    scl2 = float(row2["scale_to_g"])
    acols2 = SENSORS[example_sensor]["acc"]
    idx = np.arange(ws2, we2)
    before_y = df.loc[ws2:we2 - 1, acols2[1]].to_numpy(float) * scl2
    after_y  = df_out.loc[ws2:we2 - 1, acols2[1]].to_numpy(float)
    ax3.plot(idx, before_y, alpha=0.8, label="Before (sensor frame, g)", color="C0")
    ax3.plot(idx, after_y,  alpha=0.8, label="After (ISB)",              color="C1")
    ax3.axhline(-1, color="green", linestyle="--", linewidth=0.8, alpha=0.8)
    ax3.set_xlabel("Sample index")
    ax3.set_ylabel("Accel Y (g)")
    ax3.set_title(f"{example_sensor} ACC_Y — {dataset_name}")
    ax3.legend(loc="upper right")
    ax3.set_ylim(-1.5, 0.5)

    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, f"{dataset_name}_validation.png"),
                bbox_inches="tight")
    plt.close(fig)

    # ── Plot 2: 3-D coordinate frames — cell 5c ───────────────────────────────
    def seg_height(name):
        n = name.upper()
        if "FOOT"  in n: return -1.2
        if "SHANK" in n: return  0.0
        if "THIGH" in n: return  1.2
        return 0.0

    def seg_side(name):
        return -0.6 if name.upper().startswith("L_") else 0.6

    positions   = np.array([[seg_side(s), seg_height(s), 0.0] for s in sensors_list])
    arrow_scale = 0.4

    fig2 = plt.figure(figsize=(15, 5), dpi=150)
    fig2.suptitle(dataset_name, fontsize=11, fontweight="bold")

    ax_b = fig2.add_subplot(121, projection="3d")
    for i, s in enumerate(sensors_list):
        R_viz = (R_ft2isb @ rotations[s]) if is_foot(s) else rotations[s]
        px, py, pz = positions[i]
        for j in range(3):
            dx, dy, dz = arrow_scale * R_viz[:, j]
            ax_b.quiver(px, pz, py, dx, dz, dy,
                        color=AXIS_COLORS[j], arrow_length_ratio=0.15, linewidth=1.5)
        ax_b.text(px + 0.05, pz, py + 0.05, s, fontsize=8)
    ax_b.set_xlabel("Yareta Z (backward)")
    ax_b.set_ylabel("Yareta Y (right)")
    ax_b.set_zlabel("Yareta X (up)")
    ax_b.set_title("Before")
    lim = 2.0
    ax_b.set_xlim(-lim, lim); ax_b.set_ylim(-lim, lim); ax_b.set_zlim(-lim, lim)
    ax_b.set_box_aspect([1, 1, 1])
    ax_b.view_init(elev=20, azim=-60)
    leg = [Line2D([0], [0], color=AXIS_COLORS[j], lw=2, label=AXIS_NAMES[j]) for j in range(3)]
    ax_b.legend(handles=leg, loc="upper left", frameon=False)

    ax_a = fig2.add_subplot(122, projection="3d")
    for i, s in enumerate(sensors_list):
        R_viz = R_ft2isb if is_foot(s) else np.eye(3)
        px, py, pz = positions[i]
        for j in range(3):
            dx, dy, dz = arrow_scale * R_viz[:, j]
            ax_a.quiver(px, pz, py, dx, dz, dy,
                        color=AXIS_COLORS[j], arrow_length_ratio=0.15, linewidth=1.5)
        ax_a.text(px + 0.05, pz, py + 0.05, s, fontsize=8)
    ax_a.set_xlabel("ISB X (front)")
    ax_a.set_ylabel("ISB Z (right)")
    ax_a.set_zlabel("ISB Y (up)")
    ax_a.set_title("After")
    ax_a.set_xlim(-lim, lim); ax_a.set_ylim(-lim, lim); ax_a.set_zlim(-lim, lim)
    ax_a.set_box_aspect([1, 1, 1])
    ax_a.view_init(elev=20, azim=-60)
    leg = [Line2D([0], [0], color=AXIS_COLORS[j], lw=2, label=AXIS_NAMES[j]) for j in range(3)]
    ax_a.legend(handles=leg, loc="upper left", frameon=False)

    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, f"{dataset_name}_frames_3d.png"),
                bbox_inches="tight")
    plt.close(fig2)

    print(f"  [OK]  {dataset_name}  →  {out_dir}")


# ══════════════════════════════════════════════════════════════════════════════
# Batch runner
# ══════════════════════════════════════════════════════════════════════════════

def main():
    csv_files = []
    for dirpath, _, filenames in os.walk(INPUT_ROOT):
        for fname in filenames:
            if fname.lower().endswith(".csv"):
                csv_files.append(os.path.join(dirpath, fname))

    if not csv_files:
        print(f"No CSV files found under: {INPUT_ROOT}")
        sys.exit(1)

    print(f"Found {len(csv_files)} CSV file(s) under {INPUT_ROOT}\n")

    ok = 0; fail = 0
    for csv_path in sorted(csv_files):
        # Relative path from INPUT_ROOT  →  mirrors to OUTPUT_ROOT
        rel_dir  = os.path.relpath(os.path.dirname(csv_path), INPUT_ROOT)
        out_dir  = os.path.join(OUTPUT_ROOT, rel_dir)

        # Dataset name = CSV filename without extension (used in plot titles & output names)
        dataset_name = os.path.splitext(os.path.basename(csv_path))[0]

        print(f"Processing: {os.path.relpath(csv_path, INPUT_ROOT)}")
        try:
            process_file(csv_path, out_dir, dataset_name)
            ok += 1
        except Exception:
            print(f"  [ERROR] {csv_path}")
            traceback.print_exc()
            fail += 1

    print(f"\nDone — {ok} succeeded, {fail} failed.")
    print(f"Output saved to: {OUTPUT_ROOT}")


if __name__ == "__main__":
    main()
