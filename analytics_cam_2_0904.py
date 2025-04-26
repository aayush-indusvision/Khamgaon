from ultralytics import YOLO
import cv2
import pycomm3
from pycomm3 import LogixDriver
import os
import supporting_variables_cam_2
import numpy as np
from dashboard import *
import time as tim
from collections import deque

OUTPUT_DIR = r"Working_Saved_Clips_2"
os.makedirs(OUTPUT_DIR, exist_ok=True)

video_writer = None
is_recording = False

model = YOLO("17_10_24_Cam_2.pt")
dash=Dashboard_glob(url='http://localhost:8000/api/dashboard/')
dash_downtime=Dashboard_downtime(url='http://localhost:8000/api/downtime-analysis/')


time_unit = "second"


# output_path = "1_8_24_output_2_with_grid_glove_camera_1_part_2.mp4"
# fourcc = cv2.VideoWriter_fourcc(*'mp4v')
# out = cv2.VideoWriter(output_path, fourcc, int(fps), (frame_width, frame_height))


areas=[]

# lines = [
#     [(4,334),(4,818),(344,806),(342,334)],
#     [(342,334),(344,579),(885,563),(885,334)],
#     [(344,579),(344,878),(941,877),(940,694),(889,690),(885,566)],
#     [(682,4),(688,333),(841,333),(841,4)],
#     [(885,336),(889,690),(939,692),(941,744),(1114,744),(1109,462),(1057,460),(1053,334)],
#     [(941,744),(943,1012),(1157,1005),(1148,746)],
#     [(1050,4),(1053,242),(1458,235),(1445,4)],
#     [(1053,243),(1057,459),(1391,459),(1382,238)],
#     [(1109,462),(1114,742),(1404,742),(1391,458)],
#     [(1149,746),(1160,1073),(1493,1073),(1489,685),(1404,694),(1404,741)],
#     [(1382,240),(1402,694),(1790,644),(1740,234)],
#     [(421,160),(420,333),(688,333),(684,160)]
# ]

lines=[
        [(0,269),(0,746),(212,746),(212,269)],
        [(212,269),(212,495),(733,470),(733,269)],
        [(212,495),(212,846),(808,829),(790,589),(730,589),(733,470)],
        [(544,0),(544,269),(668,269),(668,0)],
        [(733,269),(733,589),(790,589),(795,647),(964,647),(950,381),(910,381),(910,269)],
        [(795,647),(820,927),(980,927),(980,1078),(1200,1078),(1200,830),(1076,830),(1076,640)],
        [(910,0),(910,124),(1349,124),(1349,0)],
        [(910,124),(910,381),(1230,381),(1220,124)],
        [(950,381),(964,645),(1246,635),(1230,381)],
        [(1076,640),(1076,830),(1200,830),(1200,1078),(1333,1078),(1333,606),(1244,606),(1244,635)],
        [(1220,125),(1244,606),(1630,593),(1623,120)],
        [(306,82),(306,269),(544,269),(544,72)]
]


lines_draw=[
        (0,269,0,746),(0,746,212,746),(212,746,212,269),(212,269,0,269), ##AREA 1
        (212,269,212,495),(212,495,733,470),(733,470,733,269),(733,269,212,269), ##AREA 2
        (212,495,212,846),(212,846,808,829),(808,829,790,589),(790,589,730,589),(730,589,733,470),(733,470,212,495), ##AREA 3
        (544,0,544,269),(544,269,668,269),(668,269,668,0),(668,0,544,0), ##AREA 4
        (733,269,733,589),(733,589,790,589),(790,589,795,647),(795,647,964,647),(964,647,950,381),(950,381,910,381),(910,381,910,269),(910,269,733,269), ##AREA 5
        (795,647,820,927),(820,927,980,927),(980,927,980,1078),(980,1078,1200,1078),(1200,1078,1200,830),(1200,830,1076,830),(1076,830,1076,640),(1076,640,795,647), ##AREA 6
        (910,0,910,124),(910,124,1349,124),(1349,124,1349,0),(1349,0,910,0), ##AREA 7
        (910,124,910,381),(910,381,1230,381),(1230,381,1220,124),(1220,124,910,124), ##AREA 8
        (950,381,964,645),(964,645,1246,635),(1246,635,1230,381),(1230,381,950,381), ##AREA 9
        (1076,640,1076,830),(1076,830,1200,830),(1200,830,1200,1078),(1200,1078,1333,1078),(1333,1078,1333,606),(1333,606,1244,606),(1244,606,1244,635),(1244,635,1076,640), ##AREA 10
        (1220,125,1244,606),(1244,606,1630,593),(1630,593,1623,120),(1623,120,1220,125), ##AREA 11
        (306,82,306,269),(306,269,544,269),(544,269,544,72),(544,72,306,82)
]

fps=5

area_roi=np.array([(595,0),(602,268),(700,265),(691,0)],dtype=np.int32)

area_names=['Side heater','Packing table','Plough','Pincer','Folder and bottom elevation','Knife assembly','Pocketed belt','Top elevator','Gripper finger','Paper feed assembly','Gripper guard','Manual Rotating Assembly']

area_timing_ref=[90,120,60,0.1,120,90,60,0.1,60,120,60,0.1]

major_or_minor_stop=[False for _ in range(len(lines))]
minor_stopage=[0 for _ in range(len(lines))]
major_stopage=[0 for _ in range(len(lines))]
area_time_total=[0.0 for _ in range(len(lines))]
area_time=[0.0 for _ in range(len(lines))]
area_time_global=[0.0 for _ in range(len(lines))]
area_time_copy=[0.0 for _ in range(len(lines))]

send_data=[0 for _ in range(len(lines))]
send_data_global=[0 for _ in range(len(lines))]

for i in lines:
    areas.append(np.array(i))

def start_recording(frame_size, fps=5):
    global video_writer, is_recording

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"door_open_{timestamp}.avi"
    output_path = os.path.join(OUTPUT_DIR, filename)

    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    video_writer = cv2.VideoWriter(output_path, fourcc, fps, frame_size)
    is_recording = True

    print(f"[RECORDING] Started: {filename}")

def stop_recording():
    global video_writer, is_recording

    if video_writer:
        video_writer.release()
        video_writer = None
        print(f"[RECORDING] Stopped and saved.")
    is_recording = False

def reset_plc(plc, plc_ip="192.168.10.222"):
    try:
        if plc:
            plc.close()
        plc = LogixDriver(plc_ip)
        # plc = CIPDriver(plc_ip)
        plc.open()
        print("Reconnected to PLC")
        # plc_data = plc.read(*supporting_variables_cam_2.variables)
    except Exception as e:
        print(f"Failed to reconnect to PLC: {e}")
        print(f"Not writing to plc")
        
    return plc

def toggle_plc_trigger(plc, plc_ip="192.168.10.222"):
    max_retries = 3
    delay_between_attempts = timedelta(milliseconds=10)  # 100 ms delay between attempts

    for retry in range(max_retries):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            
            plc_data = plc.read(*supporting_variables_cam_2.variables)
            if plc_data:
                print("Reading Values")
                break
            else:
                plc_data=None
                print("Failed to read values")
        except Exception as e:
            print(f"Error writing to PLC at {timestamp}: {e}")
        print(f"Retry {retry + 1}/{max_retries}")
        wait_until = datetime.now() + delay_between_attempts
        while datetime.now() < wait_until:
            pass  # Busy wait
        plc= reset_plc(plc, plc_ip)
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
    
def check_hand_stationary(current_bboxes, last_hand_positions, last_movement_frames, 
                           stationary_frame_count=75, movement_threshold=10, current_frame=0):
    """
    Check which hands have not moved for more than the specified number of frames and return their bounding box coordinates.

    Args:
        current_bboxes (list of lists): List where each entry is a list of bounding box coordinates [x1, y1, x2, y2].
        last_hand_positions (dict): Dictionary with indices as keys and last known positions as values.
        last_movement_frames (dict): Dictionary with indices as keys and the last frame movement was detected.
        stationary_frame_count (int): Number of frames to consider the hand as stationary.
        movement_threshold (float): Distance in pixels to determine if movement has occurred.
        current_frame (int): The current frame number.

    Returns:
        list of lists: List of bounding boxes for hands that have not moved for more than the specified number of frames.
    """
    stationary_hands = []
    # Iterate over the list of current bounding boxes
    for idx, bbox in enumerate(current_bboxes):
        # Calculate the center of the bounding box
        center_x = (bbox[0] + bbox[2]) / 2
        center_y = (bbox[1] + bbox[3]) / 2
        current_hand_position = (center_x, center_y)

        if idx in last_hand_positions:
            last_position = last_hand_positions[idx]
            distance = np.linalg.norm(np.array(current_hand_position) - np.array(last_position))
            
            if distance < movement_threshold:
                # Check if the hand has been stationary for the required number of frames
                if current_frame - last_movement_frames[idx] >= stationary_frame_count:
                    stationary_hands.append(bbox)
            else:
                last_movement_frames[idx] = current_frame
        else:
            # Initialize tracking for new hand detection
            last_hand_positions[idx] = current_hand_position
            last_movement_frames[idx] = current_frame

        # Update the position
        last_hand_positions[idx] = current_hand_position

    # Handle hands that are not detected in this frame
    detected_indices = set(range(len(current_bboxes)))
    for idx in list(last_hand_positions.keys()):
        if idx not in detected_indices:
            # If hand is not detected, check if it has been stationary for the duration
            if current_frame - last_movement_frames.get(idx, 0) >= stationary_frame_count:
                # Optionally add bounding box of the stationary hand if it was previously tracked
                if idx < len(current_bboxes):
                    stationary_hands.append(current_bboxes[idx])
            # Update the last detection frame to keep tracking
            last_movement_frames[idx] = current_frame

    return stationary_hands
    
total_major_stoppage=0.0
total_minor_stoppage=0.0
door_flag=0
door_open_close_count=[]
machine_status_flag=0
door_open_close_time=[]
tracked_gloves = []
hand_in_areas=[]
cam_flag=0
current_frame = 0
door_open_close_count=[0 for _ in range(5)]
door_open_close_time=[0.0 for _ in range(5)]
door_open_close_time_global=[0.0 for _ in range(5)]
last_hand_positions = {}
last_movement_frames = {}

def main_loop():
    
    global is_recording

    global last_hand_positions
    global last_movement_frames
    global current_frame
    global total_major_stoppage
    global total_minor_stoppage
    global door_flag
    global door_open_close_time_global
    global machine_status_flag
    global area_time
    global send_data
    global cam_flag
    global machine_stop_time
    global machine_status_flag
    global area_time_global
    global area_time_copy
    global door_open_close_count
    global door_open_close_time
    global hand_in_areas
    global tracked_gloves
    global door_open_close_count
    global door_open_close_time
    shift_wise_area_time=[0.0 for _ in range(len(lines))]
    hand_in_areas=[]
    area_time_global=[0.0 for _ in range(len(lines))]
    send_data_global=[0 for _ in range(len(lines))]
    global_timer=0.0
    total_work_time=0.0
    
    plc=initialize_plc("192.168.10.222")
    if not plc:
        print("Failed to initialise PLC")
    
        # return
    while True:
        cam_flag=0
        video_path = "rtsp://admin:admin123@192.168.10.16:554"
        #video_path = r"C:\Users\pc\Desktop\20240720_154118.mp4"
        
        cap = cv2.VideoCapture(video_path)
        
        if cap.isOpened():
            
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
            fps = cap.get(cv2.CAP_PROP_FPS) or 5
            frame_size = (width, height)
            
            # print(frame_width,frame_height)
            while cap.isOpened():
              
                ret, frame = cap.read()
                # cv2.imwrite("new_img.jpg",frame)
                cam_flag=0
                try:
                    
                    plc_data= plc.read(*supporting_variables_cam_2.variables)
                    # print(plc_data)
                    machine_status=plc.read('cctv_fb.15')
                   
                    # dummy_1=plc.read('WRA_5_Machine_Status_Stopped')
                    # dummy_2=plc.read('WRA_5_Machine_Status_Running')
                    # print(dummy_1,dummy_2)
                    
                    if ret:
                        cam_flag=1
                        for (start_x, start_y, end_x, end_y) in lines_draw:
                                cv2.line(frame, (start_x, start_y), (end_x, end_y), (0,0,255), 3)
                       
                        # cv2.imwrite("new_img.jpg",frame)
                        # print("Machine status : ",machine_status)
                        if not machine_status.value:
                           
                            if machine_status_flag==0:
                                
                                machine_status_flag=1
                                machine_stop_time=str(datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))
                                machine_stop_duration=0

                                machine_stop_duration=datetime.now()
                            n = len(plc_data)
                            
                            plc_values = []
                            for i in range(0, n) :
                                plc_values.append(plc_data[i].value)
                            plc_values = np.array(plc_values)
                            # print("PLC values : ",plc_values)
                            
                            
                            if False in plc_values:
                                if not is_recording:
                                    start_recording(frame_size, fps)
                                names=[]
                                names_and_points=[]
                                detected_hands = []
                                for idx,i in enumerate(plc_values):
                                    # print("Hello")
                                    if i==False:
                                        door_open_close_time[idx]+=(1/fps)
                                        # print(door_open_close_time[idx])
                                        if door_flag==2 or door_flag==0:
                                            door_open_close_count[idx]+=1
                                door_flag=1
                                
                                results = model.predict(source=frame, show=False, conf=0.3, save=False, stream=True,verbose=False,classes=[1,2])
                                
                                box_and_cls=[]
                                for result in results:
                                    
                                    if len(result.boxes.xyxy)!=0:
                                       
                                        len_2=list(result.boxes.cls).count(2)
                                        len_1=list(result.boxes.cls).count(1)
                                        for i in result.boxes:
                                            box_and_cls.append([i.xyxy[0],i.cls])
                                        # for cls,box in zip(result.boxes.cls,result.boxes.xyxy):
                                        for i in box_and_cls:
                                            box = i[0].cpu().numpy() if hasattr(i[0], 'cpu') else i[0].numpy() if hasattr(i[0], 'numpy') else i[0]
                                            cls=i[1].item()
                                            x1, y1, x2, y2 = box
                                            grid_x = int(((x1+x2)//2))
                                            grid_y=int((y1+y2)//2)
                                            cv2.circle(frame, (grid_x,grid_y),5, (255,0,0), 2)
                                            for area_id,work_area in enumerate(areas):
                                                # i.reshape((-1,1,2))
                                                if cv2.pointPolygonTest(work_area, (grid_x,grid_y), False) >= 0:
                                                    
                                            # print(box,cls.item())
                                            # print(result.boxes.cls)
                                            
                                                    # if (cls==0.) and (len_2<2) and (len_1<2) and (cv2.pointPolygonTest(area_roi, (int(box[2]),int(box[3])), False) >= 0):
                                                        
                                                    #     names_and_points.append([box,area_id,work_area])
                                                    #     names.append('hand_under_machine')
                                                    #     detected_hands.append(box)
                                                       
                                                    if cls == 1.:
                                                    
                                                        names_and_points.append([box,area_id,work_area])
                                                        names.append('bare_hand')
                                                        detected_hands.append(box)
                                                       
                                                    if cls == 2.:
                                                    
                                                        names_and_points.append([box,area_id,work_area])
                                                        names.append('gloves')
                                                        detected_hands.append(box)
                                                        
                                if len(names)>=1:
                                    for box_and_name in names_and_points:
                                        hand=box_and_name[0]
                                        area_id=box_and_name[1]
                                        work_area=box_and_name[2]
                                        stationary_hands = check_hand_stationary(
                                                            detected_hands,
                                                            last_hand_positions,
                                                            last_movement_frames,
                                                            stationary_frame_count= 25,  # 5 seconds * 15 fps
                                                            movement_threshold=30,
                                                            current_frame=current_frame
                                                        )
                                    current_frame=current_frame+1
                                    for box_and_name in names_and_points:
                                        hand=box_and_name[0]
                                        area_id=box_and_name[1]
                                        work_area=box_and_name[2]

                                        
                                    # if hand_track([hand])==False:
                                        if len(box_and_name)>=1:    
                                            if not np.any(np.isin(hand, stationary_hands)):
                                                area_time[area_id] += (1 / fps)  # Accumulate time spent in this grid cell
                                                # print("Before",area_time_copy[area])
                                                if area_time[area_id]>=1:
                                                    global_timer+=1/fps
                                                    # print("After",area_time_copy[area])
                                                
                                                
                                                    # if not n:
                                                    if area_id==11:
                                                        state=plc.write(f"CCTV_BOOL.18",True)
                                                    else:
                                                        state=plc.write(f"CCTV_BOOL.{area_id+1}",True)
                                                    if state:
                                                        if area_id==11:
                                                            print(f"Writing area 18 time to PLC") 
                                                        else:
                                                            print(f"Writing area {area_id+1} time to PLC") 
                                                    # print(area)
                                                    hand_in_areas.append(area_id)
                                                    send_data[area_id]=1
                                                    #cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                                                    cv2.polylines(frame,[work_area], isClosed=True,color=(0, 255, 0), thickness=3)

                                                    # if time_unit == "second":
                                                    time_spent = area_time[area_id]
                                                    # else:
                                                    #     time_spent = area_time_copy[area] * 1000  # Convert seconds to milliseconds
                                                    
                                                    
                                                    
                                                    cv2.putText(frame,f"Detected in {area_names[area_id]} for {time_spent:.2f} {time_unit}",(50,int(50*area_id*0.5)),cv2.FONT_HERSHEY_COMPLEX,1,(0,255,0),2,cv2.LINE_AA)

                                                    # print(f"Detected {box_and_name[0]} in Area {area_names[area]} for {time_spent:.2f} {time_unit}")
                                                else:
                                                    
                                                    if area_id==11:
                                                        state=plc.write(f"CCTV_BOOL.18",False)
                                                    else:
                                                        state=plc.write(f"CCTV_BOOL.{area_id+1}",False)
                                            else:
                                                
                                                if area_id==11:
                                                    state=plc.write(f"CCTV_BOOL.18",False)
                                                else:
                                                    state=plc.write(f"CCTV_BOOL.{area_id+1}",False)
                                        else:
                                                
                                                if area_id==11:
                                                    state=plc.write(f"CCTV_BOOL.18",False)
                                                else:
                                                    state=plc.write(f"CCTV_BOOL.{area_id+1}",False)

                                if is_recording and video_writer:
                                    video_writer.write(frame)
                                # else:
                                #     if area==11:
                                #         state=plc.write(f"CCTV_BOOL.18",False)
                                #     else:
                                #         state=plc.write(f"CCTV_BOOL.{area+1}",False)

                                    # area_time_copy[i]=0.0  
                                    
                            else:
                                # print("Door is closed")
                                if door_flag==1:
                                    stop_recording()
                                    ind=[]
                                    max_work_done=0
                                    max_work_area=0
                                    current_frame=0
                                    last_hand_positions = {}
                                    last_movement_frames = {}
                                    # print("Inside door_flag")
                                    myfile = open('camera_2_door_time_27_8_24.txt', 'a')
                                    myfile_work = open('analytics.txt', 'a')
                                    ind = np.nonzero(area_time)[0].tolist()
                                    if len(ind)!=0:
                                        max_work_done=max(area_time)
                                        max_work_area=area_time.index(max_work_done) 
                                        if max_work_area==11:
                                            state_new=plc.write("WRA_5_CCTV_Fault",18)
                                        else:
                                            state_new=plc.write("WRA_5_CCTV_Fault",int(max_work_area)+1)
                                        if state_new:
                                            if max_work_area==11:
                                                print(f"Max work done in 18")
                                            else:
                                                print(f"Max work done in {max_work_area+1}")
                                            max_work_area=0
                                    for idx in hand_in_areas:
                                        
                                                            
                                        if send_data[idx]==1:
                                            shift_wise_area_time[idx]+=area_time[idx]
                                            send_data_global[idx]=send_data[idx]
                                            if area_time[idx]>=area_timing_ref[idx]:
                                                
                                                major_stopage[idx]+=1
                                                
                                                total_major_stoppage+=area_time[idx]
                                                print(f"Major stopage in {area_names[idx]}")
                                                print(area_names[idx],area_time[idx],(global_timer/area_time[idx])*100)
                                                
                                                if idx==11:
                                                    dash.send_time(2,18,float(area_time[idx]),2)
                                                    # continue            
                                                    # state=plc.write("CCTV_FB_Time[18]",float(area_time[idx+1]))
                                                    
                                                    # if state:
                                                    #     print(f"Writing total time to PLC id 18 major")
                                                else:
                                                    dash.send_time(2,idx+1,float(area_time[idx]),2)
                                                    # state=plc.write(f"CCTV_FB_Time[{idx}]",float(area_time[idx+1]))
                                                    
                                                    # if state:
                                                    #     print(f"Writing total time to PLC id {idx} major")
                                                 #ADD MAJOR TO SEND MAJOR STOPPAGE
                                            
                                                
                                            else:
                                                minor_stopage[idx]+=1
                                                
                                                
                                                total_minor_stoppage+=area_time[idx]
                                                print(f"Minor stopage in {area_names[idx]}")
                                                print(area_names[idx],area_time[idx],(global_timer/area_time[idx])*100)
                                                if idx==11:
                                                    dash.send_time(2,18,float(area_time[idx]),1)
                                                    # state=plc.write("CCTV_FB_Time[18]",float(area_time[idx+1]))
                                                    # if state:
                                                    #     print("Writing total time to PLC id 18 minor")
                                                    # else:
                                                    #     print("Couldn't write in area 18 minor")
                                                    # continue
                                                else:
                                                    dash.send_time(2,idx+1,float(area_time[idx]),1)
                                                    # state=plc.write(f"CCTV_FB_Time[{idx}]",float(area_time[idx+1]))
                                                    # if state:
                                                    #     print(f"Writing total time to PLC id {idx} minor")
                                                    # else:
                                                    #     print("Couldn't write in area 17 major")
                                                 #ADD MINOR TO SEND MINOR STOPPAGE
                                        if send_data[idx]==1:        
                                            myfile_work.write(f"{area_names[idx]}: {area_time[idx]} seconds at {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}\n")
                                            print(f"{area_names[idx]}: {area_time[idx]} seconds at {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}") 
                                        total_work_time+=area_time[idx]  
                                        area_time_total[idx]+=area_time[idx]
                                        area_time_global[idx]+=area_time[idx]
                                        area_time_copy[idx]=0 
                                        send_data[idx]=0
                                        area_time[idx]=0
                                       
                                    myfile_work.write(f"Total work done: {total_work_time} seconds at {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}\n")
                                    print(f"Total work done: {total_work_time} seconds at {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}")
                                    myfile_work.write(f"Max work done in machine: {max_work_done} seconds at {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}\n")
                                    print(f"Max work done in machine: {max_work_done} seconds at {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}")

                                    for idx,time_1 in enumerate(door_open_close_time):
                                        if time_1>0:
                                            if idx==3:
                                                print(f"Door 13 was open for {time_1} seconds")
                                                myfile.write(f"Door 13 was open for {time_1} at {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}\n")
                                            else:
                                                print(f"Door {idx+1} was open for {time_1} seconds")
                                                myfile.write(f"Door {idx+1} was open for {time_1} at {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}\n")
                                            door_open_close_time_global[idx]=time_1
                                        door_open_close_time[idx]=0.0
                                    myfile.close()
                                    # door_flag=2


                                            
                            # if ((datetime.now().hour == 7 and datetime.now().minute==0 and datetime.now().second==1) and (total_minor_stoppage!=0.0 or total_major_stoppage!=0.0)) or ((datetime.now().hour == 15 and datetime.now().minute==0 and datetime.now().second==1) and (total_minor_stoppage!=0.0 or total_major_stoppage!=0.0)) or ((datetime.now().hour == 23 and datetime.now().minute==0 and datetime.now().second==1) and (total_minor_stoppage!=0.0 or total_major_stoppage!=0.0)): 
                                if(door_flag==1):
                                    
                                    # for serial in range(len(shift_wise_area_time)):
                                    #     if (int(shift_wise_area_time[serial])!=0):
                                    #         if serial == 11:
                                    #             state=plc.write("CCTV_FB_Time[17]",float(shift_wise_area_time[serial]))
                                    #             if state:
                                    #                 print("Writing total time to PLC id 17")
                                    #             shift_wise_area_time[serial]=0
                                    #             tim.sleep(10)
                                    #             state_2=plc.write("CCTV_FB_Time[17]",0.0)
                                    #             if state_2:
                                    #                 print("Reset")
                                    #         elif serial == 6:
                                    #             # state=plc.write("CCTV_FB_Time[6]",float(shift_wise_area_time[serial]))
                                    #             # if state:
                                    #             #     print("Writing total time to PLC id 17")
                                    #             # shift_wise_area_time[serial]=0
                                    #             # tim.sleep(10)
                                    #             state_2=plc.write("CCTV_FB_Time[6]",0.0)
                                    #             if state_2:
                                    #                 print("Reset")
                                            
                                    #         else:
                                    #             state=plc.write(f"CCTV_FB_Time[{serial}]",float(shift_wise_area_time[serial]))
                                    #             if state:
                                    #                 print(f"Writing total time to PLC id {serial} minor")
                                    #             shift_wise_area_time[serial]=0
                                    #             tim.sleep(10)
                                    #             state_2=plc.write(f"CCTV_FB_Time[{serial}]",0.0)
                                    #             if state_2:
                                    #                 print("Reset")
                                      
                                    myfile = open('camera_2_major_minor_time_27_8_24.txt', 'a') 
                                    if datetime.now().hour==7:
                                        print(f"Total minor stoppages in 11 pm shift: {total_minor_stoppage} seconds")
                                        print(f"Total major stoppages in 11 pm shift: {total_major_stoppage} seconds")
                                        myfile.write(f"Total minor stoppages in 11 pm shift: {total_minor_stoppage} seconds\n")
                                        myfile.write(f"Total major stoppages in 11 pm shift: {total_major_stoppage} seconds\n")
                                    elif datetime.now().hour==15:
                                        print(f"Total minor stoppages in 7 am shift: {total_minor_stoppage} seconds")
                                        print(f"Total major stoppages in 7 am shift: {total_major_stoppage} seconds")
                                        myfile.write(f"Total minor stoppages in 7 am shift: {total_minor_stoppage} seconds\n")
                                        myfile.write(f"Total major stoppages in 7 am shift: {total_major_stoppage} seconds\n")
                                    else:
                                        print(f"Total minor stoppages in 3 pm shift: {total_minor_stoppage} seconds")
                                        print(f"Total major stoppages in 3 pm shift: {total_major_stoppage} seconds")
                                        myfile.write(f"Total minor stoppages in 3 pm shift: {total_minor_stoppage} seconds\n")
                                        myfile.write(f"Total major stoppages in 3 pm shift: {total_major_stoppage} seconds\n")
                                    myfile.close()
                                    total_minor_stoppage=0.0
                                    total_major_stoppage=0.0    
                                    door_flag=2                        


                            # out.write(frame)
                            

                        elif machine_status_flag==1:
                            # print("Here at start cam 2")
                            # print(machine_stop_duration,datetime.now())
                            machine_status_flag=0
                            machine_stop_duration_2=(datetime.now()-machine_stop_duration).total_seconds()
                            # for idx in hand_in_areas:
                            #     for idx_time,time in enumerate(door_open_close_time_global):
                            #         if time>0:
                            #             if idx_time==3:
                            #                 if idx==11:
                            #                     dash_downtime.send_time(machine_stop_time,str(machine_stop_duration),str(13),str(time),18,area_time_global[idx])
                            #                 else:
                            #                     dash_downtime.send_time(machine_stop_time,str(machine_stop_duration),str(13),str(time),idx+1,area_time_global[idx])
                            #             else:
                            #                 if idx==11:
                            #                     dash_downtime.send_time(machine_stop_time,str(machine_stop_duration),str(idx_time+1),str(time),18,area_time_global[idx])
                            #                 else:
                            #                     dash_downtime.send_time(machine_stop_time,str(machine_stop_duration),str(idx_time+1),str(time),idx+1,area_time_global[idx])
                            # print(f"Machine stopped at:{machine_stop_time} for {machine_stop_duration_2} seconds")
                            if machine_stop_duration_2>=1:
                                state_new=plc.write("WRA_5_CCTV_Fault",0)
                                if state_new:
                                    print("WRA_5_CCTV_Fault RESET")
                                return [machine_stop_time,str(machine_stop_duration_2),door_open_close_time_global,hand_in_areas,area_time_global,send_data_global,global_timer]

                        frame=cv2.resize(frame,(500,500))
                        cv2.imshow('Camera_2', frame)
                        if cv2.waitKey(5) & 0xFF == ord('q'):
                            break
                       

                    else:
                        if cam_flag==1:
                            cv2.destroyWindow("Camera_2")
                            cam_flag=0
                        frame_height=1920
                        frame_width=1080
                        image = np.ones((frame_height,frame_width, 3), dtype=np.uint8) * 255
                        (text_width, text_height), baseline = cv2.getTextSize("Cannot fetch Camera 2 feed", cv2.FONT_HERSHEY_SIMPLEX, 1.5,2)
                        # text_x = (frame_width - text_width) // 2
                        # text_y = (frame_height + text_height) // 2
                        cv2.putText(image, "Cannot fetch Camera 2 feed",(320,350), cv2.FONT_HERSHEY_SIMPLEX,1.5, (0,0,0), 2, lineType=cv2.LINE_AA)
                        image=cv2.resize(image,(700,700))
                        cv2.imshow('Camera_2', image)
                        if cv2.waitKey(5) & 0xFF == ord('q'):
                            break
                        print(f"Cannot fetch Camera 2 feed at {datetime.now()}")
                        video_path = "rtsp://admin:admin123@192.168.10.16:554"
                        #video_path = r"C:\Users\pc\Desktop\20240720_154118.mp4"
                        cap = cv2.VideoCapture(video_path)
                        # main_loop()
                except Exception as e:
                    print(e)
                    # print(f"PLC not connected\nTrying to reconnect at {datetime.now()}")
                    plc=toggle_plc_trigger(plc,"192.168.10.222")
        
        else:
            if cam_flag==1:
                cv2.destroyWindow("Camera_2")
                cam_flag=0
            frame_height=1920
            frame_width=1080
            image=cv2.resize(image,(700,700))
            image = np.ones((frame_height,frame_width, 3), dtype=np.uint8) * 255
            (text_width, text_height), baseline = cv2.getTextSize("Camera 2 not connected", cv2.FONT_HERSHEY_SIMPLEX, 1.5,2)
            # text_x = (frame_width - text_width) // 2
            # text_y = (frame_height + text_height) // 2
            cv2.putText(image, "Camera 2 not connected", (320,350), cv2.FONT_HERSHEY_SIMPLEX,1.5, (0,0,0), 2, lineType=cv2.LINE_AA)
            cv2.imshow('Camera_2', image)
            if cv2.waitKey(5) & 0xFF == ord('q'):
                            break
            print(f"Camera 2 not connected at {datetime.now()}")
            video_path = "rtsp://admin:admin123@192.168.10.16:554"
            #video_path = r"C:\Users\pc\Desktop\20240720_154118.mp4"
            cap = cv2.VideoCapture(video_path)

    # cap.release()
    
# out.release()


def main_2(queue2):
    
    plc = None
    try:
        imp=main_loop()
        queue2.put(imp)
    finally:
        cv2.destroyAllWindows()
        if plc:
            plc.close()
            # logging.info("PLC connection closed")
# main_2()

