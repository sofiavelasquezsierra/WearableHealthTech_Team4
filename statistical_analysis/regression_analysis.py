import pandas as pd
import statsmodels.formula.api as smf
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import pearsonr
import symmetry  
import gait        


def process_data(data_path, fs, dataset):
    results = []
    # Convert string path to a Path object
    base_path = Path(data_path)
    
    # Check if the directory exists to avoid empty loops
    if not base_path.exists():
        print(f"Error: The directory '{data_path}' does not exist.")
        return pd.DataFrame()

    files = list(base_path.rglob("*.csv"))
    print(f"Found {len(files)} files to process.")
    
    processed_count = 0
    skipped_count = 0


    

    for f in files:
        # case for the YARETA dataset
        if dataset == "YARETA" and "Gait" not in f.name:
            skipped_count += 1
            continue

        try:
            df = pd.read_csv(f)
            processed_count += 1
            
            # 2. Extract IMU Data (ISB Mappings)
            # Adjust these strings if your CSV headers are different
            # acc = df[['TRUNK_ACC_X', 'TRUNK_ACC_Y', 'TRUNK_ACC_Z']].values
            # gyro = df[['TRUNK_GYR_X', 'TRUNK_GYR_Y', 'TRUNK_GYR_Y']].values
            acc_l = df['L_FOOT_ACC_Y'].values
            acc_r = df['R_FOOT_ACC_Y'].values
            
            # 3. Call Modular Functions
            # sway_rms = trunk_sway.get_sway_metrics(acc, gyro, fs)
            gait_si = symmetry.calculate_gait_symmetry(acc_l, acc_r, fs)
            stride_cv = gait.estimate_stride_variability(acc_r, fs)            
            # 4. Identify Dataset (Fixing the NameError)
            # We initialize with a default to prevent NameError
            current_dataset = "Unknown" 
            if "NEWBEE" in str(f).upper():
                current_dataset = "NEWBEE"
            elif "YARETA" in str(f).upper():
                current_dataset = "YARETA"
            
            results.append({
                "file_name": f.name,
                "gait_symmetry": gait_si,
                "stride_variability": stride_cv,
                "dataset": current_dataset
            })
            
        except Exception as e:
            print(f"Skipping {f.name} due to error: {e}")
            
    print(f"\n--- Processed {processed_count} Gait files ---")
    print(f"--- Skipped {skipped_count} non-Gait files ---\n")
        
    return pd.DataFrame(results).dropna(subset=["stride_variability"])


def main():
    # 1. --- DATA PROCESSING ---
    path_newbee = r"/Users/emilyannaallendorf/Library/CloudStorage/Box-Box/WHT Datasets/02_coords_synced/NEWBEE"

    path_yareta = r"/Users/emilyannaallendorf/Library/CloudStorage/Box-Box/WHT Datasets/02_coords_synced/YARETA"
    
    df_newbee = process_data(path_newbee, 60.0, "NEWBEE")
    df_yareta = process_data(path_yareta, 256.0, "YARETA")
    df_combined = pd.concat([df_newbee, df_yareta], ignore_index=True)
    df_combined = df_combined.dropna(subset=['gait_symmetry', 'stride_variability'])


# 2. --- STATISTICS ---
    # Run models to get p-values for the bar chart
    p_newbee = smf.ols("stride_variability ~ gait_symmetry", data=df_newbee).fit().pvalues['gait_symmetry']
    p_yareta = smf.ols("stride_variability ~ gait_symmetry", data=df_yareta).fit().pvalues['gait_symmetry']
    p_combined = smf.ols("stride_variability ~ gait_symmetry + C(dataset)", data=df_combined).fit().pvalues['gait_symmetry']

    # 3. --- PLOT 1: P-VALUE BAR CHART ---
    plt.figure(figsize=(8, 5))
    datasets = ['NEWBEE', 'YARETA', 'COMBINED']
    p_values = [p_newbee, p_yareta, p_combined]
    
    colors = ['gray' if p > 0.05 else 'skyblue' for p in p_values]
    sns.barplot(x=datasets, y=p_values, palette=colors)
    plt.axhline(0.05, color='red', linestyle='--', label='Significance (0.05)')
    plt.ylabel('P-Value')
    plt.title('Statistical Significance by Dataset')
    plt.legend()
    plt.show()

    # 4. --- PLOT 2: SCATTER PLOT (SYM VS VAR) ---
    plt.figure(figsize=(8, 6))
    # Calculate R-value for the label
    r_val, _ = pearsonr(df_combined['gait_symmetry'], df_combined['stride_variability'])
    
    sns.scatterplot(data=df_combined, x='gait_symmetry', y='stride_variability', hue='dataset', alpha=0.6)
    sns.regplot(data=df_combined, x='gait_symmetry', y='stride_variability', scatter=False, color='black')
    
    plt.text(0.05, 0.95, f'Pearson r = {r_val:.2f}', transform=plt.gca().transAxes, fontsize=12, verticalalignment='top')
    plt.xlabel('Gait Symmetry Index (%)')
    plt.ylabel('Stride Variability (CV %)')
    plt.title('Relationship: Symmetry vs. Variability')
    plt.grid(True, alpha=0.3)
    plt.show()

if __name__ == "__main__":
    main()



# if __name__ == "__main__":
#     # Ensure your data folder name matches what is on your drive
#     path_NEWBEE = r"/Users/emilyannaallendorf/Library/CloudStorage/Box-Box/WHT Datasets/02_coords_synced/NEWBEE"
#     df_NEWBEE = process_data(path_NEWBEE, 60.0, "NEWBEE")
#     path_YARETA = r"/Users/emilyannaallendorf/Library/CloudStorage/Box-Box/WHT Datasets/02_coords_synced/YARETA"
#     df_YARETA = process_data(path_YARETA, 256.0, "YARETA")
#     # path_CAMARGO= r"/Users/emilyannaallendorf/Library/CloudStorage/Box-Box/WHT Datasets/02_coords_synced/CAMARGO"
#     # df_CAMARGO = process_data(path_CAMARGO, 200.0, "CAMARGO")
#     # df_results = df_CAMARGO

#     # path_HUGADB= r"/Users/emilyannaallendorf/Library/CloudStorage/Box-Box/WHT Datasets/02_coords_synced/HUGADB"
#     # df_HUGADB = process_data(path_HUGADB, 200.0, "HUGADB")
#     # df_results = df_NEWBEE
#     # df_results = df_YARETA


#     df_results = pd.concat([df_NEWBEE, df_YARETA], ignore_index=True)
    
#     if not df_results.empty:
#         print("\n--- Regression Results ---")
#         # C(dataset) treats the strings as categorical factors
#         model = smf.ols("stride_variability ~ gait_symmetry + C(dataset)", data=df_results).fit()
#         print(model.summary())
#         # r, p = pearsonr(df["gait_symmetry"], df["stride_variability"])
        
#     else:
#         print("No valid data processed. Check your CSV headers and file paths.")


# import pandas as pd
# from pathlib import Path
# import statsmodels.api as sm
# import statsmodels.formula.api as smf
# import numpy as np
# from ahrs.filters import Madgwick
# from scipy.spatial.transform import Rotation as R
# from scipy.signal import find_peaks

# data_dir = Path("data")

# csv_files = list(data_dir.rglob("*.csv"))

# print(len(csv_files))
# print(csv_files[:5])

# # def get_dataset_name(filepath):
# #     parts = filepath.parts
# #     if "NEWBEE" in parts:
# #         return "NEWBEE"
# #     elif "YARETA" in parts:
# #         return "YARETA"
# #     else:
# #         return "unknown"

# # all_data = []

# # for file in csv_files:
# #     df = pd.read_csv(file)

# #     df["dataset"] = get_dataset_name(file)
# #     df["source_file"] = str(file)

# #     all_data.append(df)

# # combined_df = pd.concat(all_data, ignore_index=True)


# trunk_cols = [c for c in df.columns if c.endswith("TRUNK")]
# trunk_acc_cols = [c for c in df.columns if c.startswith("ACC") and c.endswith("TRUNK")]
# acc_trunk = df[trunk_acc_cols].values

# def extract_features(df):

#     trunk_ml = df["ACC_X_TRUNK"]
#     trunk_sway = np.std(trunk_ml)

#     vertical_acc = df["ACC_Z_TRUNK"]
#     peaks, _ = find_peaks(vertical_acc, distance=40)

#     time = df["TIME"]
#     stride_times = np.diff(time.iloc[peaks])

#     stride_variability = np.std(stride_times) / np.mean(stride_times)

#     return trunk_sway, stride_variability

# results = []

# for file in Path("data").rglob("*.csv"):

#     df = pd.read_csv(file)

#     trunk_sway, stride_var = extract_features(df)

#     if "dataset_A" in str(file):
#         dataset = "A"
#     elif "dataset_B" in str(file):
#         dataset = "B"

#     results.append({
#         "dataset": dataset,
#         "file": file.name,
#         "trunk_sway": trunk_sway,
#         "stride_variability": stride_var
#     })


# # def run_regression(df):
# #     X = df["trunk_sway"]
# #     X = sm.add_constant(X)   # adds intercept
# #     y = df["stride_variability"]

# #     model = sm.OLS(y, X).fit()
# #     print(model.summary())
# #     return model


# # model = smf.ols(
# #     "stride_variability ~ trunk_sway + dataset",
# #     data=data
# # ).fit()

# # print(model.summary())

# # print("Dataset A")
# # model_A = run_regression(data[data["dataset"]=="A"])

# # print("Dataset B")
# # model_B = run_regression(data[data["dataset"]=="B"])

# # print("Combined")
# # model_combined = run_regression(data)

# # import matplotlib.pyplot as plt
# # import seaborn as sns

# # sns.lmplot(
# #     data=data,
# #     x="trunk_sway",
# #     y="stride_variability",
# #     hue="dataset"
# # )

# # plt.title("Trunk Sway vs Stride Variability")
# # plt.show()