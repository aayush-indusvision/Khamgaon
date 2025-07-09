import cv2, os
from ultralytics import YOLO
from collections import deque
from datetime import datetime
import threading
import time

from scripts.plc import *

# --- ROI coordinates ---
x1, y1, x2, y2 = 0, 410, 490, 800

# --- PLC Setup ---
PLC_IP_ADDRESS = os.getenv('PLC_IP_ADDRESS')
PLC_STATUS_TAG = os.getenv('PLC_STATUS_TAG')
PLC_WRITE_TAG = os.getenv('PLC_WRITE_TAG')

# --- PLC Initialisation ---
plc_client = None
plc_client_on = False
plc_lock = threading.Lock()


plc_client,plc_client_on=initialize_plc(PLC_IP_ADDRESS,plc_lock)

# --- Model and paths ---
model_path = os.getenv('MODEL_WEIGHTS')
model = YOLO(model_path)

video_path = r"rtsp://admin:admin@123@192.168.10.19:554"
output_folder = r"C:\Users\pc\Desktop\Khamgaon_Analytics\ABM_SOAP_JAMMING\Soap_jamming"
os.makedirs(output_folder, exist_ok=True)

cap = cv2.VideoCapture(video_path)
if cap is None or not cap.isOpened():
    print("Error opening video file")
    exit()

fps = cap.get(cv2.CAP_PROP_FPS)
if fps == 0 or fps is None:
    fps = 7

width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fourcc = cv2.VideoWriter_fourcc(*'mp4v')

# --- Parameters ---
pre_record_seconds = 60
post_record_seconds = 5
jam_confirm_frames = int(3 * fps)

# --- Buffers & State ---
pre_buffer = deque(maxlen=int(pre_record_seconds * fps))
record_buffer = []
recording = False
recording_post_jam = False
post_jam_frame_count = 0

jamming_frame_counter = 0
jamming_confirmed = False
stop_time = None
last_detected_class = None
machine_on = True
prev_machine_on = machine_on
machine_restart_detected = False

cv2.namedWindow("Soap Jamming Detection", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Soap Jamming Detection", 500, 500)

while True:
    ret, original_frame = cap.read()
    if not ret or original_frame is None:
        print("End of video or failed to read frame")
        break

    machine_on = read_machine_status(PLC_IP_ADDRESS,PLC_STATUS_TAG,plc_lock,plc_client_on,plc_client)
    if machine_on not in [True, False]:
        machine_on = False

    frame = original_frame.copy()

    roi_crop = frame[y1:y2, x1:x2]
    pre_buffer.append(frame.copy())

    if machine_on:
        write_plc_value(0,PLC_WRITE_TAG,plc_lock,plc_client_on,plc_client)

        gray_roi = cv2.cvtColor(roi_crop, cv2.COLOR_BGR2GRAY)
        gray_roi_3ch = cv2.merge([gray_roi, gray_roi, gray_roi])
        results = model.predict(gray_roi_3ch, verbose=False)

        if len(results) > 0:
            probs = results[0].probs
            if probs is not None:
                confidence = float(probs.top1conf)
                class_id = int(probs.top1)
                class_name = results[0].names[class_id]
                last_detected_class = class_name

                if (class_name != "nondefect") or ((class_name == "nondefect") and (confidence < 0.98)):
                    jamming_frame_counter += 1
                else:
                    jamming_frame_counter = 0

                if jamming_frame_counter >= jam_confirm_frames:
                    colour = (0, 0, 255)
                    label = f"Jam: {confidence:.2f}"
                else:
                    colour = (0, 255, 0)
                    label = f"Normal: {confidence:.2f}"

                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.5, colour, 2, cv2.LINE_AA)
                cv2.rectangle(frame, (x1, y1), (x2, y2), colour, 2)

                if not jamming_confirmed and jamming_frame_counter >= jam_confirm_frames:
                    jamming_confirmed = True
                    recording = True
                    stop_time = datetime.now()
                    print(f"[{stop_time.strftime('%H:%M:%S')}] Jamming CONFIRMED")
                    write_plc_value(1,PLC_WRITE_TAG,plc_lock,plc_client_on,plc_client)
                    record_buffer.extend(pre_buffer)

        if jamming_confirmed:
            record_buffer.append(frame.copy())
            write_plc_value(1,PLC_WRITE_TAG,plc_lock,plc_client_on,plc_client)

        cv2.putText(frame, "ABM Status: Live", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)

    else:
        if jamming_confirmed and not machine_restart_detected:
            cv2.putText(frame, "Clearing Jamming", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 165, 255), 3)
        else:
            cv2.putText(frame, "ABM Status: OFF", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)

        if recording and jamming_confirmed and not recording_post_jam:
            print("Machine turned OFF during jamming — Waiting for restart")
            recording_post_jam = True
            post_jam_frame_count = 0

        if recording_post_jam:
            record_buffer.append(frame.copy())

    if recording_post_jam and machine_on and jamming_confirmed:
        if not machine_restart_detected:
            print("Machine restarted — Start post-jam recording")
            machine_restart_detected = True
        record_buffer.append(frame.copy())
        post_jam_frame_count += 1

        if post_jam_frame_count >= int(post_record_seconds * fps):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_out_path = os.path.join(output_folder, f"output_{timestamp}.mp4")
            out = cv2.VideoWriter(video_out_path, fourcc, fps, (width, height), True)

            if out.isOpened():
                for f in record_buffer:
                    out.write(f)
                out.release()
                print(f"Video saved: {video_out_path}")
            else:
                print("Error saving video")

            pre_buffer.clear()
            record_buffer.clear()
            recording = False
            recording_post_jam = False
            jamming_confirmed = False
            jamming_frame_counter = 0
            post_jam_frame_count = 0
            stop_time = None
            last_detected_class = None
            machine_restart_detected = False
            time.sleep(10)
            write_plc_value(0,PLC_WRITE_TAG,plc_lock,plc_client_on,plc_client)

    display_frame = cv2.resize(frame, (500, 500))
    cv2.imshow("Soap Jamming Detection", display_frame)

    key = cv2.waitKey(7) & 0xFF
    if key == ord('q'):
        break

    prev_machine_on = machine_on

cap.release()
cv2.destroyAllWindows()
