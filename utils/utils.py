import numpy as np
import time
import cv2

def get_average_color(image):
    avg_color = np.mean(image, axis=(0, 1))
    return np.mean(avg_color)

def format_time(seconds):
    """Convert seconds since epoch to HH:MM:SS format."""
    local_time = time.localtime(seconds)
    return time.strftime("%H:%M:%S", local_time)

def overlay_text(frame, text, position=(30, 50), color=(0, 0, 255)):
    cv2.putText(frame, text, position, cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3)
    return frame