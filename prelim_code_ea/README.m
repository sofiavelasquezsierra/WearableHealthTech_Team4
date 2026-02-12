# Column Name Harmonization with Regex Pattern Matching

This tool helps you standardize sensor column names from different datasets into a unified format.

## Overview

The `regex_meta_harmonize()` function converts varied column naming conventions into a standardized format: `SEGMENT_SENSOR_AXIS` (e.g., `R_FOOT_ACC_X`).

## Quick Start

### Step 1: Analyze Your Dataset's Naming Convention

Look at your column names and identify the pattern. For example:
- `accelerometer_right_foot_x` → sensor_segment_axis
- `Acc_X_LThigh` → sensor_axis_segment
- `RShank_Gyr_Y` → segment_sensor_axis

### Step 2: Create Your Regex Pattern

**Option A: Use an LLM (Recommended for Beginners)**

Prompt example:
```
I have sensor column names that follow this pattern:
- accelerometer_right_foot_x
- gyroscope_left_shin_y
- accelerometer_right_thigh_z

Create a regex pattern that captures three groups:
1. Sensor type (accelerometer/gyroscope)
2. Body segment (right_foot/left_shin/etc.)
3. Axis (x/y/z)
```

**Option B: Manual Pattern Creation**

Common regex building blocks:
- `([a-z]+)` - captures lowercase letters (sensor type)
- `([XYZ])` - captures uppercase single letter (axis)
- `([a-z]+_[a-z]+)` - captures two words separated by underscore (segment)
- `_` - literal underscore separator

Example patterns:
```python
# Pattern for: accelerometer_right_foot_x
patternHuGa = r"([a-z]+)_([a-z]+_[a-z]+)_([xyz])"

# Pattern for: Acc_X_LThigh
patternEx = r"([a-zA-Z]+)_([XYZ])_([a-zA-Z]+)"

# Pattern for: RShank_Gyr_Y
patternCustom = r"([a-zA-Z]+)_([a-zA-Z]+)_([XYZ])"
```

### Step 3: Define the Order Dictionary

Create a dictionary that maps the regex capture groups to their meaning **in the order they appear**:
```python
# For pattern: ([a-z]+)_([a-z]+_[a-z]+)_([xyz])
# Group 1 = sensor, Group 2 = segment, Group 3 = axis
orderHuGa = {
    'sensor': [],   # 1st capture group
    'segment': [],  # 2nd capture group  
    'axis': []      # 3rd capture group
}

# For pattern: ([a-zA-Z]+)_([XYZ])_([a-zA-Z]+)
# Group 1 = sensor, Group 2 = axis, Group 3 = segment
orderEx = {
    'sensor': [],   # 1st capture group
    'axis': [],     # 2nd capture group
    'segment': []   # 3rd capture group
}
```

**Important:** The keys in the dictionary must be in the order that corresponds to the capture groups in your regex pattern.

### Step 4: Use the Function
```python
import re

# Your pattern and order
pattern = r"([a-z]+)_([a-z]+_[a-z]+)_([xyz])"
order = {'sensor': [], 'segment': [], 'axis': []}

# Harmonize column names
standardized_name = regex_meta_harmonize(
    col_name="accelerometer_right_foot_x",
    pattern=pattern,
    order=order
)

print(standardized_name)  # Output: R_FOOT_ACC_X
```

## Full Example
```python
import re

# Define your pattern and order
patternHuGa = r"([a-z]+)_([a-z]+_[a-z]+)_([xyz])"
orderHuGa = {
    'sensor': [],   # matches ([a-z]+) - first group
    'segment': [],  # matches ([a-z]+_[a-z]+) - second group
    'axis': []      # matches ([xyz]) - third group
}

# Test with your columns
columns = [
    "accelerometer_right_foot_x",
    "accelerometer_right_shin_y",
    "gyroscope_left_thigh_z"
]

for col in columns:
    result = regex_meta_harmonize(col, patternHuGa, orderHuGa)
    print(f"{col:35} → {result}")
```

Output:
```
accelerometer_right_foot_x          → R_FOOT_ACC_X
accelerometer_right_shin_y          → R_FOOT_SHANK_Y
gyroscope_left_thigh_z              → L_THIGH_GYR_Z
```

## Customization

### Adding New Sensor Types

Edit the `get_sensor()` function:
```python
sensor_keywords = {
    'GYR': ['gyr', 'gyroscope'],
    'ACC': ['acc', 'acceleration', 'accelerometer'],
    'MAG': ['mag', 'magnometer'],
    'EMG': ['emg', 'electromyography']  # Add new sensor
}
```

### Adding New Body Segments

Edit the `get_segment()` function:
```python
anatomy_keywords = {
    'FOOT': ['foot', 'FOOT'],
    'WRIST': ['wrist', 'WRIST'],  # Add new segment
    # ... other segments
}
```

## Troubleshooting

**Problem:** Getting `UNKNOWN: column_name`
- **Solution:** Your pattern doesn't match. Check that your regex pattern matches the exact format of your column names.