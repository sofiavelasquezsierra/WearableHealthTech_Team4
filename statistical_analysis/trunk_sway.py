import numpy as np

class TrunkSwayKalman:
    def __init__(self, fs):
        self.T = 1.0 / fs
        self.X = np.array([0.0, 0.0])  # [tilt_angle, gyro_drift]
        self.P = np.eye(2)
        # Tuning parameters (Q = process noise, R = sensor noise)
        self.Q = np.array([[0.001, 0], [0, 0.003]])
        self.R = 0.01

    def calculate_observation_phi(self, ax, ay, az):
        """
        Robust implementation of Equation 8 with clipping to prevent NaN errors.
        """
        try:
            # 1. Scale by gravity (ensure we are working with g-units)
            # If your data is already in m/s^2, divide by 9.81. If in Gs, remove / 9.81.
            gx, gy, gz = ax / 9.81, ay / 9.81, az / 9.81
            
            # 2. Clip for inner arcsin: defined only for [-1, 1]
            ax_clipped = np.clip(gx, -1.0, 1.0)
            denom = np.cos(np.arcsin(ax_clipped))
            
            # 3. Prevent division by zero if tilted 90 degrees
            if abs(denom) < 1e-6:
                return 0.0
                
            # 4. Clip final fraction for outer arcsin
            final_fraction = np.clip(gz / denom, -1.0, 1.0)
            
            phi_g = np.arcsin(final_fraction)
            return np.degrees(phi_g)
        except:
            return 0.0

    def estimate(self, acc, gyro):
        """
        Runs the Kalman filter over the entire trial.
        acc: [N x 3] (X, Y, Z)
        gyro: [N x 3] (X, Y, Z)
        """
        angles = []
        for i in range(len(acc)):
            # --- Observation Step ---
            # Call our robust phi calculation
            phi_g = self.calculate_observation_phi(acc[i, 0], acc[i, 1], acc[i, 2])

            # --- Prediction Step (Equation 9) ---
            # Use Gyro X (M/L rotation in ISB)
            A = np.array([[1, -self.T], 
                          [0, 1]])
            B = np.array([self.T, 0])
            
            self.X = A @ self.X + B * gyro[i, 0]
            self.P = A @ self.P @ A.T + self.Q

            # --- Update Step (Equation 10) ---
            H = np.array([1, 0])
            # Kalman Gain
            S = H @ self.P @ H.T + self.R
            K = self.P @ H.T / S
            
            # Correct the estimate
            innovation = phi_g - (H @ self.X)
            self.X = self.X + K * innovation
            self.P = (np.eye(2) - np.outer(K, H)) @ self.P
            
            angles.append(self.X[0])
            
        return np.array(angles)

def get_sway_metrics(acc, gyro, fs):
    """
    Modular wrapper used by analysis.py
    """
    kf = TrunkSwayKalman(fs)
    angles = kf.estimate(acc, gyro)
    # Calculate Root Mean Square (RMS) of the sway angles
    return np.sqrt(np.mean(np.square(angles)))