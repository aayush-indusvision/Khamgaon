import os
from dotenv import load_dotenv
import cv2
from pycomm3 import LogixDriver
import time

from scripts.plc import initialize_plc
from utils.utils import *

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', '.env')
load_dotenv(env_path)

# ----------- CONFIG -------------
ROI_TOP_LEFT_x = int(os.getenv("ROI_TOP_LEFT_x"))
ROI_TOP_LEFT_y = int(os.getenv("ROI_TOP_LEFT_y"))
ROI_BOTTOM_RIGHT_x = int(os.getenv("ROI_BOTTOM_RIGHT_x"))
ROI_BOTTOM_RIGHT_y = int(os.getenv("ROI_BOTTOM_RIGHT_y"))
DIFFERENCE_THRESHOLD = int(os.getenv("DIFFERENCE_THRESHOLD"))
# --------------------------------


def process_rtsp_stream(rtsp_url):
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        print("[ERROR] Could not open RTSP stream.")
        return

    jamming = False
    jam_start_time = None
    jam_duration = 0
    jam_state = 0  # 1 during valid jam, 0 otherwise

    plc=initialize_plc("192.168.10.222")
    if not plc:
        print("Failed to initialise PLC")

    while True:
        video_path = "rtsp://admin:admin123@192.168.10.16:554"
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened() and plc:

            frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)

            while cap.isOpened():
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
                    jam_duration += 1/fps
                    if not jamming:
                        jam_start_time = current_time
                        jamming = True
                else:
                    if jamming:
                        if jam_duration >= 2:
                            jam_start_formatted = format_time(jam_start_time)
                            print(f"[JAM DETECTED] Timestamp: {jam_start_formatted} (Duration: {jam_duration:.2f} sec)")
                        jamming = False
                        jam_start_time = None

                # Set jam_state based on valid jam
                if jamming:
                    state=plc.write(f"BSM_AI_CAMERA_READ_INT[2]",1)
                    if state:
                        print(f"Writing 1 to PLC")
                else:
                    state=plc.write(f"BSM_AI_CAMERA_READ_INT[2]",0)
                    # print(f"Time: {format_time(current_time)}, Jam State: {jam_state}")

                # Draw ROI and status
                cv2.rectangle(frame, (ROI_TOP_LEFT_x, ROI_TOP_LEFT_y), (ROI_BOTTOM_RIGHT_x, ROI_BOTTOM_RIGHT_y), color, 3)
                cv2.putText(frame, f"Status: {status}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, color, 3)

                frame = cv2.resize(frame, (500, 500))
                cv2.imshow("RTSP Stream Analysis", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            # Final jam detection if stream ends during a jam
            if jamming:
                if jam_duration >= 2:
                    jam_start_formatted = format_time(jam_start_time)
                    print(f"[JAM DETECTED] Timestamp: {jam_start_formatted} (Duration: {jam_duration:.2f} sec)")

            cap.release()
            cv2.destroyAllWindows()
        
        else:
            print("[ERROR] Camera or PLC not connected")

# Example usage
rtsp_url = "rtsp://username:password@ip_address:port/stream"
process_rtsp_stream(rtsp_url)
