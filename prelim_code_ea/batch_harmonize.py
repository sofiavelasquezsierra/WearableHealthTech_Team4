import os
import re
import pandas as pd
from pathlib import Path
import sys

# Import your existing script
# Assuming your script is named 'harmonize_columns.py' - adjust as needed
try:
    from regex_metadata_harmonizer import regex_meta_harmonize, get_sensor, get_segment
except ImportError:
    print("ERROR: Could not import harmonize_columns.py")
    print("Make sure your script file is in the same directory or in Python path")
    sys.exit(1)

# ============================================================================
# CONFIGURATION
# ============================================================================

INPUT_FOLDER = "/Users/emilyannaallendorf/Library/CloudStorage/Box-Box/WHT Datasets/00_raw/NEWBEE/multi_modal_gait_database/data_set_only_xsens"  # Root folder containing course folders (A, B, C)
OUTPUT_FOLDER = "/Users/emilyannaallendorf/Library/CloudStorage/Box-Box/WHT Datasets/01_columns_synced/NEWBEE/data_set" # Folder to save processed CSVs
SENSORS_TO_KEEP = ['ACC', 'GYR', 'MAG']  # Only keep these sensor types

# ============================================================================
# REGEX PATTERNS FOR DIFFERENT DATASET CONVENTIONS
# ============================================================================

# # Pattern 1: HuGaDB style (accelerometer_right_foot_x)
# pattern_hugadb = r"([a-z]+)_([a-z]+_[a-z]+)_([xyz])"
# order_hugadb = {
#     'sensor': [],
#     'segment': [],
#     'axis': []
# }

# # Pattern 2: Xsens raw sensor data (sensorFreeAcceleration_RightFoot_x)
# pattern_xsens_sensor = r"(sensor[a-zA-Z]+)_([a-zA-Z]+)_([a-zA-Z0-9]+)"
# order_xsens_sensor = {
#     'sensor': [],
#     'segment': [],
#     'axis': []
# }

# # Pattern 3: Xsens computed angular velocity (angularVelocity_RightFoot_x)
# pattern_xsens_angular = r"(angularVelocity[a-zA-Z]+)_([a-zA-Z]+)_([a-zA-Z0-9]+)"
# order_xsens_angular = {
#     'sensor': [],
#     'segment': [],
#     'axis': []
# }

# # ============================================================================
# # HELPER FUNCTIONS
# # ============================================================================

# def detect_dataset_type(columns):
#     """
#     Detect which dataset convention is being used based on column names.
#     Returns: 'hugadb', 'xsens', or 'unknown'
#     """
#     sample_cols = columns[:100]  # Check first 100 columns
    
#     # Check for HuGaDB pattern
#     hugadb_matches = sum(1 for col in sample_cols if re.search(pattern_hugadb, col))
    
#     # Check for Xsens pattern
#     xsens_matches = sum(1 for col in sample_cols 
#                        if re.search(pattern_xsens_sensor, col) or 
#                           re.search(pattern_xsens_angular, col))
    
#     if hugadb_matches > xsens_matches and hugadb_matches > 0:
#         return 'hugadb'
#     elif xsens_matches > 0:
#         return 'xsens'
#     else:
#         return 'mixed'  # Try both patterns


# def harmonize_column_name(col_name, pattern, order):
#     """
#     Wrapper around your regex_meta_harmonize function.
#     Returns the harmonized column name or None if not ACC/GYR/MAG.
#     """
#     # Make a fresh copy of order dict for this call
#     order_copy = {key: [] for key in order.keys()}
    
#     try:
#         # Call your existing function
#         result = regex_meta_harmonize(col_name, pattern, order_copy)
        
#         # Check if result contains ACC, GYR, or MAG
#         if result and not result.startswith("UNKNOWN"):
#             # Extract sensor type from result (format: SEGMENT_SENSOR_AXIS)
#             parts = result.split('_')
#             if len(parts) >= 2:
#                 sensor_type = parts[-2]  # Second to last part is sensor
#                 if sensor_type in SENSORS_TO_KEEP:
#                     return result
#     except Exception as e:
#         # If there's any error with this column, just skip it
#         pass
    
#     return None


# def try_all_patterns(col_name):
#     """
#     Try all available patterns to harmonize a column name.
#     Returns harmonized name or None if no pattern matches.
#     """
#     # Try HuGaDB pattern
#     result = harmonize_column_name(col_name, pattern_hugadb, order_hugadb)
#     if result:
#         return result
    
#     # Try Xsens sensor pattern
#     result = harmonize_column_name(col_name, pattern_xsens_sensor, order_xsens_sensor)
#     if result:
#         return result
    
#     # Try Xsens angular velocity pattern
#     result = harmonize_column_name(col_name, pattern_xsens_angular, order_xsens_angular)
#     if result:
#         return result
    
#     return None


# def process_csv(file_path, course, participant_id, output_base_dir):
#     """
#     Process a single CSV file: filter and rename columns to standard format.
    
#     Args:
#         file_path: Path to input CSV file
#         course: Course identifier (A, B, or C)
#         participant_id: Participant ID (e.g., id01)
#         output_base_dir: Base output directory
    
#     Returns:
#         Dictionary with processing statistics
#     """
#     print(f"\n  Processing: {course}/{participant_id}/{file_path.name}")
    
#     try:
#         # Read CSV
#         df = pd.read_csv(file_path)
#         original_cols = df.columns.tolist()
#         original_count = len(original_cols)
        
#         # Detect dataset type
#         dataset_type = detect_dataset_type(original_cols)
#         print(f"    Detected type: {dataset_type}")
        
#         # Prepare column mapping
#         column_mapping = {}
#         skipped_columns = []
        
#         if dataset_type == 'hugadb':
#             # Use HuGaDB pattern
#             for col in original_cols:
#                 new_name = harmonize_column_name(col, pattern_hugadb, order_hugadb)
#                 if new_name:
#                     column_mapping[col] = new_name
#                 else:
#                     skipped_columns.append(col)
        
#         elif dataset_type == 'xsens':
#             # Try both Xsens patterns
#             for col in original_cols:
#                 # Try sensor pattern first
#                 new_name = harmonize_column_name(col, pattern_xsens_sensor, order_xsens_sensor)
                
#                 # If that didn't work, try angular velocity pattern
#                 if not new_name:
#                     new_name = harmonize_column_name(col, pattern_xsens_angular, order_xsens_angular)
                
#                 if new_name:
#                     column_mapping[col] = new_name
#                 else:
#                     skipped_columns.append(col)
        
#         else:  # 'mixed' or 'unknown' - try all patterns
#             for col in original_cols:
#                 new_name = try_all_patterns(col)
#                 if new_name:
#                     column_mapping[col] = new_name
#                 else:
#                     skipped_columns.append(col)
        
#         # Even if no columns matched, we still process the file
#         if not column_mapping:
#             print(f"    WARNING: No ACC/GYR/MAG columns found in this file")
#             print(f"    File will be skipped (no relevant sensor data)")
#             return {
#                 'file': file_path.name,
#                 'course': course,
#                 'participant': participant_id,
#                 'status': 'no_sensor_data',
#                 'original_columns': original_count,
#                 'kept_columns': 0,
#                 'skipped_columns': original_count
#             }
        
#         # Filter to only mapped columns
#         df_filtered = df[list(column_mapping.keys())].copy()
        
#         # Rename columns
#         df_filtered.rename(columns=column_mapping, inplace=True)
        
#         # Handle duplicate column names by keeping first occurrence
#         if df_filtered.columns.duplicated().any():
#             print(f"    WARNING: Duplicate column names detected. Keeping first occurrence.")
#             df_filtered = df_filtered.loc[:, ~df_filtered.columns.duplicated(keep='first')]
        
#         # Create output directory structure: output_base/course/participant_id/
#         output_dir = output_base_dir / course / participant_id
#         output_dir.mkdir(parents=True, exist_ok=True)
        
#         # Save processed file
#         output_path = output_dir / file_path.name
#         df_filtered.to_csv(output_path, index=False)
        
#         kept_count = len(df_filtered.columns)
#         skipped_count = len(skipped_columns)
        
#         print(f"    SUCCESS: Kept {kept_count}/{original_count} columns (skipped {skipped_count})")
#         print(f"    Saved to: {output_path}")
        
#         return {
#             'file': file_path.name,
#             'course': course,
#             'participant': participant_id,
#             'status': 'success',
#             'original_columns': original_count,
#             'kept_columns': kept_count,
#             'skipped_columns': skipped_count,
#             'column_mapping': column_mapping,
#             'skipped_column_names': skipped_columns
#         }
    
#     except Exception as e:
#         print(f"    ERROR: {str(e)}")
#         return {
#             'file': file_path.name,
#             'course': course,
#             'participant': participant_id,
#             'status': 'error',
#             'error': str(e)
#         }


# def process_newbee_structure(input_folder, output_folder):
#     """
#     Process NEWBEE folder structure: NEWBEE/[A,B,C]/[idXX]/file.csv
    
#     Args:
#         input_folder: Path to NEWBEE root folder
#         output_folder: Path to output root folder
#     """
#     input_path = Path(input_folder)
#     output_path = Path(output_folder)
    
#     # Create output directory if it doesn't exist
#     output_path.mkdir(parents=True, exist_ok=True)
    
#     if not input_path.exists():
#         print(f"ERROR: Input folder does not exist: {input_folder}")
#         return
    
#     # Find all course folders (A, B, C)
#     course_folders = [f for f in input_path.iterdir() if f.is_dir() and f.name in ['courseA', 'courseB', 'courseC']]
    
#     if not course_folders:
#         print(f"ERROR: No course folders (A, B, C) found in {input_folder}")
#         return
    
#     print(f"Found {len(course_folders)} course folder(s): {[f.name for f in course_folders]}")
#     print("=" * 70)
    
#     # Track all results
#     all_results = []
#     total_files = 0
    
#     # Process each course
#     for course_folder in sorted(course_folders):
#         course = course_folder.name
#         print(f"\nProcessing Course: {course}")
#         print("-" * 70)
        
#         # Find all participant folders (idXX)
#         participant_folders = [f for f in course_folder.iterdir() 
#                              if f.is_dir() and f.name.startswith('id')]
        
#         if not participant_folders:
#             print(f"  WARNING: No participant folders found in course {course}")
#             continue
        
#         print(f"  Found {len(participant_folders)} participant(s)")
        
#         # Process each participant
#         for participant_folder in sorted(participant_folders):
#             participant_id = participant_folder.name
            
#             # Find all CSV files in participant folder
#             csv_files = list(participant_folder.glob("*.csv"))
            
#             if not csv_files:
#                 print(f"    WARNING: No CSV files found for {course}/{participant_id}")
#                 continue
            
#             total_files += len(csv_files)
            
#             # Process each CSV file
#             for csv_file in csv_files:
#                 result = process_csv(csv_file, course, participant_id, output_path)
#                 all_results.append(result)
    
#     # Print summary
#     print("\n" + "=" * 70)
#     print("PROCESSING SUMMARY")
#     print("=" * 70)
    
#     successful = [r for r in all_results if r['status'] == 'success']
#     no_sensor = [r for r in all_results if r['status'] == 'no_sensor_data']
#     errors = [r for r in all_results if r['status'] == 'error']
    
#     print(f"\nTotal files found: {total_files}")
#     print(f"  Successfully processed: {len(successful)}")
#     print(f"  No sensor data: {len(no_sensor)}")
#     print(f"  Errors: {len(errors)}")
    
#     if successful:
#         total_original = sum(r['original_columns'] for r in successful)
#         total_kept = sum(r['kept_columns'] for r in successful)
#         total_skipped = sum(r['skipped_columns'] for r in successful)
#         print(f"\nColumn statistics (successful files only):")
#         print(f"  Total original columns: {total_original}")
#         print(f"  Total kept columns (ACC/GYR/MAG): {total_kept}")
#         print(f"  Total skipped columns: {total_skipped}")
#         if total_original > 0:
#             print(f"  Kept: {100 * total_kept/total_original:.1f}%")
#             print(f"  Skipped: {100 * total_skipped/total_original:.1f}%")
    
#     # Group by course
#     print("\nBreakdown by course:")
#     for course in ['A', 'B', 'C']:
#         course_results = [r for r in successful if r['course'] == course]
#         if course_results:
#             print(f"  Course {course}: {len(course_results)} files processed")
    
#     if no_sensor:
#         print(f"\nFiles with no sensor data:")
#         for r in no_sensor:
#             print(f"  - {r['course']}/{r['participant']}/{r['file']}")
    
#     if errors:
#         print(f"\nErrors:")
#         for r in errors:
#             print(f"  - {r['course']}/{r['participant']}/{r['file']}: {r['error']}")
    
#     # Save detailed report
#     report_path = output_path / "processing_report.txt"
#     with open(report_path, 'w') as f:
#         f.write("NEWBEE PROCESSING REPORT\n")
#         f.write("=" * 70 + "\n\n")
        
#         # Group by course and participant
#         for course in ['A', 'B', 'C']:
#             course_results = [r for r in all_results if r.get('course') == course]
#             if not course_results:
#                 continue
            
#             f.write(f"\nCOURSE {course}\n")
#             f.write("-" * 70 + "\n")
            
#             # Group by participant
#             participants = sorted(set(r['participant'] for r in course_results))
#             for participant in participants:
#                 participant_results = [r for r in course_results if r['participant'] == participant]
                
#                 f.write(f"\n  Participant: {participant}\n")
                
#                 for result in participant_results:
#                     f.write(f"    File: {result['file']}\n")
#                     f.write(f"    Status: {result['status']}\n")
                    
#                     if result['status'] == 'success':
#                         f.write(f"    Original columns: {result['original_columns']}\n")
#                         f.write(f"    Kept columns: {result['kept_columns']}\n")
#                         f.write(f"    Skipped columns: {result['skipped_columns']}\n")
                        
#                         if result['kept_columns'] > 0:
#                             f.write(f"    Column mapping:\n")
#                             for old, new in sorted(result['column_mapping'].items()):
#                                 f.write(f"      {old} -> {new}\n")
                        
#                         if result.get('skipped_column_names'):
#                             f.write(f"    Skipped column names (first 10):\n")
#                             for col in result['skipped_column_names'][:10]:
#                                 f.write(f"      {col}\n")
#                             if len(result['skipped_column_names']) > 10:
#                                 f.write(f"      ... and {len(result['skipped_column_names']) - 10} more\n")
                    
#                     elif result['status'] == 'no_sensor_data':
#                         f.write(f"    No ACC/GYR/MAG columns found\n")
                    
#                     elif result['status'] == 'error':
#                         f.write(f"    Error: {result['error']}\n")
                    
#                     f.write("\n")
    
#     print(f"\nDetailed report saved to: {report_path}")


# # ============================================================================
# # MAIN EXECUTION
# # ============================================================================

# if __name__ == "__main__":
#     # Allow command line arguments
#     if len(sys.argv) >= 2:
#         INPUT_FOLDER = sys.argv[1]
#     if len(sys.argv) >= 3:
#         OUTPUT_FOLDER = sys.argv[2]
    
#     print("=" * 70)
#     print("NEWBEE CSV HARMONIZATION SCRIPT")
#     print("=" * 70)
#     print(f"Input folder: {INPUT_FOLDER}")
#     print(f"Output folder: {OUTPUT_FOLDER}")
#     print(f"Keeping only: {', '.join(SENSORS_TO_KEEP)}")
#     print(f"Expected structure: {INPUT_FOLDER}/[A,B,C]/[idXX]/*.csv")
#     print("=" * 70)
    
#     process_newbee_structure(INPUT_FOLDER, OUTPUT_FOLDER)
    
#     print("\n" + "=" * 70)
#     print("PROCESSING COMPLETE")
#     print("=" * 70)

DEBUG_MODE = False  # Set to True to see detailed pattern matching

# ============================================================================
# REGEX PATTERNS FOR DIFFERENT DATASET CONVENTIONS
# ============================================================================

# Pattern 1: HuGaDB style (accelerometer_right_foot_x)
pattern_hugadb = r"([a-z]+)_([a-z]+_[a-z]+)_([xyz])"
order_hugadb = {
    'sensor': [],
    'segment': [],
    'axis': []
}

# Pattern 2: Xsens raw sensor data (sensorFreeAcceleration_RightFoot_x)
pattern_xsens_sensor = r"(sensor[a-zA-Z]+)_([a-zA-Z]+)_([a-z0-9]+)"
order_xsens_sensor = {
    'sensor': [],
    'segment': [],
    'axis': []
}

# Pattern 3: Xsens computed angular velocity (angularVelocity_RightFoot_x)
pattern_xsens_angular = r"(angularVelocity)_([a-zA-Z]+)_([xyz])"
order_xsens_angular = {
    'sensor': [],
    'segment': [],
    'axis': []
}

# Pattern 4: Standard format without underscore in segment (acceleration_RightFoot_x)
pattern_standard = r"([a-z]+)_([a-zA-Z]+)_([xyz])"
order_standard = {
    'sensor': [],
    'segment': [],
    'axis': []
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def detect_dataset_type(columns):
    """
    Detect which dataset convention is being used based on column names.
    Returns: 'hugadb', 'xsens', 'standard', or 'mixed'
    """
    sample_cols = columns[:100]  # Check first 100 columns
    
    # Check for HuGaDB pattern (sensor_side_bodypart_axis)
    hugadb_matches = sum(1 for col in sample_cols if re.search(pattern_hugadb, col))
    
    # Check for Xsens pattern (sensorType or angularVelocity prefix)
    xsens_matches = sum(1 for col in sample_cols 
                       if re.search(pattern_xsens_sensor, col) or 
                          re.search(pattern_xsens_angular, col))
    
    # Check for standard pattern (lowercase_CamelCase_axis)
    standard_matches = sum(1 for col in sample_cols if re.search(pattern_standard, col))
    
    if DEBUG_MODE:
        print(f"    Pattern detection: HuGaDB={hugadb_matches}, Xsens={xsens_matches}, Standard={standard_matches}")
    
    if xsens_matches > 5:  # Strong indicator
        return 'xsens'
    elif hugadb_matches > 5:
        return 'hugadb'
    elif standard_matches > 5:
        return 'standard'
    else:
        return 'mixed'  # Try all patterns


def harmonize_column_name(col_name, pattern, order):
    """
    Wrapper around your regex_meta_harmonize function.
    Returns the harmonized column name or None if not ACC/GYR/MAG.
    """
    # Make a fresh copy of order dict for this call
    order_copy = {key: [] for key in order.keys()}
    
    try:
        # Call your existing function
        result = regex_meta_harmonize(col_name, pattern, order_copy)
        
        # Check if result contains ACC, GYR, or MAG
        if result and not result.startswith("UNKNOWN"):
            # Extract sensor type from result (format: SEGMENT_SENSOR_AXIS)
            parts = result.split('_')
            if len(parts) >= 2:
                sensor_type = parts[-2]  # Second to last part is sensor
                if sensor_type in SENSORS_TO_KEEP:
                    return result
    except Exception as e:
        # If there's any error with this column, just skip it
        if DEBUG_MODE:
            print(f"      Error harmonizing '{col_name}': {e}")
    
    return None


def try_all_patterns(col_name):
    """
    Try all available patterns to harmonize a column name.
    Returns harmonized name or None if no pattern matches.
    """
    # Try HuGaDB pattern
    result = harmonize_column_name(col_name, pattern_hugadb, order_hugadb)
    if result:
        if DEBUG_MODE:
            print(f"      {col_name} -> {result} (HuGaDB pattern)")
        return result
    
    # Try Xsens sensor pattern
    result = harmonize_column_name(col_name, pattern_xsens_sensor, order_xsens_sensor)
    if result:
        if DEBUG_MODE:
            print(f"      {col_name} -> {result} (Xsens sensor pattern)")
        return result
    
    # Try Xsens angular velocity pattern
    result = harmonize_column_name(col_name, pattern_xsens_angular, order_xsens_angular)
    if result:
        if DEBUG_MODE:
            print(f"      {col_name} -> {result} (Xsens angular pattern)")
        return result
    
    # Try standard pattern
    result = harmonize_column_name(col_name, pattern_standard, order_standard)
    if result:
        if DEBUG_MODE:
            print(f"      {col_name} -> {result} (Standard pattern)")
        return result
    
    return None


def show_sample_columns(columns, n=10):
    """Show first n columns for debugging"""
    print(f"    Sample columns (first {n}):")
    for col in columns[:n]:
        print(f"      - {col}")


def process_csv(file_path, course, participant_id, output_base_dir):
    """
    Process a single CSV file: filter and rename columns to standard format.
    
    Args:
        file_path: Path to input CSV file
        course: Course identifier (A, B, or C)
        participant_id: Participant ID (e.g., id01)
        output_base_dir: Base output directory
    
    Returns:
        Dictionary with processing statistics
    """
    print(f"\n  Processing: {course}/{participant_id}/{file_path.name}")
    
    try:
        # Read CSV
        df = pd.read_csv(file_path)
        original_cols = df.columns.tolist()
        original_count = len(original_cols)
        
        print(f"    Total columns: {original_count}")
        
        # Show sample columns for debugging
        if DEBUG_MODE:
            show_sample_columns(original_cols, n=15)
        
        # Detect dataset type
        dataset_type = detect_dataset_type(original_cols)
        print(f"    Detected type: {dataset_type}")
        
        # Prepare column mapping
        column_mapping = {}
        skipped_columns = []
        
        # Process based on dataset type
        if dataset_type == 'hugadb':
            print(f"    Using HuGaDB pattern...")
            for col in original_cols:
                new_name = harmonize_column_name(col, pattern_hugadb, order_hugadb)
                if new_name:
                    column_mapping[col] = new_name
                else:
                    skipped_columns.append(col)
        
        elif dataset_type == 'xsens':
            print(f"    Using Xsens patterns...")
            for col in original_cols:
                # Try sensor pattern first
                new_name = harmonize_column_name(col, pattern_xsens_sensor, order_xsens_sensor)
                
                # If that didn't work, try angular velocity pattern
                if not new_name:
                    new_name = harmonize_column_name(col, pattern_xsens_angular, order_xsens_angular)
                
                if new_name:
                    column_mapping[col] = new_name
                else:
                    skipped_columns.append(col)
        
        elif dataset_type == 'standard':
            print(f"    Using Standard pattern...")
            for col in original_cols:
                new_name = harmonize_column_name(col, pattern_standard, order_standard)
                if new_name:
                    column_mapping[col] = new_name
                else:
                    skipped_columns.append(col)
        
        else:  # 'mixed' - try all patterns
            print(f"    Trying all patterns on each column...")
            if DEBUG_MODE:
                print(f"    First 5 column attempts:")
            
            for i, col in enumerate(original_cols):
                if DEBUG_MODE and i < 5:
                    print(f"      Attempting: {col}")
                
                new_name = try_all_patterns(col)
                if new_name:
                    column_mapping[col] = new_name
                else:
                    skipped_columns.append(col)
                    if DEBUG_MODE and i < 5:
                        print(f"        -> No match")
        
        # Check results
        kept_count = len(column_mapping)
        skipped_count = len(skipped_columns)
        
        print(f"    Matched {kept_count} columns, skipped {skipped_count} columns")
        
        # If no columns matched, return early
        if not column_mapping:
            print(f"    WARNING: No ACC/GYR/MAG columns found in this file")
            print(f"    File will be skipped (no relevant sensor data)")
            
            if DEBUG_MODE:
                print(f"    Sample skipped columns:")
                for col in skipped_columns[:10]:
                    print(f"      - {col}")
            
            return {
                'file': file_path.name,
                'course': course,
                'participant': participant_id,
                'status': 'no_sensor_data',
                'original_columns': original_count,
                'kept_columns': 0,
                'skipped_columns': original_count
            }
        
        # Filter to only mapped columns
        df_filtered = df[list(column_mapping.keys())].copy()
        
        # Rename columns
        df_filtered.rename(columns=column_mapping, inplace=True)
        
        # Handle duplicate column names by keeping first occurrence
        if df_filtered.columns.duplicated().any():
            print(f"    WARNING: Duplicate column names detected. Keeping first occurrence.")
            df_filtered = df_filtered.loc[:, ~df_filtered.columns.duplicated(keep='first')]
        
        # Create output directory structure: output_base/course/participant_id/
        output_dir = output_base_dir / course / participant_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save processed file
        output_path = output_dir / file_path.name
        df_filtered.to_csv(output_path, index=False)
        
        kept_count = len(df_filtered.columns)
        
        print(f"    SUCCESS: Kept {kept_count}/{original_count} columns (skipped {skipped_count})")
        print(f"    Saved to: {output_path}")
        
        if DEBUG_MODE:
            print(f"    Sample kept columns:")
            for col in list(df_filtered.columns)[:5]:
                print(f"      - {col}")
        
        return {
            'file': file_path.name,
            'course': course,
            'participant': participant_id,
            'status': 'success',
            'original_columns': original_count,
            'kept_columns': kept_count,
            'skipped_columns': skipped_count,
            'column_mapping': column_mapping,
            'skipped_column_names': skipped_columns
        }
    
    except Exception as e:
        print(f"    ERROR: {str(e)}")
        import traceback
        if DEBUG_MODE:
            traceback.print_exc()
        return {
            'file': file_path.name,
            'course': course,
            'participant': participant_id,
            'status': 'error',
            'error': str(e)
        }


def process_newbee_structure(input_folder, output_folder):
    """
    Process NEWBEE folder structure: NEWBEE/[A,B,C]/[idXX]/file.csv
    
    Args:
        input_folder: Path to NEWBEE root folder
        output_folder: Path to output root folder
    """
    input_path = Path(input_folder)
    output_path = Path(output_folder)
    
    # Create output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)
    
    if not input_path.exists():
        print(f"ERROR: Input folder does not exist: {input_folder}")
        return
    
    # Find all course folders (A, B, C)
    course_folders = [f for f in input_path.iterdir() if f.is_dir() and f.name in ['courseA', 'courseB', 'courseC']]
    
    if not course_folders:
        print(f"ERROR: No course folders (A, B, C) found in {input_folder}")
        return
    
    print(f"Found {len(course_folders)} course folder(s): {[f.name for f in course_folders]}")
    print("=" * 70)
    
    # Track all results
    all_results = []
    total_files = 0
    
    # Process each course
    for course_folder in sorted(course_folders):
        course = course_folder.name
        print(f"\nProcessing Course: {course}")
        print("-" * 70)
        
        # Find all participant folders (idXX)
        participant_folders = [f for f in course_folder.iterdir() 
                             if f.is_dir() and f.name.startswith('id')]
        
        if not participant_folders:
            print(f"  WARNING: No participant folders found in course {course}")
            continue
        
        print(f"  Found {len(participant_folders)} participant(s)")
        
        # Process each participant
        for participant_folder in sorted(participant_folders):
            participant_id = participant_folder.name
            
            # Find all CSV files in participant folder
            csv_files = list(participant_folder.glob("*.csv"))
            
            if not csv_files:
                print(f"    WARNING: No CSV files found for {course}/{participant_id}")
                continue
            
            total_files += len(csv_files)
            
            # Process each CSV file
            for csv_file in csv_files:
                result = process_csv(csv_file, course, participant_id, output_path)
                all_results.append(result)
    
    # Print summary
    print("\n" + "=" * 70)
    print("PROCESSING SUMMARY")
    print("=" * 70)
    
    successful = [r for r in all_results if r['status'] == 'success']
    no_sensor = [r for r in all_results if r['status'] == 'no_sensor_data']
    errors = [r for r in all_results if r['status'] == 'error']
    
    print(f"\nTotal files found: {total_files}")
    print(f"  Successfully processed: {len(successful)}")
    print(f"  No sensor data: {len(no_sensor)}")
    print(f"  Errors: {len(errors)}")
    
    if successful:
        total_original = sum(r['original_columns'] for r in successful)
        total_kept = sum(r['kept_columns'] for r in successful)
        total_skipped = sum(r['skipped_columns'] for r in successful)
        print(f"\nColumn statistics (successful files only):")
        print(f"  Total original columns: {total_original}")
        print(f"  Total kept columns (ACC/GYR/MAG): {total_kept}")
        print(f"  Total skipped columns: {total_skipped}")
        if total_original > 0:
            print(f"  Kept: {100 * total_kept/total_original:.1f}%")
            print(f"  Skipped: {100 * total_skipped/total_original:.1f}%")
    
    # Group by course
    print("\nBreakdown by course:")
    for course in ['A', 'B', 'C']:
        course_results = [r for r in successful if r['course'] == course]
        if course_results:
            print(f"  Course {course}: {len(course_results)} files processed")
    
    if no_sensor:
        print(f"\nFiles with no sensor data ({len(no_sensor)} files):")
        for r in no_sensor[:5]:  # Show first 5
            print(f"  - {r['course']}/{r['participant']}/{r['file']}")
        if len(no_sensor) > 5:
            print(f"  ... and {len(no_sensor) - 5} more")
    
    if errors:
        print(f"\nErrors:")
        for r in errors:
            print(f"  - {r['course']}/{r['participant']}/{r['file']}: {r['error']}")
    
    # Save detailed report
    report_path = output_path / "processing_report.txt"
    with open(report_path, 'w') as f:
        f.write("NEWBEE PROCESSING REPORT\n")
        f.write("=" * 70 + "\n\n")
        
        # Group by course and participant
        for course in ['A', 'B', 'C']:
            course_results = [r for r in all_results if r.get('course') == course]
            if not course_results:
                continue
            
            f.write(f"\nCOURSE {course}\n")
            f.write("-" * 70 + "\n")
            
            # Group by participant
            participants = sorted(set(r['participant'] for r in course_results))
            for participant in participants:
                participant_results = [r for r in course_results if r['participant'] == participant]
                
                f.write(f"\n  Participant: {participant}\n")
                
                for result in participant_results:
                    f.write(f"    File: {result['file']}\n")
                    f.write(f"    Status: {result['status']}\n")
                    
                    if result['status'] == 'success':
                        f.write(f"    Original columns: {result['original_columns']}\n")
                        f.write(f"    Kept columns: {result['kept_columns']}\n")
                        f.write(f"    Skipped columns: {result['skipped_columns']}\n")
                        
                        if result['kept_columns'] > 0:
                            f.write(f"    Column mapping:\n")
                            for old, new in sorted(result['column_mapping'].items()):
                                f.write(f"      {old} -> {new}\n")
                        
                        if result.get('skipped_column_names'):
                            f.write(f"    Skipped column names (first 10):\n")
                            for col in result['skipped_column_names'][:10]:
                                f.write(f"      {col}\n")
                            if len(result['skipped_column_names']) > 10:
                                f.write(f"      ... and {len(result['skipped_column_names']) - 10} more\n")
                    
                    elif result['status'] == 'no_sensor_data':
                        f.write(f"    No ACC/GYR/MAG columns found\n")
                    
                    elif result['status'] == 'error':
                        f.write(f"    Error: {result['error']}\n")
                    
                    f.write("\n")
    
    print(f"\nDetailed report saved to: {report_path}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Allow command line arguments
    if len(sys.argv) >= 2:
        INPUT_FOLDER = sys.argv[1]
    if len(sys.argv) >= 3:
        OUTPUT_FOLDER = sys.argv[2]
    
    print("=" * 70)
    print("NEWBEE CSV HARMONIZATION SCRIPT")
    print("=" * 70)
    print(f"Input folder: {INPUT_FOLDER}")
    print(f"Output folder: {OUTPUT_FOLDER}")
    print(f"Keeping only: {', '.join(SENSORS_TO_KEEP)}")
    print(f"Debug mode: {DEBUG_MODE}")
    print(f"Expected structure: {INPUT_FOLDER}/[A,B,C]/[idXX]/*.csv")
    print("=" * 70)
    
    process_newbee_structure(INPUT_FOLDER, OUTPUT_FOLDER)
    
    print("\n" + "=" * 70)
    print("PROCESSING COMPLETE")
    print("=" * 70)