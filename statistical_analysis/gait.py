import numpy as np
from scipy.signal import find_peaks

def estimate_stride_variability(vertical_acc, fs):
    """
    Calculates variability using a manual frequency (fs).
    """
    # Create time based on row count and frequency
    time_simulated = np.arange(len(vertical_acc)) / fs
    
    # Find peaks in vertical acceleration (ISB Y-axis)
    # distance = 0.4s * fs (e.g., 24 samples at 60Hz)
    peaks, _ = find_peaks(vertical_acc, distance=int(fs * 0.4), prominence=0.5)
    
    if len(peaks) < 3:
        return np.nan
        
    stride_times = np.diff(time_simulated[peaks])
    cv = (np.std(stride_times) / np.mean(stride_times)) * 100
    return cv