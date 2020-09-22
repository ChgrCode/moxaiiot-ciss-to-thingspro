#!/usr/bin/env python2
'''
Bosch CISS sensor 
'''

'''
Change log
0.4.0 - 2020-08-12 - cg 
    Add serial reconnect
    
0.3.0 - 2020-08-05 - cg
    Restructure/Updates
    
0.2.0 - 2020-07-07 - cg
    Initial version
'''

__author__ = "Christian G."
__license__ = "MIT"
__version__ = '0.4.1'
__status__ = "beta"
    
import sys
import serial        
import threading
import math

from enum import Enum
from collections import deque

from chgrcodebase import *
from CissUsbConnectord_v2_3_1 import CISSNode

if check_for_module('statistics'):
    import statistics  

# Sensor Index 
class SnIx(Enum):
    ACCL = 'Accl'
    ACCL_X = 'Accl_x'
    ACCL_Y = 'Accl_y'
    ACCL_Z = 'Accl_z'
    GYRO = 'Gyro'
    GYRO_X = 'Gyro_x'
    GYRO_Y = 'Gyro_y'
    GYRO_Z = 'Gyro_z'
    MAGN = 'Magn'
    MAGN_X = 'Magn_x'
    MAGN_Y = 'Magn_y'
    MAGN_Z = 'Magn_z'
    TEMP = 'Temp'
    HUMI = 'Humi'
    PRES = 'Pres'
    LIGHT = 'Ligh'
    NOISE = 'Nois' 
    
    def ix(self):  
        return self.value 

class CissSensor(AppBase):
    _has_statistics_mod = check_for_module('statistics')
    
    def __init__(self, node, id='cissSensor', **kwargs):
        AppBase.__init__(self, id, **kwargs)
        self.ciss_node = node
        self.sensor_id = kwargs.get('sensor_id', None)
        self.data_type = kwargs.get('data_type', None)
        self.data_length = kwargs.get('data_length', None)
        self.name = kwargs.get('name', self.get_base_id())
        self.unit = kwargs.get('unit', 'n/a')        
        self.publish = kwargs.get('publish', 0)
        self.statistics = kwargs.get('statistics', 0)
        self.calc_stats = kwargs.get('calc_stats', False)
        self._ext_conf = kwargs.get('conf', None)  
        if not isinstance(self._ext_conf, dict):
            self._ext_conf = dict()
        self.name = self._ext_conf.get('name', self.name)        
        self.unit = self._ext_conf.get('unit', self.unit)        
        self.enabled = self._ext_conf.get('enabled', True)
        self.publish = self._ext_conf.get('publish', self.publish)
        self.stream_enabled = self.str2bool(self._ext_conf.get('stream_enabled', "0"))
        self.stream_period = int(self._ext_conf.get('stream_period', 1000000))
        self.event_enabled = self.str2bool(self._ext_conf.get('event_enabled', "0"))
        self.event_threshold = self._ext_conf.get('event_threshold', 0)       
        self.value_timestamp = None
        self._value = {
            'timestamp': None,
            'current': 0,
            'min': 0,
            'max': 0,
            'mean': 0,
            'std': 0            
            }
        self.value = 0
        self._value_utime_diff = None
        self._value_ucount = 0
        self.statistics = self._ext_conf.get('enable_statistics', self.statistics)
        self._max_data_size = kwargs.get('max_data_size', 10)
        self._max_data_size = max(self.statistics, self._max_data_size)
        
        if self.statistics and not self._has_statistics_mod:
            self.statistics = 0
            self.log_error('Statistics Module not found! Disable Statistics')       
        
        self._data = deque(maxlen=self._max_data_size)
        self._on_sensor_update = None
        self.log_info('Sensor %s enabled %s! statistics %d, max_values %d, publish %d!', 
                      self.name, self.enabled, self.statistics, self._max_data_size, self.publish)  
        self.log_debug('Sensor %s streaming %s! period %d! event %s, threshold %d!', 
                       self.name, self.stream_enabled, self.stream_period, self.event_enabled, self.event_threshold)      
        return
        
        
    def update_value_ext(self, stream_data):
        if not self.enabled:
            return None       
        return self.update_value(stream_data.get(self.get_base_id(), None), 
                                 stream_data.get('timestamp', None))
    
    def update_value(self, value, timestamp):
        if value is None or value == "":
            return None
        
        if timestamp is None:
            timestamp = time.time()
        
        self.value = value
        self._value['timestamp'] = timestamp
        self._value['current'] = self.value
        
        if self.value_timestamp is None:
            self._value['max'] = self.value
            self._value['min'] = self.value        
        else:
            self._value['max'] = max(self._value['max'], self.value)
            self._value['min'] = min(self._value['min'], self.value)        
            self._value_utime_diff = timestamp - self.value_timestamp
            
        self.value_timestamp = timestamp
        
        self._data.append(self.value)        
        # ToDo      
        if self.calc_stats:  
            self.calc_statistics()        
        
        self._value_ucount += 1
        
        if self._on_sensor_update:
            self._on_sensor_update(sensor=self)
            
        return value  
    
    def calc_statistics(self):
        if not self.statistics:
            return True
        elif len(self._data) < 2:        
            self.log_warning('No data information to calculate for this sensor')
            return False
        
        data = list(self._data)
        self._value['mean'] = statistics.mean(data)
        self._value['std'] = statistics.stdev(data)           
        return True
    
    def get_value(self, what=None, type=None):
        if what is None:
            return self._value
        else:
            return self._value[what]
        return None
       
    def print_values(self):
        print("[%s] %s"%  (self.name, self.get_value(None)))
        
    def set_on_update_callback(self, callback):
        self._on_sensor_update = callback
              
    '''
    CISSNode function
    '''
    @staticmethod
    def str2bool(v):
        if isinstance(v, str):
            return v.lower() in ("yes", "true", "t", "1")
        elif v:
            return True
        else: 
            return False
                          

class CissXyzSensor(CissSensor):
    
    def __init__(self, node, id='cissXyzSensor', **kwargs):
        CissSensor.__init__(self, node, id, **kwargs)
        self.extra_conf = self._ext_conf.get('range', 0) 
        self._calc_stats_elem = kwargs.get('calc_stats_sub', True) 
        self._x_sensor = CissSensor(self.ciss_node, ("%s_%s"% (id,'x')), 
                                    sensor_id=self.sensor_id, data_type=self.data_type,
                                    unit=self.unit, name=("%s_%s"% (self.name,'x')), publish=self.publish,
                                    statistics=self.statistics, max_data_size=self._max_data_size, 
                                    logger=self.get_logger())
        self._y_sensor = CissSensor(self.ciss_node, ("%s_%s"% (id,'y')), 
                                    sensor_id=self.sensor_id, data_type=self.data_type,
                                    unit=self.unit, name=("%s_%s"% (self.name,'y')), publish=self.publish,
                                    statistics=self.statistics, max_data_size=self._max_data_size, 
                                    logger=self.get_logger())
        self._z_sensor = CissSensor(self.ciss_node, ("%s_%s"% (id,'z')), 
                                    sensor_id=self.sensor_id, data_type=self.data_type,
                                    unit=self.unit, name=("%s_%s"% (self.name,'z')), publish=self.publish,
                                    statistics=self.statistics, max_data_size=self._max_data_size, 
                                    logger=self.get_logger())
        
    def update_value_ext(self, stream_data):
        if not self.enabled:
            return None
        value_x = stream_data.get(self._x_sensor.get_base_id(), None)
        if value_x is None or value_x == "":
            return None            
        value_y = stream_data.get(self._y_sensor.get_base_id(), None)
        value_z = stream_data.get(self._z_sensor.get_base_id(), None)        
        if value_y is None or value_z is None:
            return None
        
        timestamp = stream_data.get('timestamp', None)
        if self._x_sensor.update_value(value_x, timestamp) is None:
            return None
        if self._y_sensor.update_value(value_y, timestamp) is None:
            return None
        if self._z_sensor.update_value(value_z, timestamp) is None:
            return None       
        # ToDo check performance impact
        #return self.update_value(math.sqrt(value_x**2 + value_y**2 + value_z**2), timestamp)
        return self.update_value((abs(value_x) + abs(value_y) + abs(value_z)), timestamp)
  
    def get_value(self, what=None, type=None):
        if type is None:            
            return CissSensor.get_value(self, what)
        else:
            return self.get_sensor(type).get_value(what)              
        return None
    
    def get_sensor(self, type):
        if type is 'x':
            return self._x_sensor
        elif type is 'y':
            return self._y_sensor
        elif type is 'z':
            return self._z_sensor
        else:
            raise ValueError('Sensor type %s unknown'% type)
        return None
    
    def calc_statistics(self):
        if not CissSensor.calc_statistics(self):
            return False
        if self._calc_stats_elem:
            self._x_sensor.calc_statistics()
            self._y_sensor.calc_statistics()
            self._z_sensor.calc_statistics()          
        return True    


class AppCissNode(AppBase, CISSNode):
     
    def __init__(self, id='cissNode', **kwargs):
        AppBase.__init__(self, id, **kwargs)
        self._ext_conf = kwargs.get('conf', {})  
        self.name = self._ext_conf.get('name', 'Dummy')
        
        self._serial_stop = False
        self._serial_port = self._ext_conf.get('com_port', '/dev/ttyACM0')
        self._serial_read_timeout = 1
        self._serial_thread = None
        self._serial_connected = False
        
        self._stream_save_data = kwargs.get('stream_save_data', False)
        if self._stream_save_data:        
            self._stream_data = deque(maxlen=kwargs.get('max_data_size', 100))
        else:
            self._stream_data = None
        if 'sensors' not in self._ext_conf or not isinstance(self._ext_conf['sensors'], dict):
            raise ValueError('Sensor configurations messing')

        self._sensors = {
            SnIx.ACCL.value: CissXyzSensor(self, SnIx.ACCL.value, sensor_id=0x80, 
                                            data_type=0x02, unit='mg', data_length=0,
                                            conf=self._ext_conf['sensors'].get(SnIx.ACCL.value),
                                            logger=self.get_logger()), 
            SnIx.MAGN.value: CissXyzSensor(self, SnIx.MAGN.value, sensor_id=0x81,
                                            data_type=0x03, unit='uT', data_length=0,
                                            conf=self._ext_conf['sensors'].get(SnIx.MAGN.value),
                                            logger=self.get_logger()), 
            SnIx.GYRO.value: CissXyzSensor(self, SnIx.GYRO.value, sensor_id=0x82,
                                            data_type=0x04, unit='d/s', data_length=0,
                                            conf=self._ext_conf['sensors'].get(SnIx.GYRO.value),
                                            logger=self.get_logger()), 
            SnIx.TEMP.value: CissSensor(self, SnIx.TEMP.value, sensor_id=0x83,
                                            data_type=0x05, unit='C', data_length=0,
                                            conf=self._ext_conf['sensors'].get(SnIx.TEMP.value),
                                            logger=self.get_logger()), 
            SnIx.HUMI.value: CissSensor(self, SnIx.HUMI.value, sensor_id=0x83,
                                            data_type=0x07, unit='%', data_length=0,
                                            conf=self._ext_conf['sensors'].get(SnIx.HUMI.value),
                                            logger=self.get_logger()), 
            SnIx.PRES.value: CissSensor(self, SnIx.PRES.value, sensor_id=0x83,
                                            data_type=0x06, unit='hPas', data_length=0,
                                            conf=self._ext_conf['sensors'].get(SnIx.PRES.value),
                                            logger=self.get_logger()),
            SnIx.LIGHT.value: CissSensor(self, SnIx.LIGHT.value, sensor_id=0x84,
                                            data_type=0x08, unit='lx', data_length=0,
                                            conf=self._ext_conf['sensors'].get(SnIx.LIGHT.value),
                                            logger=self.get_logger()),
            SnIx.NOISE.value: CissSensor(self, SnIx.NOISE.value, sensor_id=0x85,
                                            data_type=0x09, unit='?', data_length=0,
                                            conf=self._ext_conf['sensors'].get(SnIx.NOISE.value),
                                            logger=self.get_logger())            
            }  
        self._serial_data_map = {}
        for ix, sensor in self._sensors.items():
            self._serial_data_map[sensor.data_type] = self._sensors[ix]            
        
        self.ser = serial.Serial(baudrate=19200, timeout=self._serial_read_timeout)
        self.ser.port = self._serial_port        
        CISSNode.__init__(self)  
        return 
    
    '''
    CISSNode function
    '''
    def get_ini_config(self):
        global sensor_id_glbl
        global iniFileLocation
        global dataFileLocation
        global dataFileLocationEvent
        global printInformation
        global printInformation_Conf        
        
        sensor_id_glbl = self.name
        self.sensorid = self.name
        
        iniFileLocation = None
        printInformation = self._ext_conf.get('ini_print', True)
        printInformation_Conf = self._ext_conf.get('ini_print', True)         


        #sample_period_inert_us = self._ext_conf.get('sample_period_inert', 100000)
        #sample_period_env_us = self._ext_conf.get('sample_period_env', 1000000)/1000000 
          
        if self.get_sensor(SnIx.TEMP.value).stream_enabled \
            or self.get_sensor(SnIx.HUMI.value).stream_enabled \
            or self.get_sensor(SnIx.PRES.value).stream_enabled:
            self.streaminglist["env"].streaming_enabled = True
            self.streaminglist["env"].streaming_period = max(self.get_sensor(SnIx.TEMP.value).stream_period,
                                                             self.get_sensor(SnIx.HUMI.value).stream_period,
                                                             self.get_sensor(SnIx.PRES.value).stream_period)
        else:
            self.streaminglist["env"].streaming_enabled = False
                         
        self.log_info('Env Sensors Streaming %s Period %d us', self.streaminglist["env"].streaming_enabled,
                                                             self.streaminglist["env"].streaming_period)                 
                         
        self.streaminglist["light"].streaming_enabled = self.get_sensor(SnIx.LIGHT.value).stream_enabled
        self.streaminglist["light"].streaming_period = self.get_sensor(SnIx.LIGHT.value).stream_period
               
        self.log_info('Light Sensor Streaming %s Period %d us', self.streaminglist["light"].streaming_enabled,
                                                             self.streaminglist["light"].streaming_period)                
               
        self.streaminglist["acc"].streaming_enabled = self.get_sensor(SnIx.ACCL.value).stream_enabled
        self.streaminglist["acc"].streaming_period = self.get_sensor(SnIx.ACCL.value).stream_period
        
        self.log_info('ACCL Sensor Streaming %s Period %d us', self.streaminglist["acc"].streaming_enabled,
                                                             self.streaminglist["acc"].streaming_period)          
        
        self.streaminglist["mag"].streaming_enabled = self.get_sensor(SnIx.MAGN.value).stream_enabled
        self.streaminglist["mag"].streaming_period = self.get_sensor(SnIx.MAGN.value).stream_period
        
        self.log_info('MAGN Sensor Streaming %s Period %d us', self.streaminglist["mag"].streaming_enabled,
                                                             self.streaminglist["mag"].streaming_period)        
        
        self.streaminglist["gyr"].streaming_enabled = self.get_sensor(SnIx.GYRO.value).stream_enabled
        self.streaminglist["gyr"].streaming_period = self.get_sensor(SnIx.GYRO.value).stream_period
        
        self.log_info('GYRO Sensor Streaming %s Period %d us', self.streaminglist["gyr"].streaming_enabled,
                                                             self.streaminglist["gyr"].streaming_period)         
        
        if self.get_sensor(SnIx.TEMP.value).event_enabled \
            or self.get_sensor(SnIx.HUMI.value).event_enabled \
            or self.get_sensor(SnIx.PRES.value).event_enabled:
            self.eventlist["env"].event_enabled = True
            self.eventlist["env"].event_threshold = [int(self.get_sensor(SnIx.TEMP.value).event_threshold),
                                                     int(self.get_sensor(SnIx.HUMI.value).event_threshold),
                                                     int(self.get_sensor(SnIx.PRES.value).event_threshold)]
        else:
            self.eventlist["env"].event_enabled = False
            
        self.eventlist["acc"].event_enabled = self.get_sensor(SnIx.ACCL.value).event_enabled
        self.eventlist["acc"].event_threshold = [int(self.get_sensor(SnIx.ACCL.value).event_threshold)]
        self.eventlist["mag"].event_enabled = self.get_sensor(SnIx.MAGN.value).event_enabled
        self.eventlist["mag"].event_threshold = [int(self.get_sensor(SnIx.MAGN.value).event_threshold)]
        self.eventlist["gyr"].event_enabled = self.get_sensor(SnIx.GYRO.value).event_enabled
        self.eventlist["gyr"].event_threshold = [int(self.get_sensor(SnIx.GYRO.value).event_threshold)]
        self.eventlist["light"].event_enabled = self.get_sensor(SnIx.LIGHT.value).event_enabled
        self.eventlist["light"].event_threshold = [int(self.get_sensor(SnIx.LIGHT.value).event_threshold)]
        #noise is not actually not streamed over USB 
        self.eventlist["noise"].event_enabled = self.get_sensor(SnIx.NOISE.value).event_enabled
        self.eventlist["noise"].event_threshold = [int(self.get_sensor(SnIx.NOISE.value).event_threshold)]
        
        self.acc_range = int(self.get_sensor(SnIx.ACCL.value).extra_conf)
        
        if not os.path.exists(self._serial_port):
            raise ValueError('Serial Port %s not found'% self._serial_port)
            return False

        self.ser.port = self._serial_port
        return True
    
    def update_sensor_values(self, stream_data, data_type):
        #self.log_debug('Update Sensors %d, [%s]', data_type, stream_data)
        if data_type in self._serial_data_map:
            self._serial_data_map[data_type].update_value_ext(stream_data)
        else:
            for name, sensor in self._sensors.items():
                sensor.update_value_ext(stream_data)        
        return True  
          
    def read_sensor_stream_until(self, number, timeout=0, loop_delay=0.01):
        self.log_debug('read_sensor_stream_until(%s, %s, %s)', number, timeout, loop_delay) 
        retry = 0
        t = AppTimer()
        t.start()
        ix = 0
        while not self._serial_stop and (number == 0 or (ix < number)):
            ix = ix + 1
            try: 
                if not self.is_connected():
                    self.connect()                    
                    if not self.is_connected():
                        self.set_error_str(AppErrorCode.ERROR.value, 'Failed to re-connect to Serial Port %s', self._serial_port)
                        break                    
                    self.reconfigure_sensors()
                if not self.read_sensor_stream():
                    break
            except serial.SerialException as e:
                self.log_exception('Read Serial Stream Exception! Port %s', self._serial_port)
                self.set_error_str(AppErrorCode.EXCEPTION.value, 'Failed to read Serial Port')
                if retry < 3:
                    retry = retry +  1
                    continue
                break
            
            if timeout != 0:
                if t.is_elapsed(timeout):
                    #self.log_debug('Collect time elapsed!')
                    break
            if loop_delay:
                time.sleep(loop_delay)
        
        self.log_debug('Collected %d times in %d ms', ix, t.get_elapsed())  
        if self.has_error(): return False      
        else: return True
        
    def read_sensor_thread(self, loop_delay):
        self.log_info('Sensor read stream started!')
        if not self.read_sensor_stream_until(0, 0, loop_delay):
            self.disconnect()
            return False
        return True
    
    def start_read_thread(self):
        self.log_info('Starting sensor read stream thread!')
        self.clear_error()
        self._serial_thread = threading.Thread(name=self.get_base_id(), 
                                               target=self.read_sensor_thread, 
                                               args=[0.01], kwargs={})  
        self._serial_thread.start() 
        return True        
       
    def thread_is_alive(self):
        if self._serial_thread is not None:
            return self._serial_thread.is_alive()
        else:
            return False
        
    def calc_statistics(self):
        for id, sensor in self._sensors.items():
            sensor.calc_statistics()
        return True        
       
    def get_sensors(self):
        return self._sensors    
    
    def get_sensor(self, short_name):
        if short_name in self._sensors:
            return self._sensors[short_name]
        else:
            raise ValueError('Sensor %s unknown!'% short_name)
        return None
    
    def get_sensor_value(self, short_name, what=None, type=None):
        return self.get_sensor(short_name).get_value(what, type)
    
    def print_sensor_values(self, all=True):
        if all:
            for id, sensor in self._sensors.items():
                sensor.print_values()            
                if isinstance(sensor, CissXyzSensor):
                    sensor.get_sensor('x').print_values()
                    sensor.get_sensor('y').print_values()
                    sensor.get_sensor('z').print_values()
        else:
            tmp = {}
            for id, sensor in self._sensors.items():
                tmp[sensor.name] = sensor.get_value('current')      
                if isinstance(sensor, CissXyzSensor):
                    tmp[sensor.get_sensor('x').name] = sensor.get_value('current', 'x')
                    tmp[sensor.get_sensor('y').name] = sensor.get_value('current','y')
                    tmp[sensor.get_sensor('z').name] = sensor.get_value('current','z')
            print('[%s] %s'% (self.name, str(tmp)))
        return True

       
    '''
    Overwrite CISSNode function
    '''         
    def read_sensor_stream(self): 
        #self.log_debug('read_ciss_sensor_stream')         
        out = "" 
        sof = "\xFE"
        data = []
        sub_payload = []
        payload_found = 0
        payload = []
        
        while  payload_found != 1:
            if not self.ser.is_open:
                self.log_error('Serial Port Closed! Exit!')
                return False
            while not out == sof:
                out = self.ser.read()
    
            length = self.ser.read()
            if length:
                length = ord(length)
            else:
                continue
            buffer = self.ser.read(length+1)
            payload = self.conv_data(buffer)
            payload.insert(0, length)
            out = ""
            if self.check_payload(payload) == 1:
                payload_found = 1
                self.parse_payload(payload)   
                              
        return True
    
    '''
    Overwrite CISSNode function
    '''
    @staticmethod            
    def conv_data(data):
        a = []
        for ind in range(len(data)):
            a.insert(ind, ord(data[ind]))
        return a
    
    '''
    Overwrite CISSNode function
    '''
    @staticmethod
    def check_payload(payload):
        eval = 0
        for ind in range(len(payload)-1):
            eval = eval ^ payload[ind]
    
        if eval == payload[len(payload)-1]:
            return 1
        else:
            return 0

    '''
    Overwrite CISSNode function
    '''            
    def parse_payload(self, payload):
        #self.log_debug('parse_payload') 
        payload.pop(0)
        payload.pop(len(payload)-1)
        while len(payload) != 0:
            t = self.get_type(payload[0])
            data_type = payload.pop(0)
            if t >= 0:
                mask = self.sensorlist[t].parse(payload[0:self.sensorlist[t].data_length])
                #self.log_debug('Paylod Type %d, lenght %d, Data [%s]', t, len(mask), str(mask))
                if len(mask):
                    tempDict = self.save_to_dict(self.sensorid, mask, time.time())
                    if self._stream_data is not None:
                        self._stream_data.append(tempDict)
                    self.update_sensor_values(tempDict, data_type)
                payload = payload[self.sensorlist[t].data_length:]
            else:
                break
            
    def save_to_dict(self, id, buff, tstamp):
        #self.log_debug('write_to_dict') 
        if len(buff) < 14:
            return {}        
        tempDict = {    
            'id': id,
            'timestamp': tstamp,
             SnIx.ACCL_X.value: buff[0],
             SnIx.ACCL_Y.value: buff[1],
             SnIx.ACCL_Z.value: buff[2],
             
             SnIx.GYRO_X.value: buff[3],
             SnIx.GYRO_Y.value: buff[4],
             SnIx.GYRO_Z.value: buff[5],
             
             SnIx.MAGN_X.value: buff[6],
             SnIx.MAGN_Y.value: buff[7],
             SnIx.MAGN_Z.value: buff[8],
             
             SnIx.TEMP.value: buff[9],
             SnIx.PRES.value: buff[10],
             SnIx.HUMI.value: buff[11],
             SnIx.LIGHT.value: buff[12],
             SnIx.NOISE.value: buff[13] 
            }
        #self.log_debug('write_to_dict %s', tempDict)
        return tempDict

    '''
    Overwrite CISSNode function
    '''
    def connect(self):
        self.log_info('Open Serial Port %s', self._serial_port)
        if self._serial_stop:
            self.log_error('Serial Port in stop mode! Skipping ...')
            return False
        self.ser.open()    
        self._serial_connected = True
        return         
    
    '''
    Overwrite CISSNode function
    '''
    def disconnect(self):
        self.log_info('Close Serial Port %s', self._serial_port)
        try :
            self.disable_sensors()
        except Exception as e:
            self.log_exception("Exception in disable_sensors")
        
        self.ser.close()
        self.ser.is_open = False
        self._serial_connected = False
        return       
    
    def is_connected(self):
        #self.log_debug('Serial port is open %s', self.ser.is_open)
        return self.ser.is_open and self._serial_connected
    
    def reconfigure_sensors(self):
        self.log_info('Reconfigure Sensors')
        if not self.is_connected():
            self.log_error('Serial Port not opened! %s', self._serial_port)
            return False
        self.disable_sensors()
        time.sleep(1)
        self.config_sensors()
        return True
    
    def do_exit(self):
        self._serial_stop = True
        if self._serial_thread:
            self.log_debug('Wait for serial read thread to stop')
            self._serial_thread.join(self._serial_read_timeout+3)
        if self.ser.is_open:
            self.log_debug('Disconnect from Sensors')
            self.disconnect()
        
    
class AppCissContext(AppContext):
    def __init__(self, args, **kwargs):
        AppContext.__init__(self, args, **kwargs)
        if self._config_file is None:
             self._config_file = 'sensor.json'
        self._ext_conf = {}
        self._run = False       
        self._ciss = {}  
        self._use_threading = True
                 
        
    def init_context(self):
        self.log_info('Init Context! ...')
        
        self._ext_conf = AppContext.import_file(self._config_file, 'json', def_path='/conf')        
        if 'ciss_nodes' not in self._ext_conf:
            self.log_error('Missing Ciss Node configuration!')
            return False
        if self._console_args.com_port is not None and 'cissACM0' in self._ext_conf['ciss_nodes']:
            self.log_info('Overwrite serial com port to %s', self._console_args.com_port)
            self._ext_conf['ciss_nodes']['cissACM0']['com_port'] = self._console_args.com_port
        else:
            self.log_info('Using configuration file for ciss sensor serial port')
            
        for id, node in self._ext_conf['ciss_nodes'].items():
            self._ciss[id] = AppCissNode(id, conf=node, logger=self.get_logger())
        time.sleep(1)

        return True
    
    def run_context(self):
        self.log_info('Run Context! ...')
        
        for id, ciss in self._ciss.items():
            for id, sensor in ciss.get_sensors().items():
                sensor.set_on_update_callback(self.on_sensor_upate_callback)        
        
        if self._use_threading:
            return self.run_threading_loop()
        else:
            return self.run_loop()
                        
        return True
    
    
    def run_threading_loop(self):
        self._run = True
        
        max_interval_time = 5000 # 5 seconds
         
        for id, ciss in self._ciss.items():
           ciss.start_read_thread()    
                        
        while self._run is True: 
            time.sleep(max_interval_time/1000)
            for id, ciss in self._ciss.items(): 
                if not ciss.thread_is_alive() and self._run is True:
                    self.log_error('Sensor %s Read Thread not alive! Restart', ciss.name)
                    ciss.start_read_thread()
                    continue
                ciss.calc_statistics()          
                ciss.print_sensor_values(True)                 
        
        return True
    
    def run_loop(self):        
        self._run = True
        print_all = 10
        
        max_interval_time = 5000 # 5 seconds
        max_interval_count = round(max_interval_time / 150)
        if not max_interval_count: max_interval_count = 1
        
        while self._run is True:             
            for id, ciss in self._ciss.items():           
                ciss.read_sensor_stream_until(max_interval_count, max_interval_time, 0.01)
                ciss.calc_statistics()
                if print_all < 10:
                    ciss.print_sensor_values(False)
                else:
                    ciss.print_sensor_values(True) 
                    print_all = 0
                print_all += 1  
                        
        return True
    
    def on_sensor_upate_callback(self, sensor):
        self.log_debug('Sensor %s Update %d! %s = %s! (%s)', sensor.name, sensor._value_ucount, sensor.value_timestamp, sensor.value, sensor._value_utime_diff)
    
    def do_exit(self, reason):
        self._run = False
        if self._ciss:
            for id, ciss in self._ciss.items():
                ciss.do_exit()          
        return True

'''
'''
def main_argparse(assigned_args = None):  
    # type: (List)  
    """
    Parse and execute the call from command-line.
    Args:
        assigned_args: List of strings to parse. The default is taken from sys.argv.
    Returns: 
        Namespace list of args
    """
    import argparse, logging
    parser = argparse.ArgumentParser(prog="appcmd", description=globals()['__doc__'], epilog="!!Note: .....")
    parser.add_argument("-c", dest="config_file", metavar="Config File", help="Configuration file to use!")
    parser.add_argument("-p", dest="com_port", metavar="Serial Port", help="Overwrite configurations serial Port to use!")
    parser.add_argument("-l", dest="file_level", metavar="File logging", type=int, action="store", default=None, help="Turn on file logging with level.")
    parser.add_argument("-v", "--verbose", dest="verbose_level", action="count", default=None, help="Turn on console DEBUG mode. Max = -vvv")
    parser.add_argument("-V", "--version", action="version", version=__version__) 

    return parser.parse_args(assigned_args)

'''
'''
def main(assigned_args = None):  
    # type: (List)    
       
    try:    
        cargs = main_argparse(assigned_args)
        my_app = AppCissContext(cargs, 
                                app_name='ciss_app', 
                                logger=AppContext.initLogger(cargs.verbose_level, cargs.file_level, None, True))    
        if not my_app.init_context():
            # debug_print_classes() # debuging modules loaded
            return my_app.exit_context(1)
    except KeyboardInterrupt as e:   
        if 'my_app' in locals() and my_app != None: 
            my_app.log_exception('Keyboard Interrupt Exception')
            return my_app.exit_context(e)  
        else:
            traceback.print_exc(file=sys.stdout) 
            return -1     
    except Exception as e:
        # debug_print_classes() # debugging 
        if 'my_app' in locals() and my_app != None: 
            my_app.log_exception('Initialization Exception')
            return my_app.exit_context(e)
        else:
            traceback.print_exc(file=sys.stdout)
            return -1
    else:
        try:
            if not my_app.run_context():
                return my_app.exit_context(1)
            else:
                return my_app.exit_context(0)
        except KeyboardInterrupt as e:
            my_app.log_exception('Keyboard Interrupt Exception')
            return my_app.exit_context(e)                
        except Exception as e:
            # traceback.print_exc(file=sys.stdout)
            my_app.log_exception('Runtime Exception')
            return my_app.exit_context(e)  
                 
    return 0
    
if __name__ == "__main__":     
    sys.exit(main())