import os
from dotenv import load_dotenv
import cv2
import numpy as np
import time

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
    """Convert seconds since epoch to HH:MM:SS format."""
    local_time = time.localtime(seconds)
    return time.strftime("%H:%M:%S", local_time)

def process_rtsp_stream(rtsp_url):
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        print("[ERROR] Could not open RTSP stream.")
        return

    jamming = False
    jam_start_time = None
    jam_state = 0  # 1 during valid jam, 0 otherwise

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[WARNING] Lost connection to RTSP stream. Reconnecting...")
            time.sleep(2)
            cap.release()
            cap = cv2.VideoCapture(rtsp_url)
            continue

        current_time = time.time()

        # Calculate average colors
        cropped = frame[ROI_TOP_LEFT_y:ROI_BOTTOM_RIGHT_y, ROI_TOP_LEFT_x:ROI_BOTTOM_RIGHT_x]
        avg_cropped = get_average_color(cropped)
        avg_full = get_average_color(frame)
        difference = avg_cropped - avg_full

        is_jam = difference > DIFFERENCE_THRESHOLD
        color = (0, 0, 255) if is_jam else (0, 255, 0)
        status = "Jam" if is_jam else "Good"

        # Track jam duration
        if is_jam:
            if not jamming:
                jam_start_time = current_time
                jamming = True
        else:
            if jamming:
                jam_duration = current_time - jam_start_time
                if jam_duration >= 2:
                    jam_start_formatted = format_time(jam_start_time)
                    print(f"[JAM DETECTED] Timestamp: {jam_start_formatted} (Duration: {jam_duration:.2f} sec)")
                jamming = False
                jam_start_time = None

        # Set jam_state based on valid jam
        if jamming:
            jam_duration = current_time - jam_start_time
            jam_state = 1 if jam_duration >= 2 else 0
        else:
            jam_state = 0

        print(f"Time: {format_time(current_time)}, Jam State: {jam_state}")

        # Draw ROI and status
        cv2.rectangle(frame, (ROI_TOP_LEFT_x, ROI_TOP_LEFT_y), (ROI_BOTTOM_RIGHT_x, ROI_BOTTOM_RIGHT_y), color, 3)
        cv2.putText(frame, f"Status: {status}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, color, 3)

        frame = cv2.resize(frame, (500, 500))
        cv2.imshow("RTSP Stream Analysis", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Final jam detection if stream ends during a jam
    if jamming:
        jam_duration = time.time() - jam_start_time
        if jam_duration >= 2:
            jam_start_formatted = format_time(jam_start_time)
            print(f"[JAM DETECTED] Timestamp: {jam_start_formatted} (Duration: {jam_duration:.2f} sec)")

    cap.release()
    cv2.destroyAllWindows()

# Example usage
rtsp_url = "rtsp://username:password@ip_address:port/stream"
process_rtsp_stream(rtsp_url)
