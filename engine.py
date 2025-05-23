import cv2
from static.areas import area_list,area_names
from utils.plc_control import *
import numpy as np
from static.variables import RTSP_LINK,PLC_IP
from utils.draw_lines import draw
from utils.utils import generate_empty_frame,check_hand_stationary,get_image_parameters
from ultralytics import YOLO

class DetectionAlgorithm():
    def __init__(self):

        self.model = YOLO(r"models\best.pt")

        self.plc = initialize_plc(PLC_IP)

        self.last_hand_positions = {}
        self.last_movement_frames = {}
        self.current_frame = 0
        self.area_time=[0.0 for _ in range(len(area_list))]
        self.send_data=[0 for _ in range(len(area_list))]
        self.hand_in_areas=[]

    def start(self):

        while True:
            cap = cv2.VideoCapture(r"assest\video1.mp4")

            if cap.isOpened():
                ret, frame = cap.read()

                while cap.isOpened():

                    try:
                        original_frame = frame.copy()
                        plc_data = read_values(self.plc)
                        width,height,fps = get_image_parameters(cap)

                        if ret:

                            frame=draw(frame)

                            if not plc_data.value:

                                machine_stop_duration_end=0
                                machine_stop_time=str(datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))
                                machine_stop_duration_start=datetime.datetime.now()  
                                names_and_points=[]
                                detected_hands=[]
                                results =self.model.predict(original_frame, conf=0.65, verbose=False,classes=[1])

                                for r in results:

                                    if r.boxes is not None and len(r.boxes) > 0:

                                        for box in r.boxes:
                                            box = box.xyxy[0].cpu().numpy()
                                            box_x1, box_y1, box_x2, box_y2 = box
                                            grid_x = int(((box_x1+box_x2)//2))
                                            grid_y = int(((box_y1+box_y2)//2))

                                            for area_id,work_area in enumerate(area_list):
                                                work_area=np.array(work_area)

                                                if cv2.pointPolygonTest(work_area, (grid_x,grid_y), False) >= 0:
                                                    names_and_points.append([box,area_id,work_area])
                                                    detected_hands.append(box)
                                                    cv2.rectangle(frame, (int(box_x1), int(box_y1)), (int(box_x2), int(box_y2)), (0,255,0), 2)
                                                    cv2.circle(frame, (grid_x,grid_y),5, (255,0,0), 2)
                                                    cv2.putText(frame, f"Hand", (int(box_x1), int(box_y1) - 5),cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)

                                if len(names_and_points)>=1:
                                    for box_and_name in names_and_points:
                                        hand=box_and_name[0]
                                        area_id=box_and_name[1]
                                        work_area=box_and_name[2]
                                        stationary_hands = check_hand_stationary(
                                                            detected_hands,
                                                            last_hand_positions,
                                                            last_movement_frames,
                                                            stationary_frame_count= 25,  # 5 seconds * 15 fps
                                                            movement_threshold=50,
                                                            current_frame=current_frame
                                                        )
                                    current_frame=current_frame+1
                                    for box_and_name in names_and_points:
                                        hand=box_and_name[0]
                                        area_id=box_and_name[1]
                                        work_area=box_and_name[2]   

                                        if len(box_and_name)>=1:

                                            if not np.any(np.isin(hand, stationary_hands)):
                                        
                                                self.area_time[area_id] += (1/fps)
                                                if self.area_time[area_id]>=1:
                                                    global_timer+=1/fps
                                                
                                                self.hand_in_areas.append(area_id)
                                                self.send_data[area_id]=1
                                                cv2.polylines(frame,[work_area], isClosed=True,color=(0, 255, 0),thickness=3)
                                            

                            else:
                                ind=[]
                                max_work_done=0
                                current_frame=0
                                last_hand_positions = {}
                                last_movement_frames = {}
                                ind = np.nonzero(self.area_time)[0].tolist()
                                machine_stop_duration_end=(datetime.datetime.now()-machine_stop_duration_start).total_seconds()
                                if len(ind)!=0:
                                    max_work_done=max(self.area_time)
                                    max_work_area=self.area_time.index(max_work_done) 
                                    if max_work_area == 1:
                                        state_new=self.plc.write("PLC_TAG",int(max_work_area))
                                    else:
                                        state_new=self.plc.write("PLC_TAG",int(max_work_area)+1)
                                    if state_new:
                                        print(f"Max work done in Area {max_work_area}: {area_names[max_work_area]}")
                                        max_work_area=0
                                 
                                print(f"Machine stopped at {machine_stop_time} for {machine_stop_duration_end} secnonds.")

                            frame=cv2.resize(frame,(640,640))
                            cv2.imshow("Hand Detection", frame)
                            if cv2.waitKey(1) & 0xFF == ord('q'):
                                break
                        
                        else:
                            image = generate_empty_frame(height,width)
                            cv2.imshow('Hand Detection', image)
                            if cv2.waitKey(1) & 0xFF == ord('q'):
                                break

                    except Exception as e:
                        print(e)

            cap.release()
            cv2.destroyAllWindows()

