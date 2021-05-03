import socket
import threading
import binascii
import time
import json
import keyboard
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import logging
from pathlib import Path
#import snappy


def decodethis(data):
    record = int(data[18:20], 16)
    timestamp = int(data[20:36], 16)
    lon = int(data[38:46], 16)
    lat = int(data[46:54], 16)
    alt = int(data[54:58], 16)
    sats = int(data[62:64], 16) #maybe
    print("Record: " + str(record) + "\nTimestamp: " + str(timestamp) + "\nLat,Lon: " + str(lat) + ", " + str(lon) + "\nAltitude: " + str(alt) + "\nSats: " +  str(sats) )
    return "0000" + str(record).zfill(4)


def decode_gps_data(name, data):
    timestamp = int(data[20:36], 16)
    lon = int(data[38:46], 16)
    lat = int(data[46:54], 16)
    info = name + " " + '"Timestamp":' + str(timestamp) + ','+'"Lat":' + str(lat) + ','+'"Long":' + str(lon)
    return(info)


def calc_data_count(str_val):
    str_val = str_val.hex()
    count = int(str_val[18:20],16)
    byte_count = count.to_bytes(4, byteorder = 'big')
    return byte_count


def total_length(str_val):
    str_val = str_val.hex()
    #print(str_val)
    return int(str_val[8:16],16) + 13


def calculate_bytes(str_val):
    str_val = str_val.hex()
    return int(len(str_val)/2)


def detect_key_press():
    global condition
    keyboard.wait("esc")
    condition = False
    raise Exception("Aborting server gracefully")


class SocketHandler(threading.Thread):
    
    
    def __init__(self, conn, addr, write_api, lock):
        super(SocketHandler, self).__init__()
        self.conn = conn 
        self.addr = addr
        self.write_api = write_api
        self.daemon = True
        self.lock = lock
        self.imei = ""
        self.allowed = ("867553051163608", "359632105570367", "860147042649242", \
            "860147042626570", "860147042636561", "860147042636678")
     
    def handshake(self):
        pass
    
    def run(self):
        self.handle_client(self.conn, self.addr)   
    
    
    def handle_client(self, conn, addr):
        global condition
        condition = True
        while condition:
            avl_data = ''
            pkt_size = 0
            data = self.conn.recv(4096)
            if (data.hex()[:4] == '000f'):
                logging.info(f"the length of handshake message is {len(data)}")
                self.conn.send(bytes().fromhex('01'))
                self.imei = data[2:].decode() 
                self.name = self.imei
                if self.imei not in self.allowed:
                    self.conn.send(bytes().fromhex('00'))
                    return self.conn.close()
            elif len(data) < 45:
                return self.conn.close()
            else:
                data_count = calc_data_count(data)
                self.conn.send(data_count)   
                pkt_len = total_length(data)
                logging.info(f"length of packet {pkt_len}")
                avl_data = data
                logging.info(avl_data.hex())
                if avl_data:
                    flag = self.write_db(avl_data.hex())
                return self.conn.close()

    
    def write_db(self, data):
        #print(data)
        org = "qeeri"
        bucket = "gps"
        line = "gps_data" + f",imei={self.imei}" + f" raw_data=\"{data}\"" + f"{time.time_ns()}" 
        #print(line)
        with self.lock:
            try:
                logging.info(f"Lock acquired by{self.imei}")
                self.write_api.write(bucket, org, line, batch=1)
                flag = True
            except:
                flag = False
        logging.info(f"Lock released by{self.imei}")
        return flag
        
def start():
    
    global condition 
    lock = threading.Lock()
    port = 8001
    token = "2VF9BBu-AfoqmeGUVC_i1GmDztToXkYlOWt0w-5eFkhb5G5PDxwnRy5YMoxxLZ_iaiwQNe96gMqM5loD84x-Vw=="
    condition = True
    base_path = Path("C:\\Users\\usman\\Desktop")
    log_path = base_path/"Teltonika/app.log"
    workers = []
    
    logging.basicConfig(filename=log_path.as_posix(), level=logging.INFO)
    client = InfluxDBClient(url="http://localhost:8086", token=token)
    write_api = client.write_api(write_options=SYNCHRONOUS)
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('localhost', port))
    s.settimeout(30)
    s.listen()
    
    #thread = threading.Thread(target=detect_key_press)
    #thread.start()
    print(" Server is listening ...")
    
    while condition:
        try:
            conn, addr = s.accept()
            #print("Connection from", conn)
            #print("address", addr)
            handler = SocketHandler(conn, addr, write_api, lock)
            workers.append(handler)
            handler.start()
            logging.info(f"[ACTIVE CONNECTIONS] {threading.activeCount() - 1}")
        except Exception as e:
            logging.info(f"Exception Caught: {e}, Continuing")
    print("Aborting threads gracefully....")
    
    for worker in workers:
        worker.join()
    return "Connection Closed"


if __name__ == "__main__":
    start()
