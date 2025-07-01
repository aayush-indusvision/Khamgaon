import os
from dotenv import load_dotenv
import cv2
from collections import deque
import time
import datetime

from scripts.plc import initialize_plc
from utils.utils import *

# Load .env config
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', '.env')
load_dotenv(env_path)

# -------- CONFIG ---------
ROI_TOP_LEFT_x = int(os.getenv("ROI_TOP_LEFT_x"))
ROI_TOP_LEFT_y = int(os.getenv("ROI_TOP_LEFT_y"))
ROI_BOTTOM_RIGHT_x = int(os.getenv("ROI_BOTTOM_RIGHT_x"))
ROI_BOTTOM_RIGHT_y = int(os.getenv("ROI_BOTTOM_RIGHT_y"))
DIFFERENCE_THRESHOLD = int(os.getenv("DIFFERENCE_THRESHOLD"))
SAVE_FOLDER = os.getenv('SAVED_FOLDER')
# -------------------------

def process_rtsp_stream(rtsp_url):
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        print("[ERROR] Could not open RTSP stream.")
        return

    # PLC
    plc = initialize_plc("192.168.10.222")
    if not plc:
        print("[ERROR] Failed to initialise PLC")

    # State variables
    jamming = False
    recording = False
    potential_jam_duration = 0
    jam_duration = 0
    jam_start_time = None
    out = None

    # Video info
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')

    # Buffer for 1 minute = 60 * fps
    buffer_seconds = 60
    frame_buffer = deque(maxlen=int(buffer_seconds * fps))

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("[WARNING] Frame read failed. Reconnecting...")
            cap.release()
            time.sleep(2)
            cap = cv2.VideoCapture(rtsp_url)
            continue

        # Crop ROI and calculate difference
        roi = frame[ROI_TOP_LEFT_y:ROI_BOTTOM_RIGHT_y, ROI_TOP_LEFT_x:ROI_BOTTOM_RIGHT_x]
        avg_roi = get_average_color(roi)
        avg_full = get_average_color(frame)
        difference = avg_roi - avg_full
        is_jam = difference > DIFFERENCE_THRESHOLD

        frame_buffer.append(frame.copy())
        status = "Jam" if jamming else "Good"
        color = (0, 0, 255) if jamming else (0, 255, 0)

        # Jam detection logic
        if is_jam:
            potential_jam_duration += 1 / fps

            if not jamming and potential_jam_duration >= 2:
                # Confirm jamming
                jamming = True
                jam_start_time = time.time()
                jam_duration = 0

                ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                filename = f"jam_{ts}.mp4"
                filepath = os.path.join(SAVE_FOLDER, filename)
                out = cv2.VideoWriter(filepath, fourcc, fps, (width, height))
                print(f"[INFO] Jamming confirmed. Recording started: {filepath}")

                # Write buffer
                for buffered_frame in frame_buffer:
                    out.write(buffered_frame)
                recording = True

            if jamming:
                jam_duration += 1 / fps
        else:
            potential_jam_duration = 0

            if jamming:
                # Jamming ended
                jam_end_time = time.time()
                jam_start_fmt = format_time(jam_start_time)
                duration_fmt = jam_duration
                print(f"[JAM CLEARED] Start: {jam_start_fmt}, Duration: {duration_fmt:.2f} sec")

                # Stop states
                jamming = False
                jam_duration = 0
                jam_start_time = None

                if recording and out:
                    out.release()
                    print("[INFO] Recording stopped.")
                    recording = False

        # PLC write
        if jamming:
            plc.write("BSM_AI_CAMERA_READ_INT[2]", 1)
        else:
            plc.write("BSM_AI_CAMERA_READ_INT[2]", 0)

        # Show stream with ROI
        cv2.rectangle(frame, (ROI_TOP_LEFT_x, ROI_TOP_LEFT_y),
                      (ROI_BOTTOM_RIGHT_x, ROI_BOTTOM_RIGHT_y), color, 2)
        cv2.putText(frame, f"Status: {status}", (50, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 2, color, 3)
        
                # Write live frame to video if recording
        if recording and out:
            out.write(frame)

        cv2.imshow("RTSP Jam Monitor", cv2.resize(frame, (500, 500)))
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Cleanup
    if out:
        out.release()
    cap.release()
    cv2.destroyAllWindows()


# Example usage
if __name__ == "__main__":
    rtsp_url = "rtsp://admin:admin123@192.168.10.16:554"
    process_rtsp_stream(rtsp_url)
