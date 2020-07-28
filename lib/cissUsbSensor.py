#!/usr/bin/env python2
'''
Bosch CISS sensor 
'''

'''
Change log
0.2.0 - 2020-07-07 - cg
    Initial version
'''

__author__ = "Christian G."
__license__ = "MIT"
__version__ = '0.2.0'
__status__ = "beta"
    
import sys
import serial
from enum import Enum
from collections import deque


from chgrcodebase import *
from CissUsbConnectord_v2_3_1 import CISSNode


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
    
    def __init__(self, node, id='cissSensor', **kwargs):
        AppBase.__init__(self, id, **kwargs)
        self.ciss_node = node
        self._ext_conf = kwargs.get('conf', None)  
        if not isinstance(self._ext_conf, dict):
            self._ext_conf = dict()
        self.name = self._ext_conf.get('name', self.get_base_id())
        self.unit = self._ext_conf.get('unit', 'n/a')        
        self.enabled = self._ext_conf.get('enabled', 0)
        self.publish = self._ext_conf.get('publish', 0)
        self.stream_enabled = self._ext_conf.get('stream_enabled', 0)
        self.stream_period = self._ext_conf.get('stream_period', 10)
        self.event_enabled = self._ext_conf.get('event_enabled', 0)
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
        self._max_data_size = kwargs.get('max_data_size', 10)
        self._data = deque(maxlen=self._max_data_size)
        self._statistics = self._ext_conf.get('enable_statistics', 0)
        if self._statistics:
            if not check_for_module('statistics'):
                self._statistics = 0
                self.log_error('Statistics Module not found! Disable Statistics')            
        
        self._on_sensor_update = None
        self.log_info('CISS Sensor %s', self.name)        
        return
        
        
    def update_value_ext(self, stream_data):
        if not self.enabled:
            return None
        value = stream_data.get(self.get_base_id(), None)
        if value is None or value == "":
            return None        
        return self.update_value(value, stream_data.get('timestamp', None))
    
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
        
        self.value_timestamp = timestamp
        self._data.append(self.value)        
        # ToDo      
        if self._statistics:  
            self._value['mean'] = statistics.mean(self._data)
            self._value['std'] = statistics.stdev(self._data)        
        
        if self._on_sensor_update:
            self._on_sensor_update(sensor=self)
            
        return value  
    
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
              

class CissXyzSensor(CissSensor):
    
    def __init__(self, node, id='cissXyzSensor', **kwargs):
        CissSensor.__init__(self, node, id, **kwargs)
        self.extra_conf = self._ext_conf.get('range', 0)  
        self._x_sensor = CissSensor(self.ciss_node, ("%s_%s"% (id,'x')), max_data_size=self._max_data_size, logger=self.get_logger())
        self._y_sensor = CissSensor(self.ciss_node, ("%s_%s"% (id,'y')), max_data_size=self._max_data_size, logger=self.get_logger())
        self._z_sensor = CissSensor(self.ciss_node, ("%s_%s"% (id,'z')), max_data_size=self._max_data_size, logger=self.get_logger())
        
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
        
        return self.update_value((abs(int(value_x)) + abs(int(value_y)) + abs(int(value_z))), timestamp)
  
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


class AppCissNode(AppBase, CISSNode):
     
    def __init__(self, id='cissNode', **kwargs):
        AppBase.__init__(self, id, **kwargs)
        self._ext_conf = kwargs.get('conf', {})  
        self.name = self._ext_conf.get('name', 'Dummy')
        self._serial_port = self._ext_conf.get('com_port', '/dev/ttyACM0')
        self._serial_stop = False
        
        self._stream_data = deque(maxlen=kwargs.get('max_data_size', 100))
        if 'sensors' not in self._ext_conf or not isinstance(self._ext_conf['sensors'], dict):
            raise ValueError('Sensor configurations messing')

        self._sensors = {
            SnIx.ACCL.value: CissXyzSensor(self, SnIx.ACCL.value, 
                                            conf=self._ext_conf['sensors'].get(SnIx.ACCL.value),
                                            logger=self.get_logger()),
            SnIx.GYRO.value: CissXyzSensor(self, SnIx.GYRO.value, 
                                            conf=self._ext_conf['sensors'].get(SnIx.GYRO.value),
                                            logger=self.get_logger()),
            SnIx.MAGN.value: CissXyzSensor(self, SnIx.MAGN.value, 
                                            conf=self._ext_conf['sensors'].get(SnIx.MAGN.value),
                                            logger=self.get_logger()),
            SnIx.TEMP.value: CissSensor(self, SnIx.TEMP.value, 
                                            conf=self._ext_conf['sensors'].get(SnIx.TEMP.value),
                                            logger=self.get_logger()),
            SnIx.HUMI.value: CissSensor(self, SnIx.HUMI.value, 
                                            conf=self._ext_conf['sensors'].get(SnIx.HUMI.value),
                                            logger=self.get_logger()),
            SnIx.PRES.value: CissSensor(self, SnIx.PRES.value, 
                                            conf=self._ext_conf['sensors'].get(SnIx.PRES.value),
                                            logger=self.get_logger()),
            SnIx.LIGHT.value: CissSensor(self, SnIx.LIGHT.value, 
                                            conf=self._ext_conf['sensors'].get(SnIx.LIGHT.value),
                                            logger=self.get_logger()),
            SnIx.NOISE.value: CissSensor(self, SnIx.NOISE.value, 
                                            conf=self._ext_conf['sensors'].get(SnIx.NOISE.value),
                                            logger=self.get_logger())            
            }  
        self.ser = serial.Serial(baudrate=19200, timeout=1)
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
                         
        self.streaminglist["light"].streaming_enabled = self.get_sensor(SnIx.LIGHT.value).stream_enabled
        self.streaminglist["light"].streaming_period = self.get_sensor(SnIx.LIGHT.value).stream_period
               
        self.streaminglist["acc"].streaming_enabled = self.get_sensor(SnIx.ACCL.value).stream_enabled
        self.streaminglist["acc"].streaming_period = self.get_sensor(SnIx.LIGHT.value).stream_period
        
        self.streaminglist["mag"].streaming_enabled = self.get_sensor(SnIx.MAGN.value).stream_enabled
        self.streaminglist["mag"].streaming_period = self.get_sensor(SnIx.LIGHT.value).stream_period
        
        self.streaminglist["gyr"].streaming_enabled = self.get_sensor(SnIx.GYRO.value).stream_enabled
        self.streaminglist["gyr"].streaming_period = self.get_sensor(SnIx.LIGHT.value).stream_period
        
        if self.get_sensor(SnIx.TEMP.value).event_enabled \
            or self.get_sensor(SnIx.HUMI.value).event_enabled \
            or self.get_sensor(SnIx.PRES.value).event_enabled:
            self.streaminglist["env"].event_enabled = True
            self.eventlist["env"].event_threshold = [int(self.get_sensor(SnIx.TEMP.value).event_threshold),
                                                     int(self.get_sensor(SnIx.HUMI.value).event_threshold),
                                                     int(self.get_sensor(SnIx.PRES.value).event_threshold)]
        else:
            self.streaminglist["env"].event_enabled = False
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
    
    def update_sensor_values(self, stream_data):
        for name, sensor in self._sensors.items():
            sensor.update_value_ext(stream_data)        
        return True  
    
    def process_stream_data(self, number, timeout=None):
        self.log_debug('process_stream_data(%s, %s)', number, timeout) 
        try:
            data = self._stream_data.popleft()
        except IndexError as e:
            self.log_info('No entries found in stream data')
            return True 
                   
        if timeout is not None:
            t = AppTimer()
            t.start()
 
        ix = 0
        while ix < number and data is not None:
            ix = ix + 1
            self.update_sensor_values(data)
            if timeout != None:
                if t.is_elapsed(timeout):
                    #self.log_debug('Collect time elapsed!')
                    break
            try:
                data = self._stream_data.popleft()
            except IndexError as e:
                self.log_info('No entries anymore in stream data')
                return True            
        return True
        
    def collect_sensor_stream_until(self, number, timeout=0, loop_delay=0.1):
        self.log_info('collect_sensor_stream(%s, %s)', number, timeout) 
        if timeout != 0:
            t = AppTimer()
            t.start()
        ix = 0
        while ix < number and not self._serial_stop:
            ix = ix + 1
            try: 
                if not self.ser.is_open:
                    self.ser.open()
                    if not self.ser.is_open:
                        raise ValueError('Failed to open Serial Port')
                if not self.read_ciss_sensor_stream():
                    return False
            except serial.SerialException as e:
                self.log_exception('Read Serial Stream Exception!')
            
            if timeout != 0:
                if t.is_elapsed(timeout):
                    #self.log_debug('Collect time elapsed!')
                    break
            if loop_delay:
                time.sleep(loop_delay)
        return True
    
    def get_sensor(self, short_name):
        if short_name in self._sensors:
            return self._sensors[short_name]
        else:
            raise ValueError('Sensor %s unknown!'% short_name)
        return None
    
    def get_sensor_value(self, short_name, what=None, type=None):
        return self.get_sensor(short_name).get_value(what, type)
    
    def get_sensors(self):
        return self._sensors
    
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
       
    @staticmethod
    def is_integer_num(n):
        if isinstance(n, int):
            return True
        if isinstance(n, float):
            return n.is_integer()
        return False
    
    @staticmethod
    def get_sensor_value(stream_data, sensor, default, absolute=False):
        tmp = stream_data.get(sensor, default)
        if not AppCissNode.is_integer_num(tmp):
            tmp = 0
        if absolute:
            return abs(tmp)
        else:
            return tmp
            
    def read_ciss_sensor_stream(self): 
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
    CISSNode function
    '''
    @staticmethod            
    def conv_data(data):
        a = []
        for ind in range(len(data)):
            a.insert(ind, ord(data[ind]))
        return a
    
    '''
    CISSNode function
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
    CISSNode function
    '''            
    def parse_payload(self, payload):
        #self.log_debug('parse_payload') 
        payload.pop(0)
        payload.pop(len(payload)-1)
        while len(payload) != 0:
            t = self.get_type(payload[0])
            payload.pop(0)
            if t >= 0:
                mask = self.sensorlist[t].parse(payload[0:self.sensorlist[t].data_length])
                #self.log_debug('Paylod Type %d, lenght %d, Data [%s]', t, len(mask), str(mask))
                if len(mask):
                    tempDict = self.save_to_dict(self.sensorid, mask, time.time())
                    self._stream_data.append(tempDict)
                    self.update_sensor_values(tempDict)
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
             SnIx.HUMI.value: buff[10],
             SnIx.PRES.value: buff[11],
             SnIx.LIGHT.value: buff[12],
             SnIx.NOISE.value: buff[13] 
            }
        #self.log_debug('write_to_dict %s', tempDict)
        return tempDict

    '''
    CISSNode function
    '''
    def connect(self):
        if self._serial_stop:
            self.log_error('Serial Port in stop mode!')
            return False
        return self.ser.open()            
    
    def do_exit(self):
        self._serial_stop = True
        if self.ser.is_open:
            self.disconnect()
        
    
class AppCissContext(AppContext):
    def __init__(self, args, **kwargs):
        AppContext.__init__(self, args, **kwargs)
        if self._config_file is None:
             self._config_file = 'sensor.json'
        self._ext_conf = {}
        self._run = False       
        self._ciss = {}  
                 
        
    def init_context(self):
        self.log_info('Init Context! ...')
        self._ext_conf = AppContext.import_file(self._config_file, 'json', def_path='/conf')        
        if 'ciss_nodes' not in self._ext_conf:
            self.log_error('Missing Ciss Node configuration!')
            return False
        for id, node in self._ext_conf['ciss_nodes'].items():
            self._ciss[id] = AppCissNode(id, conf=node, logger=self.get_logger())

        return True
    
    def run_context(self):
        self.log_info('Run Context! ...')
        
        for id, ciss in self._ciss.items():
            for id, sensor in ciss.get_sensors().items():
                sensor.set_on_update_callback(self.on_sensor_upate_callback)        
        
        self._run = True
        print_all = 10
        while self._run == True: 
            
            for id, ciss in self._ciss.items():               
                ciss.collect_sensor_stream_until(20, 5000, 0.1)
                if print_all < 10:
                    ciss.print_sensor_values(False)
                else:
                    ciss.print_sensor_values(True) 
                    print_all = 0
                print_all += 1               
                
        return True
    
    def on_sensor_upate_callback(self, sensor):
        self.log_debug('Sensor %s Update! %s = %s', sensor.name, sensor.value_timestamp, sensor.value)
    
    def do_exit(self, reason):
        self._run = False
        time.sleep(5)
        if self._ciss:
            for id, ciss in self._ciss.items():
                ciss.do_exit()          
        return True

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