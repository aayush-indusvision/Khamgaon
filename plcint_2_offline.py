import cv2, os
from ultralytics import YOLO
from collections import deque
from datetime import datetime
import time

# --- ROI coordinates ---
x1, y1, x2, y2 = 0, 100, 350, 350

# --- Simulated PLC state ---
machine_on = True

# --- Model and paths ---
model_path = r"classify02.pt"
model = YOLO(model_path)

video_path = r"assets\jammed_videos-20250703T113153Z-1-001\jammed_videos\data1.mp4"
output_folder = r"Soap_jamming"
os.makedirs(output_folder, exist_ok=True)

cap = cv2.VideoCapture(video_path)
if cap is None or not cap.isOpened():
    print("Error opening video file")
    exit()

fps = cap.get(cv2.CAP_PROP_FPS)
if fps == 0 or fps is None:
    fps = 8

resize_width, resize_height = 600, 720
fourcc = cv2.VideoWriter_fourcc(*'mp4v')

# --- Parameters ---
pre_record_seconds = 5
post_record_seconds = 5
jam_confirm_frames = int(1.5 * fps)

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
prev_machine_on = machine_on
machine_restart_detected = False

cv2.namedWindow("Soap Jamming Detection", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Soap Jamming Detection", resize_width, resize_height)

while True:
    ret, frame = cap.read()
    if not ret or frame is None:
        print("End of video or failed to read frame")
        break

    roi_crop = frame[y1:y2, x1:x2]
    resized_frame = cv2.resize(frame, (resize_width, resize_height))

    pre_buffer.append(resized_frame)

    if machine_on:
        cv2.putText(resized_frame, "Machine ON", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

        results = model.predict(roi_crop, verbose=False)
        if len(results) > 0:
            probs = results[0].probs
            if probs is not None:
                class_id = int(probs.top1)
                class_name = results[0].names[class_id]
                last_detected_class = class_name

                if class_name != "nondefect":
                    jamming_frame_counter += 1
                else:
                    jamming_frame_counter = 0

                if jamming_frame_counter >= 1.5*fps:
                    colour = (0, 0, 255)
                    label = "Jam"
                else:
                    colour = (0, 255, 0)
                    label = "nondefect"

                cv2.putText(resized_frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, colour, 2, cv2.LINE_AA)
                cv2.rectangle(resized_frame, (x1, y1), (x2, y2), colour, 2)

                if not jamming_confirmed and jamming_frame_counter >= jam_confirm_frames:
                    jamming_confirmed = True
                    recording = True
                    stop_time = datetime.now()
                    print(f"[{stop_time.strftime('%H:%M:%S')}] Jamming CONFIRMED")
                    print("Wrote 3 to PLC.")
                    record_buffer.extend(pre_buffer)

        if jamming_confirmed:
            record_buffer.append(resized_frame)

    else:
        if jamming_confirmed and not machine_restart_detected:
            cv2.putText(resized_frame, "Clearing Jamming", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 165, 255), 2)
        else:
            cv2.putText(resized_frame, "Machine OFF", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

        if recording and jamming_confirmed and not recording_post_jam:
            print("Machine turned OFF during jamming — Waiting for restart")
            recording_post_jam = True
            post_jam_frame_count = 0

        if recording_post_jam:
            record_buffer.append(resized_frame)

    if recording_post_jam and machine_on and jamming_confirmed:
        if not machine_restart_detected:
            print("Machine restarted — Start post-jam recording")
            machine_restart_detected = True
        record_buffer.append(resized_frame)
        post_jam_frame_count += 1

        if post_jam_frame_count >= int(post_record_seconds * fps):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_out_path = os.path.join(output_folder, f"output_{timestamp}.mp4")
            out = cv2.VideoWriter(video_out_path, fourcc, fps, (resize_width, resize_height), True)

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

    cv2.imshow("Soap Jamming Detection", resized_frame)

    key = cv2.waitKey(20) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('m'):
        new_state = not machine_on
        print("Toggled machine to", "ON" if new_state else "OFF")
        machine_on = new_state

    prev_machine_on = machine_on

cap.release()
cv2.destroyAllWindows()
