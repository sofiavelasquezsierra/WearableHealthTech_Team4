import numpy as np
from scipy.signal import find_peaks

def calculate_gait_symmetry(acc_l, acc_r, fs):
    # 1. Force 1D and remove Gravity/Offset
    # Subtracting the median centers the 'quiet' parts of the signal at 0.0
    acc_l_clean = np.asarray(acc_l).flatten() - np.median(acc_l)
    acc_r_clean = np.asarray(acc_r).flatten() - np.median(acc_r)

    # 2. Relaxed Peak Detection
    # Since we are at zero, a prominence of 0.15 is very safe for heel strikes
    dist = int(fs * 0.35) # Minimum 0.35s between steps
    peaks_l, _ = find_peaks(acc_l_clean, distance=dist, prominence=0.15)
    peaks_r, _ = find_peaks(acc_r_clean, distance=dist, prominence=0.15)

    # 3. Diagnostic check (helps you find why files skip)
    if len(peaks_l) < 3 or len(peaks_r) < 3:
        return np.nan

    # 4. Calculate Mean Peak Intensity
    # We use the absolute value of the peaks from the 0-baseline
    mean_peak_l = np.mean(np.abs(acc_l_clean[peaks_l]))
    mean_peak_r = np.mean(np.abs(acc_r_clean[peaks_r]))

    # 5. Symmetry Index (SI) Formula
    # SI = (|L - R| / (0.5 * (L + R))) * 100
    diff = abs(mean_peak_l - mean_peak_r)
    avg = 0.5 * (mean_peak_l + mean_peak_r)
    
    if avg == 0: return np.nan
    
    return (diff / avg) * 100