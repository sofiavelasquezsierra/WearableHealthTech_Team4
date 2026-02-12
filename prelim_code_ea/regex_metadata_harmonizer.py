import re
import pandas as pd

# Construct a pattern based on the convention followed by the dataset you are trying to harmonize
# Example Pattern: matches "Acc_X_LThigh" or "Gyr_Y_RShank"
# Group 1: Sensor (Acc/Gyr), Group 2: Axis (X/Y/Z), Group 3: Segment (LThigh/RShank)
pattern = r"([a-zA-Z]+)_([XYZ])_([a-zA-Z]+)"
# seg_map = {"LThigh": "L_THIGH", "RShank": "R_SHANK", "LFoot": "L_FOOT"}

# Normalize meta data column names from a defined pattern
def regex_meta_harmonize(col_name, pattern, seg_map, sens_map):
    match = re.search(pattern, col_name)
    if match:
        sensor, axis, segment = match.groups() # based on the pattern defined
        
        
        # 1) Convert segments
        std_segment = get_smart_segment(segment) 
        
        # 2) Convert sensors
        sens_map = {"Acc": "ACCEL", "Gyr": "GYRO", "Mag": "MAG"}
        std_sensor = sens_map.get(sensor, sensor.upper())
        
        # 3) Reassemble into your Gold Standard: SEGMENT_SENSOR_AXIS
        return f"{std_segment}_{std_sensor}_{axis.upper()}"
    
    return col_name # Return original if no match

def get_smart_segment(raw_segment):
    raw_segment = raw_segment.lower().replace("_", "")
    
    # 1. Determine Side
    side = ""
    if any(raw_segment.startswith(s) for s in ['l', 'left', 'L', 'LEFT']):
        side = "L"
    elif any(raw_segment.startswith(s) for s in ['r', 'right', 'R', "RIGHT"]):
        side = "R"
        
    # 2. Determine Anatomy 
    # You only need to define the base anatomical terms once
    #   'GROUND_TRUTH'  : ['list', 'of', 'potential', 'names']
    anatomy_keywords = {
        'THIGH'         : ['thigh', 'THIGH'],
        'SHANK'         : ['shank', 'SHANK', 'leg', 'LEG'],
        'FOOT'          : ['foot', 'FOOT'],
        'PELVIS'        : ['pelvis', 'PELVIS', 'sacrum', 'SACRUM'],
        'ARM_UPPER'     : ['arm_upper', 'ARM_UPPER', 'humerus', 'HUMERUS'],
        'ARM_LOWER'     : ['arm_lower', 'ARM_LOWER', 'radius', 'RADIUS']
    }
    
    found_anatomy = "UNKNOWN/MISSING"
    for key in anatomy_keywords:
        for term in anatomy_keywords[key]:
            if term in raw_segment:
                found_anatomy = key
                break
            
    return f"{side}_{found_anatomy}" if side else found_anatomy

# Testing the smart segment logic
print(get_smart_segment("LeftThigh")) # Output: L_THIGH
print(get_smart_segment("r_shank"))   # Output: R_SHANK
print(get_smart_segment("l_leg"))     # Output: L_SHANK
print(get_smart_segment("sacrum"))    # Output: PELVIS
print(get_smart_segment("PELVIS"))    # Output: PELVIS
print(get_smart_segment("HUMERUS"))   # Output: ARM_UPPER