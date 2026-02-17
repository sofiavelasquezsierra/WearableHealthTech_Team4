import re
# import pandas as pd

# Construct a pattern based on the convention followed by the dataset you are trying to harmonize
# Example Pattern: matches "Acc_X_LThigh" or "Gyr_Y_RShank"
# Group 1: Sensor (Acc/Gyr), Group 2: Axis (X/Y/Z), Group 3: Segment (LThigh/RShank)
# also give the order of the information that is found in dict format
patternEx = r"([a-zA-Z]+)_([XYZ])_([a-zA-Z]+)"
orderEx = ['sensor', 'axis', 'segment']
patternHuGa = r"([a-z]+)_([a-z]+_[a-z]+)_([xyz])"
orderHuGa = {'sensor' : [], 
             'segment': [],
             'axis'   : []}

# Normalize meta data column names from a defined pattern
def regex_meta_harmonize(col_name, pattern, order):
    match = re.search(pattern, col_name)
    if match:
        sub1, sub2, sub3 = match.groups() # based on the pattern defined
        sub = [sub1, sub2, sub3]
        i = 0
        for key in order:
            order[key] = sub[i]
            i = i + 1
        
        # 1) Convert segments
        std_segment = get_segment(order['segment'])
        
        # 2) Convert sensors
        std_sensor = get_sensor(order['sensor'])
        
        # 3) Reassemble into your Gold Standard: SEGMENT_SENSOR_AXIS
        axis = order['axis']
        return f"{std_segment}_{std_sensor}_{axis.upper()}"

    return f"UNKNOWN: {col_name}"

def get_sensor(raw_sensor):
    sensor_keywords = {
        'GYR' : ['gyr', 'gyroscope'],
        'ACC' : ['acc', 'acceleration'],
        'MAG' : ['mag', 'magnometer']
    }

    found_sensor = "NONE"
    for key in sensor_keywords:
        for term in sensor_keywords[key]:
            if term in raw_sensor:
                found_sensor = key
                break

    return found_sensor


def get_segment(raw_segment):
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
        # Lower Body
        'THIGH'         : ['thigh', 'THIGH', 'upper_leg', 'upperLeg', 'UPPER_LEG'],
        'SHANK'         : ['shank', 'SHANK', 'leg', 'LEG', 'lower_leg', 'lowerLeg', 'LOWER_LEG', 'shin', 'SHIN'],
        'PELVIS'        : ['pelvis', 'PELVIS', 'sacrum', 'SACRUM'],
        'ANKLE'         : ['ankle', 'ANKLE'],
        'FOOT'          : ['foot', 'FOOT'],
        
        # Upper Body
        'STERNUM'       : ['sternum', 'STERNUM', 'chest', 'CHEST'],
        'ARM_UPPER'     : ['upperarm', 'UpperArm','arm_upper', 'ARM_UPPER', 'humerus', 'HUMERUS'],
        'ARM_LOWER'     : ['arm_lower', 'ARM_LOWER', 'armLower', 'radius', 'RADIUS', 'forearm', 'FOREARM', 'ForeArm', 'LowerArm'],
        'SHOULDER'      : ['shoulder', 'SHOULDER'],
        'HAND'          : ['hand', 'HAND'],
        'HEAD'          : ['head', 'HEAD'],
        'NECK'          : ['NECK', 'neck', 'Neck']
    }
    
    found_anatomy = "NONE"
    for key in anatomy_keywords:
        for term in anatomy_keywords[key]:
            if term in raw_segment:
                found_anatomy = key
                break
            
    return f"{side}_{found_anatomy}" if side else found_anatomy

# Testing the smart segment logic
print(regex_meta_harmonize("accelerometer_right_foot_x", patternHuGa, orderHuGa))
print(regex_meta_harmonize("accelerometer_right_shin_x", patternHuGa, orderHuGa))
print(regex_meta_harmonize("gyroscope_left_thigh_z", patternHuGa, orderHuGa))
print(regex_meta_harmonize("EMG_right", patternHuGa, orderHuGa))   
