import os
from pycomm3 import LogixDriver
import cv2
import numpy as np
import time as tim
from dashboard import *

def start_recording(frame_size, fps=5):
    global video_writer, is_recording

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"door_open_{timestamp}.avi"
    output_path = os.path.join(OUTPUT_DIR, filename)

    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    video_writer = cv2.VideoWriter(output_path, fourcc, fps, frame_size)
    is_recording = True

    print(f"[RECORDING] Started: {filename}")

def stop_recording():
    global video_writer, is_recording

    if video_writer:
        video_writer.release()
        video_writer = None
        print(f"[RECORDING] Stopped and saved.")
    is_recording = False
    
def check_hand_stationary(current_bboxes, last_hand_positions, last_movement_frames, 
                           stationary_frame_count=75, movement_threshold=10, current_frame=0):
    """
    Check which hands have not moved for more than the specified number of frames and return their bounding box coordinates.

    Args:
        current_bboxes (list of lists): List where each entry is a list of bounding box coordinates [x1, y1, x2, y2].
        last_hand_positions (dict): Dictionary with indices as keys and last known positions as values.
        last_movement_frames (dict): Dictionary with indices as keys and the last frame movement was detected.
        stationary_frame_count (int): Number of frames to consider the hand as stationary.
        movement_threshold (float): Distance in pixels to determine if movement has occurred.
        current_frame (int): The current frame number.

    Returns:
        list of lists: List of bounding boxes for hands that have not moved for more than the specified number of frames.
    """
    stationary_hands = []

    # Iterate over the list of current bounding boxes
    for idx, bbox in enumerate(current_bboxes):
        # Calculate the center of the bounding box
        center_x = (bbox[0] + bbox[2]) / 2
        center_y = (bbox[1] + bbox[3]) / 2
        current_hand_position = (center_x, center_y)

        if idx in last_hand_positions:
            last_position = last_hand_positions[idx]
            distance = np.linalg.norm(np.array(current_hand_position) - np.array(last_position))
            
            if distance < movement_threshold:
                # Check if the hand has been stationary for the required number of frames
                if current_frame - last_movement_frames[idx] >= stationary_frame_count:
                    stationary_hands.append(bbox)
            else:
                last_movement_frames[idx] = current_frame
        else:
            # Initialize tracking for new hand detection
            last_hand_positions[idx] = current_hand_position
            last_movement_frames[idx] = current_frame

        # Update the position
        last_hand_positions[idx] = current_hand_position

    # Handle hands that are not detected in this frame
    detected_indices = set(range(len(current_bboxes)))
    for idx in list(last_hand_positions.keys()):
        if idx not in detected_indices:
            # If hand is not detected, check if it has been stationary for the duration
            if current_frame - last_movement_frames.get(idx, 0) >= stationary_frame_count:
                # Optionally add bounding box of the stationary hand if it was previously tracked
                if idx < len(current_bboxes):
                    stationary_hands.append(current_bboxes[idx])
            # Update the last detection frame to keep tracking
            last_movement_frames[idx] = current_frame

    return stationary_hands

def generate_empty_frame(height,width):
    image = np.ones((height,width, 3), dtype=np.uint8) * 255
    (text_width, text_height), baseline = cv2.getTextSize("Cannot fetch Camera feed", cv2.FONT_HERSHEY_SIMPLEX, 1.5,2)
    text_x = (width - text_width) // 2
    text_y = (height + text_height) // 2
    cv2.putText(image, "Cannot fetch Camera feed", (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX,1.5, (0,0,0), 2, lineType=cv2.LINE_AA)
    return image

def get_image_parameters(cap):
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
    fps = cap.get(cv2.CAP_PROP_FPS) or 5

    return width,height,fps