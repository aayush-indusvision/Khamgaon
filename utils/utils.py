import numpy as np
import time

def get_average_color(image):
    avg_color = np.mean(image, axis=(0, 1))
    return np.mean(avg_color)

def format_time(seconds):
    """Convert seconds since epoch to HH:MM:SS format."""
    local_time = time.localtime(seconds)
    return time.strftime("%H:%M:%S", local_time)