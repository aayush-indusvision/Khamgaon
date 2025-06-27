import cv2

# List to store clicked points
clicked_points = []

def click_event(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        print(f"Clicked at: ({x}, {y})")
        clicked_points.append((x, y))
        # Show a small circle where you clicked
        cv2.circle(img, (x, y), 5, (0, 255, 0), -1)
        cv2.imshow("Image", img)

# Load the image
image_path = r"video_5\frame_00000.jpg"  # Change this to your image path
img = cv2.imread(image_path)

if img is None:
    print("Failed to load image. Check the path.")
else:
    cv2.imshow("Image", img)
    cv2.setMouseCallback("Image", click_event)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    print("All clicked points:")
    for point in clicked_points:
        print(point)
