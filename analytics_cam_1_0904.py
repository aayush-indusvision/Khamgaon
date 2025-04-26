from ultralytics import YOLO
import pycomm3
import os
from pycomm3 import LogixDriver
import cv2
import numpy as np
import time as tim
from dashboard import *
import supporting_variables_cam_1

fps=5

OUTPUT_DIR = r"Working_Saved_Clips_1"
os.makedirs(OUTPUT_DIR, exist_ok=True)

video_writer = None
is_recording = False

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
        plc_data = plc.read(*supporting_variables_cam_1.variables)
        machine_status=plc.read('cctv_fb.15')
    except Exception as e:
        print(f"Failed to reconnect to PLC: {e}")
        print("Not writing to PLC")
        
    return plc

def toggle_plc_trigger(plc, plc_ip="192.168.10.222"):
    max_retries = 3
    delay_between_attempts = timedelta(milliseconds=10)  # 100 ms delay between attempts

    for retry in range(max_retries):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
           
            plc_data = plc.read(*supporting_variables_cam_1.variables)
            machine_status=plc.read('cctv_fb.15')
            if plc_data:
                # print(plc_data)
                print("Reading Values")
                break
            else:
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

model = YOLO("08_10_24_Cam_1.pt")
time_unit = "second"


dash=Dashboard_glob(url='http://localhost:8000/api/dashboard/')
dash_downtime=Dashboard_downtime(url='http://localhost:8000/api/downtime-analysis/')


areas=[]

lines = [
    [(615,96),(625,490),(722,485),(805,635),(790,96)],
    [(493,490),(510,942),(805,942),(805,635),(722,485),(625,490)],
    [(790,96),(805,855),(1217,855),(1217,595),(1073,450),(1040,96)],
    [(1040,15),(1050,211),(1367,211),(1367,15)],
    [(1050,211),(1073,450),(1217,595),(1322,595),(1310,211)],
    [(1217,595),(1217,855),(805,855),(805,1045),(1466,1045),(1466,595)]
]

lines_draw = [
    (615,96,625,490),(625,490,722,485),(722,485,805,635),(805,635,790,96),(790,96,615,96), ##AREA 1
    (493,490,510,942),(510,942,805,942),(805,942,805,635),(805,635,722,485),(722,485,625,490),(625,490,493,490), ##AREA 2
    (790,96,805,855),(805,855,1217,855),(1217,855,1217,595),(1217,595,1073,450),(1073,450,1040,96),(1040,96,790,96), ##AREA3
    (1040,15,1050,211),(1050,211,1367,211),(1367,211,1367,15),(1367,15,1040,15), ##AREA 4
    (1050,211,1073,450),(1073,450,1217,595),(1217,595,1322,595),(1322,595,1310,211),(1310,211,1050,211), ##AREA 5
    (1217,595,1217,855),(1217,855,805,855),(805,855,805,1045),(805,1045,1466,1045),(1466,1045,1466,595),(1466,595,1217,595)
]

under_arm_roi=[]


area_roi = np.array([(1000, 55), (1027, 230), (1043, 304), (1134, 387), (1217, 467), (1284, 564), (1290, 706), (1321, 950), (729, 991), (668, 76)],dtype=np.int32)
# area_roi=np.array([(1195, 245), (1203, 325), (1216, 447), (1224, 508), (1248, 536), (1266, 573), (1280, 621), (1285, 669), (1273, 710), (1255, 762), (1219, 809), (1183, 837), (1134, 864), (1075, 878), (1003, 872), (938, 841), (879, 783), (853, 725), (839, 644), (834, 598), (824, 570), (815, 487), (808, 335), (806, 233)],dtype=np.int32)

area_names=['Socketed mounting body','Soap infeed','Pickup chain drive','Pincer guard','Pocketed belt chain drive','Pickup assembly']

area_timing_ref=[90,60,0.1,0.1,0.1,0.1]
major_or_minor_stop=[False for _ in range(len(lines))]
# arm_area_time=[0.0 for _ in range(len(lines))]
glove_area_time=[0.0 for _ in range(len(lines))]
glove_area_time_total=[0.0 for _ in range(len(lines))]
glove_area_time_global=[0.0 for _ in range(len(lines))]
glove_area_time_copy=[0.0 for _ in range(len(lines))]

minor_stopage=[0 for _ in range(len(lines))]
major_stopage=[0 for _ in range(len(lines))]
send_data=[0 for _ in range(len(lines))]
send_data_global=[0 for _ in range(len(lines))]


for i in lines:
    areas.append(np.array(i))


total_major_stoppage=0.0
total_minor_stoppage=0.0
door_flag=0

door_open_close_count=[]
door_open_close_time=[]
machine_status_flag=0
current_frame = 0
last_hand_positions = {}
last_movement_frames = {}
hand_in_areas=[]
door_open_close_count=[0 for _ in range(5)]
door_open_close_time=[0.0 for _ in range(5)]
door_open_close_time_global=[0.0 for _ in range(5)]
def main_loop():
   
    global is_recording

    global last_hand_positions
    global last_movement_frames
    global current_frame
    global total_major_stoppage
    global total_minor_stoppage
    global door_flag
    global send_data_global
    shift_wise_area_time=[0.0 for _ in range(len(lines))]
    global machine_stop_duration
    global machine_stop_time
    global machine_status_flag
    global glove_area_time
    global glove_area_time_copy
    global glove_area_time_global
    global send_data
    global door_open_close_count
    global door_open_close_time
    global hand_in_areas
    global door_open_close_count
    global door_open_close_time
    
    global_timer=0.0
    total_work_time=0.0
    hand_in_areas=[]
    glove_area_time_global=[0.0 for _ in range(len(lines))]
    send_data_global=[0 for _ in range(len(lines))]
    
    plc=initialize_plc("192.168.10.222")
    if not plc:
        print("Failed to initialise PLC")
        # return
    while True:
        video_path = "rtsp://admin:admin123@192.168.10.15:554"
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
            fps = cap.get(cv2.CAP_PROP_FPS) or 5
            frame_size = (width, height)
            while cap.isOpened():
                ret, frame = cap.read()
                # print(ret)
                try:
                    plc_data= plc.read(*supporting_variables_cam_1.variables)
                    # print(plc_data)
                    
                    machine_status=plc.read('cctv_fb.15')
                    dummy=plc.read('WRA_5_Machine_Status_Waiting')
                    if ret: 
                        for (start_x, start_y, end_x, end_y) in lines_draw:
                                    cv2.line(frame, (start_x, start_y), (end_x, end_y), (0,0,255), 2)
                        # print(machine_status.value)
                        if not machine_status.value:
                            
                            if machine_status_flag==0:
                                
                                machine_status_flag=1
                                machine_stop_duration=0

                                machine_stop_time=str(datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))
                                machine_stop_duration=datetime.now()   
                            n = len(plc_data)
                            
                            plc_values = []
                            for i in range(0, n) :
                                plc_values.append(plc_data[i].value)
                            plc_values = np.array(plc_values)
                                
                            if False in plc_values:
                                if not is_recording:
                                    start_recording(frame_size, fps)
                                for idx,i in enumerate(plc_values):
                                    if i==False:
                                        door_open_close_time[idx]+=(1/fps)
                                        if door_flag==2 or door_flag==0:
                                            door_open_close_count[idx]+=1
                                
                                door_flag=1
                                
                                results = model.predict(source=frame, show=False, conf=0.35,save=False,stream=True,verbose=False)
                                
                                box_and_cls=[]
                                
                                names = []
                                detected_hands=[]
                                names_and_points=[]
                                for result in results:
                                    if len(result.boxes.xyxy)!=0:
                                        len_2=list(result.boxes.cls).count(2)
                                        len_1=list(result.boxes.cls).count(1)
                                        for i in result.boxes:
                                            box_and_cls.append([i.xyxy[0],i.cls])
                                        for i in box_and_cls:
                                            box = i[0].cpu().numpy() if hasattr(i[0], 'cpu') else i[0].numpy() if hasattr(i[0], 'numpy') else i[0]
                                            cls=i[1].item()
                                            x1, y1, x2, y2 = box
                                            
                                            grid_x = int(((x1+x2)//2))
                                            grid_y = int(((y1+y2)//2))
                                            cv2.circle(frame, (grid_x,grid_y),5, (255,0,0), 2)
                                            for area_id,work_area in enumerate(areas):
                                            
                                                # i.reshape((-1,1,2))
                                                if cv2.pointPolygonTest(work_area, (grid_x,grid_y), False) >= 0:
                                            # box = box.cpu().numpy() if hasattr(box, 'cpu') else box.numpy() if hasattr(box, 'numpy') else box
                                                    if (cls==0.) and (len_2<2) and (len_1<2) and (cv2.pointPolygonTest(area_roi, (int(box[0]),int(box[1])), False) >= 0):
                                                        
                                                        names_and_points.append([box,area_id,work_area])
                                                        names.append('hand_under_machine')
                                                        detected_hands.append(box)
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
                                                            movement_threshold=50,
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
                                        
                                    
                                                glove_area_time[area_id] += (1/fps)
                                                if glove_area_time[area_id]>=1:
                                                    global_timer+=1/fps
                                                    hand_in_machine_areas=1
                                                    state=plc.write(f"CCTV_BOOL.{area_id+12}",True)
                                                    if state:
                                                        print(f"Writing area {area_id+12} time to PLC") 
                                                    hand_in_areas.append(area_id)
                                                    send_data[area_id]=1
                                                    # cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2) 
                                                    cv2.polylines(frame,[work_area], isClosed=True,color=(0, 255, 0),thickness=3)
                                                    
                                                    # print(f"Detected {box_and_name[0]} in {area_names[num]} for {glove_area_time[num]:.2f} {time_unit}")
                                                    # cv2.putText(frame,f"Detected in {area_names[num]} for {glove_area_time[num]:.2f} {time_unit}",(50,50+num*40),cv2.FONT_HERSHEY_COMPLEX,1,(0,255,0),2,cv2.LINE_AA)
                                                else:
                                                
                                                    state=plc.write(f"CCTV_BOOL.{area_id+12}",False)
                                            else:
                                                
                                                    state=plc.write(f"CCTV_BOOL.{area_id+12}",False)
                                        else:
                                                
                                             state=plc.write(f"CCTV_BOOL.{area_id+12}",False)
                                if is_recording and video_writer:
                                    video_writer.write(frame)
                                    
                                
                                                
                            else:
                                if door_flag==1:
                                    stop_recording()
                                    ind=[]
                                    max_work_done=0
                                    current_frame=0
                                    last_hand_positions = {}
                                    last_movement_frames = {}
                                    myfile = open('camera_1_door_time_27_8_24.txt', 'a')
                                    myfile_work = open('analytics.txt', 'a')
                                    ind = np.nonzero(glove_area_time)[0].tolist()
                                    if len(ind)!=0:
                                        max_work_done=max(glove_area_time)
                                        
                                        max_work_area=glove_area_time.index(max_work_done) 
                                        state_new=plc.write("WRA_5_CCTV_Fault",int(max_work_area)+12)
                                        if state_new:
                                            print(f"Max work done in {max_work_area+12}")
                                            max_work_area=0
                                    for idx in hand_in_areas:
                                        if send_data[idx]==1:
                                            shift_wise_area_time[idx]+=glove_area_time[idx]
                                            send_data_global[idx]=send_data[idx]
                                            if glove_area_time[idx]>=area_timing_ref[idx]:
                                                
                                                major_stopage[idx]+=1
                                                
                                                total_major_stoppage+=glove_area_time[idx]
                                                print(f"Major stopage in {area_names[idx]}")
                                                print(area_names[idx],glove_area_time[idx],(global_timer/glove_area_time[idx])*100)
                                                dash.send_time(1,idx+12,float(glove_area_time[idx]),2)
                                                
                                                #ADD MAJOR TO SEND MAJOR STOPPAGE
                                            
                                                
                                            else:
                                                minor_stopage[idx]+=1

                                                total_minor_stoppage+=glove_area_time[idx]
                                                # total_minor_stoppage+=glove_area_time[idx]
                                                print(f"Minor stopage in {area_names[idx]}")
                                                print(area_names[idx],glove_area_time[idx],(global_timer/glove_area_time[idx])*100)
                                                dash.send_time(1,idx+12,float(glove_area_time[idx]),1)
                                                # state=plc.write(f"CCTV_FB_Time[{idx+11}]",float(glove_area_time[idx]))
                                                # if state:
                                                #     print(f"Writing total time to PLC id {idx+11} minor")
                                                #ADD MINOR TO SEND MINOR STOPPAGE
                                        if send_data[idx]==1:        
                                            myfile_work.write(f"{area_names[idx]}: {glove_area_time[idx]} seconds at {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}\n")
                                            print(f"{area_names[idx]}: {glove_area_time[idx]} seconds at {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}")        
                                        send_data[idx]=0    
                                        glove_area_time_total[idx]+=glove_area_time[idx]
                                        glove_area_time_global[idx]+=glove_area_time[idx] 
                                        total_work_time+=glove_area_time[idx]
                                        
                                        glove_area_time_copy[idx]=0
                                        glove_area_time[idx]=0
                                    myfile_work.write(f"Total work done: {total_work_time} seconds at {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}\n")
                                    print(f"Total work done: {total_work_time} seconds at {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}")
                                    myfile_work.write(f"Max work done in machine: {max_work_done} seconds at {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}\n")
                                    print(f"Max work done in machine: {max_work_done} seconds at {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}")

                                    for idx,time_1 in enumerate(door_open_close_time):
                                        if time_1>0:
                                            print(f"Door {idx+7} was open for {time_1} seconds")
                                            myfile.write(f"Door {idx+7} was open for {time_1} at {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}\n")
                                            door_open_close_time_global[idx]=time_1
                                        door_open_close_time[idx]=0.0
                                    myfile.close()
                                    # door_flag=2
                                
                            # if ((datetime.now().hour == 7 and datetime.now().minute==0 and datetime.now().second==1) and (total_minor_stoppage!=0.0 or total_major_stoppage!=0.0)) or ((datetime.now().hour == 15 and datetime.now().minute==0 and datetime.now().second==1) and (total_minor_stoppage!=0.0 or total_major_stoppage!=0.0)) or ((datetime.now().hour == 23 and datetime.now().minute==0 and datetime.now().second==1) and (total_minor_stoppage!=0.0 or total_major_stoppage!=0.0)): 
                                if door_flag==1:
                                    # for serial in range(len(shift_wise_area_time)):
                                    #     if (int(shift_wise_area_time[serial])!=0):
                                            
                                    #         state=plc.write(f"CCTV_FB_Time[{serial+11}]",float(shift_wise_area_time[serial]))

                                    #         if state:
                                    #             print(f"Writing total time to PLC id {serial+11}")
                                    #         shift_wise_area_time[serial]=0
                                    #         tim.sleep(10)
                                    #         state_2=plc.write(f"CCTV_FB_Time[{serial+11}]",0.0)
                                    #         if state_2:
                                    #             print("Reset")
                                        
                                    myfile = open('camera_1_major_minor_time_27_8_24.txt', 'a') 
                                    if datetime.now().hour==7:
                                        print(f"Total minor stoppages in 11 pm shift: {total_major_stoppage} seconds")
                                        print(f"Total major stoppages in 11 pm shift: {total_major_stoppage} seconds")
                                        myfile.write(f"Total minor stoppages in 11 pm shift: {total_major_stoppage} seconds\n")
                                        myfile.write(f"Total major stoppages in 11 pm shift: {total_major_stoppage} seconds\n")
                                    elif datetime.now().hour==15:
                                        print(f"Total minor stoppages in 7 am shift: {total_major_stoppage} seconds")
                                        print(f"Total major stoppages in 7 am shift: {total_major_stoppage} seconds")
                                        myfile.write(f"Total minor stoppages in 7 am shift: {total_major_stoppage} seconds\n")
                                        myfile.write(f"Total major stoppages in 7 am shift: {total_major_stoppage} seconds\n")
                                    else:
                                        print(f"Total minor stoppages in 3 pm shift: {total_major_stoppage} seconds")
                                        print(f"Total major stoppages in 3 pm shift: {total_major_stoppage} seconds")
                                        myfile.write(f"Total minor stoppages in 3 pm shift: {total_major_stoppage} seconds\n")
                                        myfile.write(f"Total major stoppages in 3 pm shift: {total_major_stoppage} seconds\n")
                                    myfile.close()
                                    total_minor_stoppage=0.0
                                    total_major_stoppage=0.0
                                    door_flag=2
                                # out.write(frame)
                            

                        elif machine_status_flag==1:
                            # print("Here at start cam 1")
                            # print(machine_stop_duration,datetime.now())
                            machine_status_flag=0
                            machine_stop_duration_1=(datetime.now()-machine_stop_duration).total_seconds()
                            # for idx in hand_in_areas:
                            #     for idx_time,time in enumerate(door_open_close_time_global):
                            #         if time>0:
                            #             if send_data_global[idx]:
                            #                 send_data_global[idx]=False
                            #                 dash_downtime.send_time(machine_stop_time,str(machine_stop_duration),str(idx_time+7),str(time),idx+12,glove_area_time_global[idx])

                            # print(f"Machine stopped at:{machine_stop_time} for {machine_stop_duration_1} seconds")
                            if machine_stop_duration_1>=1:
                                state_new=plc.write("WRA_5_CCTV_Fault",0)
                                if state_new:
                                    print("WRA_5_CCTV_Fault RESET")
                                return [machine_stop_time,str(machine_stop_duration_1),door_open_close_time_global,hand_in_areas,glove_area_time_global,send_data_global,global_timer]

                        frame = cv2.resize(frame,(500,500))
                        frame=cv2.flip(frame,0)
                        frame=cv2.flip(frame,1)
                        cv2.imshow('Camera_1', frame)
                        if cv2.waitKey(5) & 0xFF == ord('q'):
                            break
                        
                    else:
                        cv2.destroyWindow("Camera_1")
                        image = np.ones((frame_height,frame_width, 3), dtype=np.uint8) * 255
                        (text_width, text_height), baseline = cv2.getTextSize("Cannot fetch Camera 1 feed", cv2.FONT_HERSHEY_SIMPLEX, 1.5,2)
                        text_x = (frame_width - text_width) // 2
                        text_y = (frame_height + text_height) // 2
                        cv2.putText(image, "Cannot fetch Camera 1 feed", (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX,1.5, (0,0,0), 2, lineType=cv2.LINE_AA)
                        cv2.imshow('Camera_1', image)
                        if cv2.waitKey(5) & 0xFF == ord('q'):
                            break
                        print(f"Unable to fetch feed from Camera 1 at {datetime.now()}")
                        video_path = "rtsp://admin:admin123@192.168.10.15:554"
                        cap = cv2.VideoCapture(video_path)
                        # main_loop()
                except Exception as e:
                    print(e)
                    # print("PLC not connected\nTrying to reconnect")
                    plc=toggle_plc_trigger(plc,"192.168.10.222")
        else:
            cv2.destroyWindow("Camera_1")
            image = np.ones((frame_height,frame_width, 3), dtype=np.uint8) * 255
            (text_width, text_height), baseline = cv2.getTextSize("Camera 1 not connected", cv2.FONT_HERSHEY_SIMPLEX, 1.5,2)
            text_x = (frame_width - text_width) // 2
            text_y = (frame_height + text_height) // 2
            cv2.putText(image, "Camera 1 not connected", (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX,1.5, (0,0,0), 2, lineType=cv2.LINE_AA)
            cv2.imshow('Camera_1', image)
            if cv2.waitKey(5) & 0xFF == ord('q'):
                            break
            print(f"Camera 1 not connected at {datetime.now()}")
            video_path = "rtsp://admin:admin123@192.168.10.15:554"
            cap = cv2.VideoCapture(video_path)
    

    # cap.release()
# out.release()
# cv2.destroyAllWindows()

def main_1(queue1):
    plc = None
    try:
        imp=main_loop()
        queue1.put(imp)
    finally:
        cv2.destroyAllWindows()
        if plc:
            plc.close()
            # logging.info("PLC connection closed")

# main_1()
