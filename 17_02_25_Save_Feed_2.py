from ultralytics import YOLO
import pycomm3
from pycomm3 import LogixDriver
import cv2
import os
import datetime
import numpy as np
import time
from ping3 import ping
import supporting_variables_cam_2
from collections import deque

# Reset PLC connection
def reset_plc(plc, plc_ip="192.168.10.222"):
    try:
        if plc:
            plc.close()
        plc = LogixDriver(plc_ip)
        plc.open()
        print("Reconnected to PLC")
        plc.read(*supporting_variables_cam_2.variables)
        plc.read('cctv_fb.15')
    except Exception as e:
        print(f"Failed to reconnect to PLC: {e}")
        print("Not writing to PLC")
    return plc

# Initialize PLC connection
def initialize_plc(plc_ip="192.168.10.222"):
    try:
        plc = LogixDriver(plc_ip)
        plc.open()
        print("Connected to PLC")
        return plc
    except Exception as e:
        print(f"Failed to connect to PLC: {e}")
        return None

# Set up video storage path
output_dir = r"New_Saved_Clips_2"
os.makedirs(output_dir, exist_ok=True)

# Initialize event timestamps
machine_stop_time_new = None
door_open_time_new = None
door_close_time_new = None
machine_stopped_once_new = True
door_opened_once_new = True
machine_start_time_new = None
recording_triggered_new = False

# Placeholder values for video properties
frame_width, frame_height, fps = 640, 480, 5

# Initialize frame buffer
frame_buffer = deque(maxlen=fps * 600)  # Store last 10 minutes of frames

def save_last_10_minutes():
    global output_dir

    if len(frame_buffer) == 0:
        print("Error: Frame buffer is empty. No video to save.")
        return

    buffer_newest_time = frame_buffer[-1][0]
    start_time = max(buffer_newest_time - 600, frame_buffer[0][0])  # Last 10 minutes
    end_time = buffer_newest_time  # Up to the latest frame

    save_video(start_time, end_time)

# Function to save video between given timestamps
def save_video(start_time, end_time):
    global output_dir

    output_path = os.path.join(output_dir, f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.avi")
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))
    frames_written = 0

    for frame_time, frame in list(frame_buffer):
        if start_time <= frame_time <= end_time:
            out.write(frame)
            frames_written += 1

    out.release()

    if frames_written == 0:
        print("Error: No frames written. Check timestamps and buffer.")
    else:
        print(f"Clip saved as {output_path} with {frames_written} frames.")

# Define event recording function
def record_event(event):
    global machine_stop_time_new, door_open_time_new, door_close_time_new, machine_start_time_new
    global machine_stopped_once_new, door_opened_once_new, recording_triggered_new

    timestamp = time.time()
    new_time = datetime.datetime.now()

    if event == "stop" and machine_stopped_once_new:
        machine_stopped_once_new = False
        machine_stop_time_new = timestamp
        recording_triggered_new = False
        print(f"Machine Stopped at: {new_time}")

    elif event == "door" and door_opened_once_new:
        if machine_stop_time_new and not recording_triggered_new:
            door_opened_once_new = False
            door_open_time_new = timestamp
            print(f"Door Opened at: {new_time}")
            if door_open_time_new - machine_stop_time_new > 600:
                print("⚠ Warning: Door opened more than 10 minutes after machine stopped! ⚠")
                print("Saving last 10 minutes of video and clearing frame buffer.")
                save_last_10_minutes()
                frame_buffer.clear()
            else:
                extract_clip()
            recording_triggered_new = True

    elif event == "close":
        door_opened_once_new = True
        door_close_time_new = timestamp
        print(f"Door Closed at: {new_time}")

    elif event == "start":
        machine_stopped_once_new = True
        machine_start_time_new = timestamp
        recording_triggered_new = False
        print(f"Machine Started at: {new_time}")

# Function to extract video clips
def extract_clip():
    global machine_stop_time_new, door_open_time_new

    if not machine_stop_time_new or not door_open_time_new:
        print("Error: Missing timestamps.")
        return

    if len(frame_buffer) == 0:
        print("Error: Frame buffer is empty.")
        return

    buffer_oldest_time = frame_buffer[0][0]
    buffer_newest_time = frame_buffer[-1][0]

    start_time = max(machine_stop_time_new - 120, buffer_oldest_time)
    end_time = min(door_open_time_new, buffer_newest_time)

    print(f"Extracting video from {start_time} to {end_time}...")

    if start_time >= end_time:
        print("Error: Start time must be before end time.")
        return

    output_path = os.path.join(output_dir, f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.avi")

    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))
    frames_written = 0

    for frame_time, frame in list(frame_buffer):
        if start_time <= frame_time <= end_time:
            out.write(frame)
            frames_written += 1

    out.release()

    if frames_written == 0:
        print("Error: No frames written. Check timestamps and buffer.")
    else:
        print(f"Clip saved as {output_path} with {frames_written} frames.")

# Main loop
def main_loop():
    global frame_width, frame_height, fps, frame_buffer
    while True:
        try:
            if (ping("192.168.10.222") is not None) and (ping("192.168.10.16") is not None):
                plc = initialize_plc("192.168.10.222")
                if not plc:
                    print("Failed to initialise PLC")
                    return

                video_path = "rtsp://admin:admin123@192.168.10.16:554"
                cap = cv2.VideoCapture(video_path)

                if cap.isOpened():
                    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = cap.get(cv2.CAP_PROP_FPS) or 5
                    frame_buffer = deque(maxlen=int(fps * 600))

                flag_new = 0
                machine_flag_new = 0

                while cap.isOpened():
                    ret, frame = cap.read()
                    if ret:
                        frame_time = time.time()
                        frame_buffer.append((frame_time, frame))

                        plc_data = plc.read(*supporting_variables_cam_2.variables)
                        plc_values = [data.value for data in plc_data] if plc_data else []
                        machine_status = plc.read('cctv_fb.15')

                        if not machine_status.value:
                            machine_flag_new = 1
                            record_event("stop")

                            if False in plc_values:
                                record_event("door")
                                flag_new = 1
                            elif flag_new == 1:
                                record_event("close")
                                flag_new = 0

                        elif machine_flag_new == 1:
                            record_event("start")
                            machine_flag_new = 0
                    else:
                        continue
            else:
                print("Camera or PLC not connected")
        except Exception as e:
            print(e)
            continue

main_loop()
