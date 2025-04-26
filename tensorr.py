from ultralytics import YOLO

# Load the YOLOv8 model
model = YOLO(r"C:\Users\pc\Desktop\Khamgaon_Analytics\08_10_24_Cam_1.pt")
print(model)

# Export the model to TensorRT format
model.export(format="engine", batch=1,half=True)  # creates 'yolov8n.engine'

# Load the exported TensorRT model
tensorrt_model = YOLO(r"08_10_24_Cam_1.engine",task='segment')

# Run inference
# results = tensorrt_model(r"C:\Users\pc\Desktop\Open_pouch_model-20240830T104935Z-001\Open_pouch_model\images_0609")