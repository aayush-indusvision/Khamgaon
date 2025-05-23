import cv2
from static.areas import area_draw


def draw(frame):
    for (start_x, start_y, end_x, end_y) in area_draw:
        cv2.line(frame, (start_x, start_y), (end_x, end_y), (0,0,255), 2)

    return frame
