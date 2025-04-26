from ultralytics import YOLO
import pycomm3
from pycomm3 import LogixDriver
import cv2
import os
import datetime
import numpy as np
import time
from ping3 import ping
import supporting_variables_cam_1
from collections import deque

# Initialize video and output settings
output_dir = r"New_Saved_Clips_1"
os.makedirs(output_dir, exist_ok=True)

frame_width, frame_height, fps = 640, 480, 5
frame_buffer = deque(maxlen=fps * 600)

# Event timestamp variables
machine_stop_time = None
door_open_time = None
machine_stopped_once = True
door_opened_once = True
recording_triggered = False

# PLC connection helpers
def reset_plc(plc, plc_ip="192.168.10.222"):
    try:
        if plc:
            plc.close()
        plc = LogixDriver(plc_ip)
        plc.open()
        print("Reconnected to PLC")
        plc.read(*supporting_variables_cam_1.variables)
        plc.read('cctv_fb.15')
    except Exception as e:
        print(f"Failed to reconnect to PLC: {e}")
    return plc

def initialize_plc(plc_ip="192.168.10.222"):
    try:
        plc = LogixDriver(plc_ip)
        plc.open()
        print("Connected to PLC")
        return plc
    except Exception as e:
        print(f"Failed to connect to PLC: {e}")
        return None

# Video writing

def get_output_path():
    return os.path.join(output_dir, f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.avi")

def save_video(start_time, end_time):
    if len(frame_buffer) == 0:
        print("Error: Frame buffer is empty.")
        return

    output_path = get_output_path()
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))
    frames_written = 0

    for frame_time, frame in list(frame_buffer):
        if start_time <= frame_time <= end_time:
            out.write(frame)
            frames_written += 1

    out.release()
    print(f"Clip saved: {output_path}, frames: {frames_written}")


def save_last_10_minutes():
    if not frame_buffer:
        print("Error: Frame buffer is empty.")
        return

    buffer_newest_time = frame_buffer[-1][0]
    start_time = max(buffer_newest_time - 600, frame_buffer[0][0])
    save_video(start_time, buffer_newest_time)


def extract_clip():
    if not machine_stop_time or not door_open_time:
        print("Error: Missing timestamps.")
        return

    if not frame_buffer:
        print("Error: Frame buffer is empty.")
        return

    start_time = max(machine_stop_time - 120, frame_buffer[0][0])
    end_time = min(door_open_time, frame_buffer[-1][0])

    if start_time >= end_time:
        print("Error: Start time must be before end time.")
        return

    save_video(start_time, end_time)


def record_event(event):
    global machine_stop_time, door_open_time, machine_stopped_once
    global door_opened_once, recording_triggered

    timestamp = time.time()
    now = datetime.datetime.now()

    if event == "stop" and machine_stopped_once:
        machine_stopped_once = False
        machine_stop_time = timestamp
        recording_triggered = False
        print(f"Machine stopped at: {now}")

    elif event == "door" and door_opened_once:
        if machine_stop_time and not recording_triggered:
            door_opened_once = False
            door_open_time = timestamp
            print(f"Door opened at: {now}")
            if door_open_time - machine_stop_time > 600:
                print("⚠ Warning: Door opened > 10 minutes after machine stop. Saving last 10 mins.")
                save_last_10_minutes()
                frame_buffer.clear()
            else:
                extract_clip()
            recording_triggered = True

    elif event == "close":
        door_opened_once = True
        print(f"Door closed at: {now}")

    elif event == "start":
        machine_stopped_once = True
        recording_triggered = False
        print(f"Machine started at: {now}")


def main_loop():
    global frame_width, frame_height, fps, frame_buffer

    while True:
        try:
            if ping("192.168.10.222") and ping("192.168.10.15"):
                plc = initialize_plc("192.168.10.222")
                if not plc:
                    print("Failed to initialize PLC")
                    return

                cap = cv2.VideoCapture("rtsp://admin:admin123@192.168.10.15:554")

                if cap.isOpened():
                    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = cap.get(cv2.CAP_PROP_FPS) or 5
                    frame_buffer = deque(maxlen=int(fps * 600))

                flag = 0
                machine_flag = 0

                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        continue

                    frame_buffer.append((time.time(), frame))

                    plc_data = plc.read(*supporting_variables_cam_1.variables)
                    plc_values = [d.value for d in plc_data] if plc_data else []
                    machine_status = plc.read('cctv_fb.15')

                    if not machine_status.value:
                        machine_flag = 1
                        record_event("stop")
                        if False in plc_values:
                            record_event("door")
                            flag = 1
                        elif flag:
                            record_event("close")
                            flag = 0
                    elif machine_flag:
                        record_event("start")
                        machine_flag = 0

            else:
                print("Camera or PLC not connected")
        except Exception as e:
            print(e)
            continue

main_loop()
