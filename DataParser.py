import time
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict


class DataParser:
    """ Class parses whole codec-8 of teltonika into dictionaries """
    
    def __init__(self, imei):
        """All attributes of teltonika parser are listed here"""
        self.avl_dict = {}
        self.avl_dicts = {}
        #self.avl_dict['imei'] = imei
        self.imei = imei

    def get_avl_count(self, str_val):
        """ Get the number of AVL data packets present within a single message"""
        count = int(str_val[18:20], 16)
        return count

    def read_nth_io(self, nth, byte_map, data):
        """Create a dictionary of n-bytes datapoints"""
        io_map = {}
        start = 0
        step = byte_map[nth] * 2
        total = len(data)
        #print(f"Total is for {total}")
        #print(f"Start is for {start}")
        #print(f"step is for {step}")

        for val in range(start, total, step):
            #print(val)
            io_id = int(data[val:val+2], 16)
            io_data = int(data[val+2:val+step], 16)
            #print(f"io_id_val for {val} ")
            #print(f"io_id_val+2 for {val+2} ")
            #print(f"io_id_val+step  for {val+step} ")

            io_map["ID "+str(io_id)] = io_data

        return io_map    

    def decode_gps(self, gps):
        """ decode gps, speed from the avl packet"""
        lon = int(gps[0:8], 16)
        lat = int(gps[8:16], 16)
        alt = int(gps[16:20], 16)
        angle = int(gps[20:24], 16)
        sat = int(gps[24:26], 16)
        speed = int(gps[26:30], 16)
        return [lon, lat]#, alt, angle, sat, speed]
        
    def read_io(self, io, event_start, data_dict):
        "should get input starting at avl packet"
        event_id_end = event_start + 2
        event_id = int(io[event_start:event_id_end], 16)
        num_total_end = event_id_end + 2
        num_total_io = int(io[event_id_end:num_total_end], 16)
        data_dict["event_id"] = event_id
        data_dict["total_number_of_io"] = num_total_io
        byte_map = {'n1':2, 'n2':3, "n4":5, "n8":9}
        start = num_total_end 
        end = num_total_end + 2
    
        for val in ['n1', 'n2', 'n4', 'n8']:
            if val not in data_dict.keys():
                data_dict[val] = {}
            data_dict[val]["io_start"] = start
            total_io = int(io[start:end], 16) 
            size = total_io * byte_map[val] * 2 # since they are ids and val for each nth element
            if size == 0:
                ind_end = end
                data = False
            else:
                ind_end = end + size
                data = io[end:ind_end] 
            start = ind_end 
            end = start + 2 # the total io field is 1 byte long hence 2
            data_dict[val]["total"] = total_io
            data_dict[val]["raw_data"] = data # this excludes size of nth_io si it begins after nth count
            if data:
                #print(val)
                #print(data)
                data_dict[val]["parsed_data"] = self.read_nth_io(val, byte_map, data)
            else:
                data_dict[val]["parsed_data"] = None
            data_dict[val]["io_end"] = ind_end # this is end of the nth io
        
        data_dict["avl_end"] = ind_end
        data_dict["imei"] = self.imei

    def avl_data_parser(self, input_str, start_index):
        """primary function to parse whole avl data"""
        ind_ts_start = start_index # should be 20 * 2
        ind_ts_end = ind_ts_start + 16 # offset be 8 * 2 for hex
        ind_p_start = ind_ts_end
        ind_p_end = ind_p_start + 2 # offset
        ind_gps_start = ind_p_end
        ind_gps_end = ind_gps_start + 30
        io_element_start = ind_gps_end
        #print(ind_ts_end)
        #print(ind_ts_start)
        time = int(input_str[ind_ts_start:ind_ts_end], 16)
        priority = int(input_str[ind_p_start:ind_p_end], 16)
        gps = input_str[ind_gps_start:ind_gps_end]
        #print(f'this is gps, {gps}')
        
        self.avl_dict["gps"] = self.decode_gps(gps)
        self.avl_dict["time"] = datetime.fromtimestamp(time/1000).strftime('%Y-%m-%d %H:%M:%S')
        self.avl_dict["priority"] = priority
        #print(f'this is priority, {priority}')
        #print(f'this is start of io_element, {io_element_start}')
        self.read_io(input_str, io_element_start, self.avl_dict)
        
        #return self.avl_dict
        #self.set_attributes(avl_dict)

    def get_avl_data(self, avl_count, input_str, start_index=0):
        "The get_avl_data function should get an input starting from the data packets"
        #avl_dicts = {}
        #print(input_str)
        start_index = 20 # 10 * 2 hex
        for val in range(avl_count):
            self.avl_data_parser(input_str, start_index)
            #print("************************New information*****************************")
            #print(self.avl_dict)
            #print("********************************************************************")
            self.avl_dicts[val] = self.avl_dict
            start_index = self.avl_dict["avl_end"]
        #self.avl_dicts = avl_dicts
        #self.set_attributes()
        return self.avl_dicts
    
    
    def set_attributes(self):
        self.gps = self.avl_dict["gps"]
        self.lon = self.avl_dict["lon"]
        self.lat = self.avl_dict["lat"]
        self.avl_count = self.avl_dict["avl_count"]
