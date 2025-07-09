import cv2, threading, os
from pycomm3 import LogixDriver
from ultralytics import YOLO
from collections import deque
from datetime import datetime
import time, csv

x1, y1, x2, y2 = 0, 100, 350, 350

PLC_IP_ADDRESS = '192.168.10.222'
PLC_STATUS_TAG = 'Spiral_5_CCTV_Read.14'
PLC_WRITE_TAG = 'ABM_5_AI_CAMERA_READ_INT[1]'

plc_client = None
plc_client_on = False
plc_lock = threading.Lock()

def initialize_plc(ip):
    global plc_client, plc_client_on
    with plc_lock:
        try:
            plc_client = LogixDriver(ip)
            plc_client.open()
            plc_client_on = True
            print(f"Connected to PLC at {ip}")
        except Exception as e:
            print("PLC Init Error:", e)
            plc_client_on = False

def reset_plc(ip):
    global plc_client, plc_client_on
    with plc_lock:
        try:
            if plc_client:
                plc_client.close()
                time.sleep(0.5)  
            plc_client = LogixDriver(ip)
            plc_client.open()
            plc_client_on = True
            print("PLC Reconnected")
        except Exception as e:
            print("PLC Reconnect Failed:", e)
            plc_client_on = False

def read_machine_status():
    with plc_lock:
        try:
            if plc_client_on and plc_client:
                status = plc_client.read(PLC_STATUS_TAG)
                if status is not None:
                    return status.value
                else:
                    print("Status is None, trying reconnect...")
                    reset_plc(PLC_IP_ADDRESS)
        except Exception as e:
            print("PLC Read Error:", e)
            reset_plc(PLC_IP_ADDRESS)
            return False
    return False

def put_text_with_background(frame, text, position, font, font_scale, text_color, thickness):
    (tw, th), base = cv2.getTextSize(text, font, font_scale, thickness)
    x, y = position
    bg_color = (0, 0, 0)
    cv2.rectangle(frame, (x, y - th - base), (x + tw, y + base), bg_color, -1)
    cv2.putText(frame, text, position, font, font_scale, text_color, thickness)

model_path = r"C:\Users\pc\Desktop\soap_count\classify02.pt"
model = YOLO(model_path)

input_path = "rtsp://admin:admin@123@192.168.10.19:554"
output_folder = r"C:\Users\pc\Desktop\soap_count\Soap_jamming"
os.makedirs(output_folder, exist_ok=True)

log_path = os.path.join(output_folder, "Jamming.csv")
if not os.path.exists(log_path):
    with open(log_path, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Stop Count", "Stop Time", "Start Time", "Duration (seconds)"])

initialize_plc(PLC_IP_ADDRESS)

cap = cv2.VideoCapture(input_path)
if cap is None or not cap.isOpened():
    print("Error opening video stream")
    exit()

fps = cap.get(cv2.CAP_PROP_FPS)
if fps == 0 or fps is None:
    fps = 8

resize_width, resize_height = 600, 720
fourcc = cv2.VideoWriter_fourcc(*'mp4v')

pre_stop_buffer = deque(maxlen=int(fps * 60))
post_stop_buffer = []
collect_post_stop = False
post_stop_frame_count = 0
post_stop_target = int(fps * 60)

prev_machine_on = False
last_detected_class = None
stop_time = None
stop_counter = 0

cv2.namedWindow("Soap Jamming Detection", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Soap Jamming Detection", resize_width, resize_height)

while True:
    ret, frame = cap.read()
    if not ret or frame is None:
        print("Failed to read frame")
        continue

    machine_on = read_machine_status()
    if machine_on not in [True, False]:
        machine_on = False  

    roi_crop = frame[y1:y2, x1:x2]
    resized_frame = cv2.resize(frame, (resize_width, resize_height))

    if machine_on == True:
        put_text_with_background(resized_frame, "Machine ON", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

        results = model.predict(roi_crop, verbose=False)
        if len(results) > 0:
            probs = results[0].probs
            if probs is not None:
                class_id = int(probs.top1)
                confidence = float(probs.top1conf)
                class_name = results[0].names[class_id]
                last_detected_class = class_name
                label = f"{class_name}"
                colour1 = (0, 255, 0) if class_name == "nondefect" else (0, 0, 255)
                cv2.putText(resized_frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, colour1, 2, cv2.LINE_AA)
                cv2.rectangle(resized_frame, (x1, y1), (x2, y2), colour1, 2)

        if resized_frame is not None:
            pre_stop_buffer.append(resized_frame)

        if collect_post_stop is True:
            post_stop_buffer.clear()
            collect_post_stop = False
            post_stop_frame_count = 0
            if stop_time:
                start_time = datetime.now()
                duration = (start_time - stop_time).total_seconds()
                stop_counter += 1
                with open(log_path, mode='a', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow([stop_counter, stop_time.strftime('%Y-%m-%d %H:%M:%S'),
                                     start_time.strftime('%Y-%m-%d %H:%M:%S'), int(duration)])

    else:
        put_text_with_background(resized_frame, "Machine OFF", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

        if prev_machine_on is True:
            collect_post_stop = True
            post_stop_buffer = []
            post_stop_frame_count = 0
            stop_time = datetime.now()

            if last_detected_class != "nondefect" and last_detected_class is not None:
                try:
                    with plc_lock:
                        plc_client.write(PLC_STATUS_TAG, 3)
                        print("Wrote 3 to PLC.")
                except Exception as e:
                    print("Error writing to PLC:", e)

        if collect_post_stop:
            post_stop_buffer.append(resized_frame)
            post_stop_frame_count += 1

            if post_stop_frame_count >= post_stop_target:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                video_path = os.path.join(output_folder, f"output_{timestamp}.mp4")
                out = cv2.VideoWriter(video_path, fourcc, fps, (resize_width, resize_height), True)

                if out.isOpened():
                    for f in list(pre_stop_buffer) + post_stop_buffer:
                        out.write(f)
                    out.release()
                    print("Video saved in:", video_path)
                else:
                    print("Error opening VideoWriter")

                collect_post_stop = False
                post_stop_buffer.clear()
                pre_stop_buffer.clear()

    cv2.imshow("Soap Jamming Detection", resized_frame)
    prev_machine_on = machine_on

    if cv2.waitKey(8) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
