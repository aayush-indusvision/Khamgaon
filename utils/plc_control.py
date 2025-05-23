import utils.support_variables as support_variables
import datetime
from pycomm3 import LogixDriver

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
    
def read_values(plc):
    return plc.read(*support_variables.variables)