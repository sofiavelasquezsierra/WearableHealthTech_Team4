import Levenshtein
from Levenshtein import distance
import numpy as np

# normalize a name to a certain convention
# it seems easier computationally to get rid of underscores then add them 
def normalize_PelvisAccX(s):
    return s.lower().replace("_", "").replace("p", "P").replace("a", "A").replace("x", "X")

# geodesic rotation distance given two rotation matricies R1 and R2:
# standard metric in IMU alignment
def so3_distance(R1, R2):
    return np.arccos((np.trace(R1.T @ R2) - 1) / 2)


norm = normalize_PelvisAccX("pelvis_acc_x")
# example of inconsistent metadata
dist1 = distance("pelvis_acc_x", "PelvisAccX")
print("pelvis_acc_x vs PelvisAccX: distance = ", dist1, "normalized = ", norm)
dist2 = distance("hello", "worLd")
print("hello vs world: distance = ", dist2)
dist3 = distance("zero", "zero")
print("zero vs zero: distance = ", dist3)

