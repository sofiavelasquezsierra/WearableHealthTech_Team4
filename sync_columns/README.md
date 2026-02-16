# Sensor Metadata Harmonization (LLM-based)

Harmonizes heterogeneous sensor column names to a unified format: **SEGMENT_SENSOR_AXIS**.

## Target Format

Examples: `R_FOOT_ACC_X`, `L_THIGH_GYR_Z`, `PELVIS_MAG_Y`

- **SEGMENT**: L_FOOT, R_FOOT, L_SHANK, R_SHANK, L_THIGH, R_THIGH, PELVIS, TRUNK, etc.
- **SENSOR**: ACC (accelerometer), GYR (gyroscope), MAG (magnetometer)
- **AXIS**: X, Y, Z

## Dependencies

```bash
pip install pandas openai tqdm
```

Set `OPENAI_API_KEY` in your environment.

## Usage

### Step 1: Get mapping (run on one sample file per dataset)

**HuGaDB:**
```bash
python get_mapping.py "/Users/nny/Library/CloudStorage/Box-Box/WHT Datasets/00_raw/HUGADB/HuGaDB_v2_various_01_00.csv" -o "/Users/nny/Library/CloudStorage/Box-Box/WHT Datasets/01_columns_synced/test_hugadb.csv"
```

**Yareta:**
```bash
python get_mapping.py "/Users/nny/Library/CloudStorage/Box-Box/WHT Datasets/00_raw/YARETA/Human gait and other movements - markers inertial sensors pressure insoles force plates/researchdata/P01_S01/SYNC_DATA/P01_S01_SlowGait_01.csv" -o "/Users/nny/Library/CloudStorage/Box-Box/WHT Datasets/01_columns_synced/test_yareta.csv"
```

**CAMARGO** (replace `SAMPLE.csv` with a file from `00_raw/CAMARGO/CAMARSO_CSV/`):
```bash
python get_mapping.py "/Users/nny/Library/CloudStorage/Box-Box/WHT Datasets/00_raw/CAMARGO/CAMARSO_CSV/SAMPLE.csv" -o "/Users/nny/Library/CloudStorage/Box-Box/WHT Datasets/01_columns_synced/test_camargo.csv"
```

**RealWorldHAR** (replace path with a file from `00_raw/RealWorldHAR/realworld2016_dataset/`, e.g. `S1/*.csv`):
```bash
python get_mapping.py "/Users/nny/Library/CloudStorage/Box-Box/WHT Datasets/00_raw/RealWorldHAR/realworld2016_dataset/S1/SAMPLE.csv" -o "/Users/nny/Library/CloudStorage/Box-Box/WHT Datasets/01_columns_synced/test_realworldhar.csv"
```

**NEWBEE** (replace path with a file from `00_raw/NEWBEE/multi_modal_gait_database/data_set/`):
```bash
python get_mapping.py "/Users/nny/Library/CloudStorage/Box-Box/WHT Datasets/00_raw/NEWBEE/multi_modal_gait_database/data_set/SAMPLE.csv" -o "/Users/nny/Library/CloudStorage/Box-Box/WHT Datasets/01_columns_synced/test_newbee.csv"
```

Or run all three with the helper script: `./run_get_mapping.sh`

### Step 2: Convert all files in dataset

```bash
python main.py HUGADB
python main.py YARETA --dry-run
```

### Harmonize column names only (no CSV)

```bash
python get_mapping.py --columns "accelerometer_right_foot_x,gyroscope_left_thigh_z"
```

## References

- `prelim_code_ea/regex_metadata_harmonizer.py` – regex-based approach and target schema
- `01_metadata/s01-v5_harmonize_GPT.py` – LLM calling patterns for biomechanics
