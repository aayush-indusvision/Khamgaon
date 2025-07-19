# import os
# from dotenv import load_dotenv
# import cv2
# from collections import deque
# import time
# import datetime
# import numpy as np

# from scripts.plc import initialize_plc
# from utils.utils import get_average_color,overlay_text

# # Load .env config
# env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', '.env')
# load_dotenv(env_path)

# # -------- CONFIG ---------
# ROI_TOP_LEFT_x = int(os.getenv("ROI_TOP_LEFT_x"))
# ROI_TOP_LEFT_y = int(os.getenv("ROI_TOP_LEFT_y"))
# ROI_BOTTOM_RIGHT_x = int(os.getenv("ROI_BOTTOM_RIGHT_x"))
# ROI_BOTTOM_RIGHT_y = int(os.getenv("ROI_BOTTOM_RIGHT_y"))
# DIFFERENCE_THRESHOLD = int(os.getenv("DIFFERENCE_THRESHOLD"))
# SAVE_FOLDER = os.getenv("SAVE_FOLDER")
# PLC_READ_TAG = os.getenv("PLC_READ_TAG")
# PLC_WRITE_TAG = os.getenv('PLC_WRITE_TAG')
# PLC_IP = os.getenv('PLC_IP')
# CAMERA_RTSP_URL = os.getenv('CAMERA_RTSP_URL')
# # -------------------------

# def process_rtsp_stream(rtsp_url):
#     plc = initialize_plc(PLC_IP)

#     fourcc = cv2.VideoWriter_fourcc(*'mp4v')
#     buffer_seconds = 60

#     jam_confirmed = False
#     recording = False
#     out = None

#     jam_start_time = None
#     jam_clear_time = None
#     post_jam_timer_started = False
#     machine_restarted = False

#     cap = None
#     frame_buffer = deque()
#     reconnect_wait = 2  # seconds

#     while True:
#         if cap is None or not cap.isOpened():
#             if cap:
#                 cap.release()
#             print("[ERROR] Camera not connected. Attempting reconnect...")
#             black_frame = np.zeros((500, 500, 3), dtype=np.uint8)
#             black_frame=overlay_text(black_frame, "Camera Not Connected!", (50, 250), (0, 0, 255))
#             cv2.imshow("RTSP Jam Monitor", black_frame)
#             cv2.waitKey(1)

#             cap = cv2.VideoCapture()
#             cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
#             cap.open(rtsp_url)
#             time.sleep(reconnect_wait)
#             continue

#         ret, frame = cap.read()
#         if not ret:
#             print("[ERROR] Camera disconnected. Waiting to reconnect...")
#             black_frame = np.zeros((500, 500, 3), dtype=np.uint8)
#             black_frame=overlay_text(black_frame, "Camera Disconnected!", (50, 250), (0, 0, 255))
#             cv2.imshow("RTSP Jam Monitor", black_frame)
#             cv2.waitKey(1)
#             cap.release()
#             cap = None
#             time.sleep(reconnect_wait)
#             continue

#         fps = cap.get(cv2.CAP_PROP_FPS) or 30
#         width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
#         height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
#         if len(frame_buffer) == 0:
#             frame_buffer = deque(maxlen=int(buffer_seconds * fps))

#         # Reconnect PLC if needed
#         if not plc:
#             plc = initialize_plc(PLC_IP)
#             time.sleep(2)

#         machine_running = False
#         try:
#             machine_running = plc.read(PLC_READ_TAG)  # Read machine state
#         except:
#             print("[ERROR] PLC read failed.")
#             plc = None
#             continue

#         current_time = time.time()
#         annotated_frame = frame.copy()

#         # Default annotation
#         annotated_frame=overlay_text(annotated_frame, f"Machine: {'Running' if machine_running.value else 'Stopped'}", (30, 40), (255, 255, 0))

#         # Only check jam when machine is running
#         if machine_running.value:
#             roi = frame[ROI_TOP_LEFT_y:ROI_BOTTOM_RIGHT_y, ROI_TOP_LEFT_x:ROI_BOTTOM_RIGHT_x]
#             avg_roi = get_average_color(roi)
#             avg_full = get_average_color(frame)
#             brightness_difference = avg_roi - avg_full
#             is_jam = brightness_difference > DIFFERENCE_THRESHOLD

#             if is_jam:
#                 if jam_start_time is None:
#                     jam_start_time = current_time
#                 elif current_time - jam_start_time >= 0.1:
#                     jam_confirmed = True
#                     jam_clear_time = None
#                     post_jam_timer_started = False
#                     machine_restarted = False
#             else:
#                 jam_start_time = None
#                 if jam_confirmed and not post_jam_timer_started:
#                     jam_clear_time = current_time
#                     post_jam_timer_started = True
#         else:
#             # If jam was previously confirmed and now machine is restarted
#             if jam_confirmed and post_jam_timer_started and not machine_restarted:
#                 if current_time - jam_clear_time >= 10:
#                     machine_restarted = True
#                     if recording and out:
#                         out.release()
#                         print("[INFO] Recording stopped after jam cleared and machine restarted.")
#                     recording = False
#                     out = None
#                     jam_confirmed = False
#                     post_jam_timer_started = False
#                     jam_start_time = None

#         # -------------------- Annotate Frame --------------------
#         if jam_confirmed:
#             annotated_frame=overlay_text(annotated_frame, "Status: Jam", (50, 100), (0, 0, 255))
#             cv2.rectangle(annotated_frame, (ROI_TOP_LEFT_x, ROI_TOP_LEFT_y),
#                           (ROI_BOTTOM_RIGHT_x, ROI_BOTTOM_RIGHT_y), (0, 0, 255), 2)
#             if not recording:
#                 ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
#                 filename = f"jam_{ts}.mp4"
#                 filepath = os.path.join(SAVE_FOLDER, filename)
#                 out = cv2.VideoWriter(filepath, fourcc, fps, (width, height))
#                 print(f"[JAM DETECTED] Recording started: {filepath}")
#                 for buffered_frame in frame_buffer:
#                     out.write(buffered_frame)
#                 recording = True
#         else:
#             annotated_frame=overlay_text(annotated_frame, "Status: Good", (50, 100), (0, 255, 0))
#             cv2.rectangle(annotated_frame, (ROI_TOP_LEFT_x, ROI_TOP_LEFT_y),
#                           (ROI_BOTTOM_RIGHT_x, ROI_BOTTOM_RIGHT_y), (0, 255, 0), 2)

#         frame_buffer.append(annotated_frame.copy())

#         # -------------------- PLC Write --------------------
#         try:
#             if plc:
#                 plc.write(PLC_WRITE_TAG, 1 if jam_confirmed else 0)
#         except:
#             plc = None
#             print("[ERROR] PLC write failed.")

#         # -------------------- Save Frame --------------------
#         if recording and out:
#             out.write(annotated_frame)

#         cv2.imshow("RTSP Jam Monitor", cv2.resize(annotated_frame, (500, 500)))
#         if cv2.waitKey(1) & 0xFF == ord('q'):
#             break

#     if out:
#         out.release()
#     if cap:
#         cap.release()
#     cv2.destroyAllWindows()

# if __name__ == "__main__":
#     rtsp_url = CAMERA_RTSP_URL
#     process_rtsp_stream(rtsp_url)

import os
from dotenv import load_dotenv
import cv2
from collections import deque
import time
import datetime
import numpy as np

from scripts.plc import initialize_plc
from utils.utils import get_average_color, overlay_text
from utils import supporting_variables

# Load .env config
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', '.env')
load_dotenv(env_path)

# -------- CONFIG ---------
ROI_TOP_LEFT_x = int(os.getenv("ROI_TOP_LEFT_x"))
ROI_TOP_LEFT_y = int(os.getenv("ROI_TOP_LEFT_y"))
ROI_BOTTOM_RIGHT_x = int(os.getenv("ROI_BOTTOM_RIGHT_x"))
ROI_BOTTOM_RIGHT_y = int(os.getenv("ROI_BOTTOM_RIGHT_y"))
DIFFERENCE_THRESHOLD = int(os.getenv("DIFFERENCE_THRESHOLD"))
SAVE_FOLDER = os.getenv("SAVE_FOLDER")
PLC_READ_TAG = os.getenv("PLC_READ_TAG")
PLC_WRITE_TAG = os.getenv('PLC_WRITE_TAG')
PLC_IP = os.getenv('PLC_IP')
CAMERA_RTSP_URL = os.getenv('CAMERA_RTSP_URL')
# -------------------------

def process_rtsp_stream(rtsp_url):
    plc = initialize_plc(PLC_IP)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    buffer_seconds = 60

    jam_confirmed = False
    recording = False
    out = None
    jam_start_time = None

    awaiting_guard_close_after_stop = False
    jam_cleared = False
    post_jam_restart_recording = False
    machine_restart_time = None

    cap = None
    frame_buffer = deque()
    reconnect_wait = 2  # seconds

    prev_machine_running = False

    while True:
        if cap is None or not cap.isOpened():
            if cap:
                cap.release()
            print("[ERROR] Camera not connected. Attempting reconnect...")
            black_frame = np.zeros((500, 500, 3), dtype=np.uint8)
            black_frame = overlay_text(black_frame, "Camera Not Connected!", (50, 250), (0, 0, 255))
            cv2.imshow("RTSP Jam Monitor", black_frame)
            cv2.waitKey(1)

            cap = cv2.VideoCapture()
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            cap.open(rtsp_url)
            time.sleep(reconnect_wait)
            continue

        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Camera disconnected. Waiting to reconnect...")
            black_frame = np.zeros((500, 500, 3), dtype=np.uint8)
            black_frame = overlay_text(black_frame, "Camera Disconnected!", (50, 250), (0, 0, 255))
            cv2.imshow("RTSP Jam Monitor", black_frame)
            cv2.waitKey(1)
            cap.release()
            cap = None
            time.sleep(reconnect_wait)
            continue

        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
        if len(frame_buffer) == 0:
            frame_buffer = deque(maxlen=int(buffer_seconds * fps))

        if not plc:
            plc = initialize_plc(PLC_IP)
            time.sleep(2)

        try:
            machine_running = plc.read(PLC_READ_TAG)
            guard_plc_data = plc.read(*supporting_variables.variables)
            guard_values = np.array([item.value for item in guard_plc_data])
        except:
            print("[ERROR] PLC read failed.")
            plc = None
            continue

        current_time = time.time()
        annotated_frame = frame.copy()
        annotated_frame = overlay_text(annotated_frame, f"Machine: {'Running' if machine_running.value else 'Stopped'}", (30, 40), (255, 255, 0))

        # Jam detection logic
        if machine_running.value:
            roi = frame[ROI_TOP_LEFT_y:ROI_BOTTOM_RIGHT_y, ROI_TOP_LEFT_x:ROI_BOTTOM_RIGHT_x]
            avg_roi = get_average_color(roi)
            avg_full = get_average_color(frame)
            brightness_difference = avg_roi - avg_full
            is_jam = brightness_difference > DIFFERENCE_THRESHOLD

            if is_jam:
                if jam_start_time is None:
                    jam_start_time = current_time
                elif current_time - jam_start_time >= 1:
                    if not jam_confirmed:
                        print("[JAM DETECTED] Jam confirmed.")
                    jam_confirmed = True
                    jam_cleared = False
                    awaiting_guard_close_after_stop = False
            else:
                jam_start_time = None
        else:
            jam_start_time = None
            if jam_confirmed:
                if not awaiting_guard_close_after_stop:
                    if False in guard_values:
                        awaiting_guard_close_after_stop = True
                        print("[INFO] Guard opened after machine stopped. Awaiting all guards to close...")
                elif False not in guard_values:
                    jam_confirmed = False
                    jam_cleared = True
                    awaiting_guard_close_after_stop = False
                    print("[INFO] Jam cleared after guard cycle.")

        # Detect machine restart after jam was cleared
        if jam_cleared and not prev_machine_running and machine_running.value:
            machine_restart_time = current_time
            post_jam_restart_recording = True
            jam_cleared = False
            print("[INFO] Machine restarted after jam. Continuing recording for 10 seconds...")

        # Annotate frame
        if jam_confirmed:
            annotated_frame = overlay_text(annotated_frame, "Status: Jam", (50, 100), (0, 0, 255))
            cv2.rectangle(annotated_frame, (ROI_TOP_LEFT_x, ROI_TOP_LEFT_y),
                          (ROI_BOTTOM_RIGHT_x, ROI_BOTTOM_RIGHT_y), (0, 0, 255), 2)
            if not recording:
                ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                filename = f"jam_{ts}.mp4"
                filepath = os.path.join(SAVE_FOLDER, filename)
                out = cv2.VideoWriter(filepath, fourcc, fps, (width, height))
                print(f"[INFO] Recording started: {filepath}")
                for buffered_frame in frame_buffer:
                    out.write(buffered_frame)
                recording = True
        else:
            annotated_frame = overlay_text(annotated_frame, "Status: Good", (50, 100), (0, 255, 0))
            cv2.rectangle(annotated_frame, (ROI_TOP_LEFT_x, ROI_TOP_LEFT_y),
                          (ROI_BOTTOM_RIGHT_x, ROI_BOTTOM_RIGHT_y), (0, 255, 0), 2)

        # Stop recording after 10 seconds post restart
        if post_jam_restart_recording and current_time - machine_restart_time >= 10:
            if out:
                out.release()
            print("[INFO] Recording stopped 10 seconds after machine restart.")
            out = None
            recording = False
            post_jam_restart_recording = False

        frame_buffer.append(annotated_frame.copy())

        # PLC write
        try:
            if plc:
                plc.write(PLC_WRITE_TAG, 1 if jam_confirmed else 0)
        except:
            plc = None
            print("[ERROR] PLC write failed.")

        if recording and out:
            out.write(annotated_frame)

        cv2.imshow("RTSP Jam Monitor", cv2.resize(annotated_frame, (500, 500)))
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        # Store previous machine state
        prev_machine_running = machine_running.value

    if out:
        out.release()
    if cap:
        cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    rtsp_url = CAMERA_RTSP_URL
    process_rtsp_stream(rtsp_url)
