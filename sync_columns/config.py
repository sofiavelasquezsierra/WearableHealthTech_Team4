from os.path import join

"""
Configuration for sensor metadata harmonization.
Target format: SEGMENT_SENSOR_AXIS (e.g., R_FOOT_ACC_X, L_THIGH_GYR_Z)
"""

BLUE, GREEN, YELLOW, RED, RESET = '\033[94m', '\033[92m', '\033[93m', '\033[91m', '\033[0m'

# --- Paths (change these to your own) ---
WHT_DATASETS_DIR = "/Users/nny/Library/CloudStorage/Box-Box/WHT Datasets"
RAW_DIR = join(WHT_DATASETS_DIR, "00_raw")
SYNCED_DIR = join(WHT_DATASETS_DIR, "01_columns_synced")
MAPPING_DIR = join(SYNCED_DIR, "00_mappings")
RAW_DIR_MARKER = "00_raw"  # used to extract dataset name from path

# Canonical sensor types for inertial measurement units (IMU)
SENSOR_TYPES = ['ACC', 'GYR', 'MAG']

# Canonical body segments for wearable sensor placement (lower body + common upper body)
SENSOR_SEGMENTS = {
    'L_FOOT': 'Left Foot',
    'R_FOOT': 'Right Foot',
    'L_SHANK': 'Left Shank (Lower Leg)',
    'R_SHANK': 'Right Shank (Lower Leg)',
    'L_THIGH': 'Left Thigh (Upper Leg)',
    'R_THIGH': 'Right Thigh (Upper Leg)',
    'L_PELVIS': 'Left Pelvis / Hip',
    'R_PELVIS': 'Right Pelvis / Hip',
    'PELVIS': 'Pelvis / Sacrum (midline)',
    'TRUNK': 'Trunk / Sternum / Chest',
    'L_ARM': 'Left Upper Arm',
    'R_ARM': 'Right Upper Arm',
    'L_FOREARM': 'Left Forearm',
    'R_FOREARM': 'Right Forearm',
    'L_HAND': 'Left Hand / Wrist',
    'R_HAND': 'Right Hand / Wrist',
    'HEAD': 'Head',
}

# Axis labels
AXES = ['X', 'Y', 'Z']

# Dataset-specific subdirs under RAW_DIR
DATASET_ROOTS = {
    "YARETA": join(RAW_DIR, "YARETA", "Human gait and other movements - markers inertial sensors pressure insoles force plates", "researchdata"),
    "CAMARGO": join(RAW_DIR, "CAMARGO", "Camargo_CSV"),
    "RealWorldHAR": join(RAW_DIR, "RealWorldHAR", "realworld2016_dataset"),
    "HUGADB": join(RAW_DIR, "HUGADB"),
    "NEWBEE": join(RAW_DIR, "NEWBEE", "multi_modal_gait_database", "data_set"),
}
