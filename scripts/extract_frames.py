import cv2
import os

# Path to the input video
video_path = r'assets\video_5.dav'

# Folder to save extracted frames
output_folder = r'video_5'
os.makedirs(output_folder, exist_ok=True)

# Open the video file
cap = cv2.VideoCapture(video_path)

frame_index = 0
saved_count = 0

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Save every 50th frame
    if frame_index % 1 == 0:
        frame_filename = os.path.join(output_folder, f'frame_{frame_index:05d}.jpg')
        cv2.imwrite(frame_filename, frame)
        saved_count += 1
        break

    frame_index += 1

cap.release()
print(f"Done! Extracted {saved_count} frames.")
