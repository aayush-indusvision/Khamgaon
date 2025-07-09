from pycomm3 import LogixDriver
import time


def initialize_plc(ip,plc_lock):
    # global plc_client, plc_client_on
    with plc_lock:
        try:
            plc_client = LogixDriver(ip)
            plc_client.open()
            plc_client_on = True
            print(f"Connected to PLC at {ip}")
        except Exception as e:
            print("PLC Init Error:", e)
            plc_client_on = False
        return plc_client,plc_client_on

def reset_plc(ip,plc_lock):
    # global plc_client, plc_client_on
    with plc_lock:
        try:
            if plc_client:
                plc_client.close()
                time.sleep(0.5)
            plc_client = LogixDriver(ip)
            plc_client.open()
            plc_client_on = True
            print("PLC Reconnected")
        except Exception as e:
            print("PLC Reconnect Failed:", e)
            plc_client_on = False
    return plc_client_on

def read_machine_status(PLC_IP_ADDRESS,PLC_STATUS_TAG,plc_lock,plc_client_on,plc_client):
    with plc_lock:
        try:
            if plc_client_on and plc_client:
                status = plc_client.read(PLC_STATUS_TAG)
                if status is not None:
                    return status.value == 1
                else:
                    print("Status is None, trying reconnect...")
                    plc_client_on=reset_plc(PLC_IP_ADDRESS,plc_lock)
        except Exception as e:
            print("PLC Read Error:", e)
            reset_plc(PLC_IP_ADDRESS,plc_lock)
    return False

def write_plc_value(value,PLC_WRITE_TAG,plc_lock,plc_client_on,plc_client):
    with plc_lock:
        try:
            if plc_client_on and plc_client:
                plc_client.write(PLC_WRITE_TAG, value)
        except Exception as e:
            print(f"PLC Write Error to {PLC_WRITE_TAG}:", e)