# import os
# from dotenv import load_dotenv
# import cv2
# import numpy as np

# env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', '.env')
# load_dotenv(env_path)

# # ----------- CONFIG -------------
# ROI_TOP_LEFT_x = int(os.getenv("ROI_TOP_LEFT_x"))
# ROI_TOP_LEFT_y = int(os.getenv("ROI_TOP_LEFT_y"))
# ROI_BOTTOM_RIGHT_x = int(os.getenv("ROI_BOTTOM_RIGHT_x"))
# ROI_BOTTOM_RIGHT_y = int(os.getenv("ROI_BOTTOM_RIGHT_y"))
# DIFFERENCE_THRESHOLD = int(os.getenv("DIFFERENCE_THRESHOLD"))
# # --------------------------------

# def get_average_color(image):
#     avg_color = np.mean(image, axis=(0, 1))
#     return np.mean(avg_color)

# def format_time(seconds):
#     """Convert seconds to HH:MM:SS format."""
#     hours = int(seconds // 3600)
#     minutes = int((seconds % 3600) // 60)
#     secs = int(seconds % 60)
#     return f"{hours:02}:{minutes:02}:{secs:02}"

# def process_video(video_path):
#     jam_flag=0
#     cap = cv2.VideoCapture(video_path)
#     fps = cap.get(cv2.CAP_PROP_FPS)
#     frame_idx = 0

#     while cap.isOpened():
#         ret, frame = cap.read()
#         if not ret:
#             break

#         frame_idx += 1
#         timestamp_seconds = frame_idx / fps
#         timestamp_formatted = format_time(timestamp_seconds)

#         # Calculate average colors
#         cropped = frame[ROI_TOP_LEFT_y:ROI_BOTTOM_RIGHT_y, ROI_TOP_LEFT_x:ROI_BOTTOM_RIGHT_x]
#         avg_cropped = get_average_color(cropped)
#         avg_full = get_average_color(frame)
#         difference = avg_cropped - avg_full

#         # Determine status and draw
#         is_jam = difference > DIFFERENCE_THRESHOLD
#         color = (0, 0, 255) if is_jam else (0, 255, 0)
#         status = "Jam" if is_jam else "Good"

#         # Log jamming time
#         if is_jam and jam_flag==0:
#             print(f"[JAM DETECTED] Timestamp: {timestamp_formatted} (Frame {frame_idx}, Diff: {difference:.2f})")
#             jam_flag=1
            

#         # Draw ROI and status
#         cv2.rectangle(frame, (ROI_TOP_LEFT_x, ROI_TOP_LEFT_y), (ROI_BOTTOM_RIGHT_x, ROI_BOTTOM_RIGHT_y), color, 3)
#         cv2.putText(frame, f"Status: {status}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, color, 3)

#         frame = cv2.resize(frame, (500, 500))
#         cv2.imshow("Frame Analysis", frame)
#         if cv2.waitKey(1) & 0xFF == ord('q'):
#             break

#     cap.release()
#     cv2.destroyAllWindows()

# # Example usage
# video_path = r"assets\video_5.dav"
# process_video(video_path)


import os
from dotenv import load_dotenv
import cv2
import numpy as np

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', '.env')
load_dotenv(env_path)

# ----------- CONFIG -------------
ROI_TOP_LEFT_x = int(os.getenv("ROI_TOP_LEFT_x"))
ROI_TOP_LEFT_y = int(os.getenv("ROI_TOP_LEFT_y"))
ROI_BOTTOM_RIGHT_x = int(os.getenv("ROI_BOTTOM_RIGHT_x"))
ROI_BOTTOM_RIGHT_y = int(os.getenv("ROI_BOTTOM_RIGHT_y"))
DIFFERENCE_THRESHOLD = int(os.getenv("DIFFERENCE_THRESHOLD"))
# --------------------------------

def get_average_color(image):
    avg_color = np.mean(image, axis=(0, 1))
    return np.mean(avg_color)

def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02}:{minutes:02}:{secs:02}"

def process_video(video_path):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_idx = 0

    jamming = False
    jam_start_frame = None

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        timestamp_seconds = frame_idx / fps
        timestamp_formatted = format_time(timestamp_seconds)

        # Crop and calculate average brightness
        cropped = frame[ROI_TOP_LEFT_y:ROI_BOTTOM_RIGHT_y, ROI_TOP_LEFT_x:ROI_BOTTOM_RIGHT_x]
        avg_cropped = get_average_color(cropped)
        avg_full = get_average_color(frame)
        difference = avg_cropped - avg_full

        # Check for jam
        print(difference)
        is_jam = difference > DIFFERENCE_THRESHOLD
        color = (0, 0, 255) if is_jam else (0, 255, 0)
        status = "Jam" if is_jam else "Good"

        # Jam start logic
        if is_jam:
            if not jamming:
                jamming = True
                jam_start_frame = frame_idx
        else:
            if jamming:
                jam_duration = (frame_idx - jam_start_frame) / fps
                if jam_duration >= 2:
                    jam_timestamp = format_time(jam_start_frame / fps)
                    print(f"[JAM DETECTED] Timestamp: {jam_timestamp} (Duration: {jam_duration:.2f} sec)")
                jamming = False
                jam_start_frame = None

        # Draw ROI and status
        cv2.rectangle(frame, (ROI_TOP_LEFT_x, ROI_TOP_LEFT_y), (ROI_BOTTOM_RIGHT_x, ROI_BOTTOM_RIGHT_y), color, 3)
        cv2.putText(frame, f"Status: {status}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, color, 3)

        frame = cv2.resize(frame, (500, 500))
        cv2.imshow("Frame Analysis", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Handle case if jamming was active at end of video
    if jamming:
        jam_duration = (frame_idx - jam_start_frame) / fps
        if jam_duration >= 5:
            jam_timestamp = format_time(jam_start_frame / fps)
            print(f"[JAM DETECTED] Timestamp: {jam_timestamp} (Duration: {jam_duration:.2f} sec)")

    cap.release()
    cv2.destroyAllWindows()

# Example usage
video_path = r"jam_20250702-234630.mp4"
process_video(video_path)
