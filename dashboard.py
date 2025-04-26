from datetime import *
import requests


class Dashboard_glob:
    def __init__(self, url):
        self.url = url
    

    def send_time(self,machine_id,area, seconds,type_of_stop):

            # Current system date and time
            recorded_date_time = str(datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))

            # JSON payload
            payload= {
                "base64_image": None,
                "machines_id": machine_id,
                "plant_id": 1,
                "duration":seconds,
                "areas_id":area,
                "recorded_date_time":recorded_date_time,
                "type_of_stoppage":type_of_stop
            }

            # Send POST request
            response = requests.post(self.url, json=payload)

            # Check response status
            if response.status_code == 200:
                print(" time sent  successfully boys :).")
            else:
                print("Failed to send image. Status code:", response.status_code)

class Dashboard_downtime:
    def __init__(self, url):
        self.url = url
    

    def send_time(self,machine_stop_time,machine_stop_duration,gate_id,gate_open_duration,area_id,area_duration):

            # Current system date and time
            recorded_date_time = str(datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))

            # JSON payload
            payload= {
                "base64_image": None,
                "machine_stop_time": machine_stop_time,
                "machine_stop_duration": machine_stop_duration,
                "gate": gate_id,
                "gate_open_duration":gate_open_duration,
                "areas": area_id,
                "area_duration": area_duration
            }

            # Send POST request
            response = requests.post(self.url, json=payload)

            # Check response status
            if response.status_code == 200:
                print(" time sent  successfully boys :).")
            else:
                print("Failed to send image. Status code:", response.status_code)
        
