#!/usr/bin/env python2
'''
Bosch CISS sensor 

Change log
0.1.0 - 2020-07-07 - cg
    Initial version
'''

__author__ = "Christian G."
__license__ = "MIT"
__version__ = '0.1.0'
__status__ = "beta"
    
import sys
import serial
from enum import Enum
from collections import deque


from chgrcodebase import *
from CissUsbConnectord_v2_3_1 import CISSNode

def check_for_module(module):
    try:
        __import__('imp').find_module(module)
        found = True
    except ImportError:
        found = False
    return found

class CissSensorName(Enum):
    ACCL = 'Acceleration'
    GYRO = 'Gyroscope'
    MAGN = 'Magnetometer'
    TEMP = 'Temperature'
    HUMI = 'Humidity'
    PRES = 'Pressure'
    LIGHT = 'LIGHT'
    NOISE = 'Noise'
    
class CissSensorNameShort(Enum):
    SN_ACCL = 'Accl'
    SN_ACCL_X = 'Accl_x'
    SN_ACCL_Y = 'Accl_y'
    SN_ACCL_Z = 'Accl_z'
    SN_GYRO = 'Gyro'
    SN_GYRO_X = 'Gyro_x'
    SN_GYRO_Y = 'Gyro_y'
    SN_GYRO_Z = 'Gyro_z'
    SN_MAGN = 'Magn'
    SN_MAGN_X = 'Magn_x'
    SN_MAGN_Y = 'Magn_y'
    SN_MAGN_Z = 'Magn_z'
    SN_TEMP = 'Temp'
    SN_HUMI = 'Humi'
    SN_PRES = 'Pres'
    SN_LIGHT = 'Ligh'
    SN_NOISE = 'Nois'
    
    def __str__(self):
        return str(self.value)    

class CissSensor(AppBase):
    
    def __init__(self, id='cissSensor', **kwargs):
        AppBase.__init__(self, id, **kwargs)
        self.name = kwargs.get('name', self.get_base_id())
        self.unit = kwargs.get('unit')
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
        self._statistics = check_for_module('statistics')
        
        
    def update_value_ext(self, stream_data):
        value = stream_data.get(self.get_base_id(), None)
        if value is None:
            return None        
        return self.update_value(value, stream_data.get('timestamp', None))
    
    def update_value(self, value, timestamp):
        if value is None or value == "":
            return None
        if timestamp is None:
            timestamp = time.time()
        self.value_timestamp = timestamp
        self.value = int(value)
        self._value['timestamp'] = self.value_timestamp
        self._value['current'] = self.value
        self._value['min'] = min(self._value['min'], self.value)
        self._value['max'] = max(self._value['max'], self.value)        
        # ToDo      
        if self._statistics:  
            self._value['mean'] = statistics.mean(self._data)
            self._value['std'] = statistics.stdev(self._data)        
        self._data.append(self.value)
        return value  
    
    def get_value(self, what=None):
        if what is None:
            return self._value
        else:
            return self._value[what]
        return None

        
    def print_values(self):
        print("[%s] %s"%  (self.name, self.get_value(None)))

class CissXyzSensor(CissSensor):
    
    def __init__(self, id='cissXyzSensor', **kwargs):
        CissSensor.__init__(self, id, **kwargs)
        self._x_sensor = CissSensor(("%s_%s"% (id,'x')), max_data_size=self._max_data_size)
        self._y_sensor = CissSensor(("%s_%s"% (id,'y')), max_data_size=self._max_data_size)
        self._z_sensor = CissSensor(("%s_%s"% (id,'z')), max_data_size=self._max_data_size)
        
    def update_value_ext(self, stream_data):
        value_x = stream_data.get(self._x_sensor.get_base_id(), None)
        value_y = stream_data.get(self._y_sensor.get_base_id(), None)
        value_z = stream_data.get(self._z_sensor.get_base_id(), None)        
        if value_x is None or value_y is None or value_z is None:
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
        self._ciss_legacy_ini = self._ext_conf.get('ini_file', 'sensor.ini')
        self._serial_port = self._ext_conf.get('com_port', '/dev/ttyACM0')
        self._serial_stop = False
        
        self._stream_data = deque(maxlen=kwargs.get('max_data_size', 100))  
        self._sensors = {
            CissSensorNameShort.SN_ACCL.value: CissXyzSensor(CissSensorNameShort.SN_ACCL.value),
            CissSensorNameShort.SN_GYRO.value: CissXyzSensor(CissSensorNameShort.SN_GYRO.value),
            CissSensorNameShort.SN_MAGN.value: CissXyzSensor(CissSensorNameShort.SN_MAGN.value),
            CissSensorNameShort.SN_TEMP.value: CissSensor(CissSensorNameShort.SN_TEMP.value),
            CissSensorNameShort.SN_HUMI.value: CissSensor(CissSensorNameShort.SN_HUMI.value),
            CissSensorNameShort.SN_PRES.value: CissSensor(CissSensorNameShort.SN_PRES.value),
            CissSensorNameShort.SN_LIGHT.value: CissSensor(CissSensorNameShort.SN_LIGHT.value),
            CissSensorNameShort.SN_NOISE.value: CissSensor(CissSensorNameShort.SN_NOISE.value)            
            }  
        self.ser = serial.Serial()
        self.ser.baudrate = 19200
        self.ser.timeout = 1
        self.ser.port = self._serial_port        
        CISSNode.__init__(self)  
        return 
    
    def get_ini_config(self):
        global sensor_id_glbl
        global iniFileLocation
        global dataFileLocation
        global dataFileLocationEvent
        global printInformation
        global printInformation_Conf        
        
        sensor_id_glbl = self.name
        iniFileLocation = self._ciss_legacy_ini 
        printInformation = True
        printInformation_Conf = True         
        
        CISSNode.get_ini_config(self)
        
        if not os.path.exists(self.port):
            raise ValueError('Serial Port %s not found'% self.port)
            return False
        self._serial_port = self.port 
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
        
    def collect_sensor_stream_until(self, number, timeout=None, loop_delay=0.1):
        self.log_info('collect_sensor_stream(%s, %s)', number, timeout) 
        if timeout != None:
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
            
            if timeout != None:
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
    
    def get_sensor_value(self, short_name, type=None):
        sensor = self._get_sensor(short_name)
        return sensor.get_value(type)
    
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
        out = 0 
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
    
    @staticmethod            
    def conv_data(data):
        a = []
        for ind in range(len(data)):
            a.insert(ind, ord(data[ind]))
        return a
    
    @staticmethod
    def check_payload(payload):
        eval = 0
        for ind in range(len(payload)-1):
            eval = eval ^ payload[ind]
    
        if eval == payload[len(payload)-1]:
            return 1
        else:
            return 0
                
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
             CissSensorNameShort.SN_ACCL_X.value: buff[0],
             CissSensorNameShort.SN_ACCL_Y.value: buff[1],
             CissSensorNameShort.SN_ACCL_Z.value: buff[2],
             
             CissSensorNameShort.SN_GYRO_X.value: buff[3],
             CissSensorNameShort.SN_GYRO_Y.value: buff[4],
             CissSensorNameShort.SN_GYRO_Z.value: buff[5],
             
             CissSensorNameShort.SN_MAGN_X.value: buff[6],
             CissSensorNameShort.SN_MAGN_Y.value: buff[7],
             CissSensorNameShort.SN_MAGN_Z.value: buff[8],
             
             CissSensorNameShort.SN_TEMP.value: buff[9],
             CissSensorNameShort.SN_HUMI.value: buff[10],
             CissSensorNameShort.SN_PRES.value: buff[11],
             CissSensorNameShort.SN_LIGHT.value: buff[12],
             CissSensorNameShort.SN_NOISE.value: buff[13] 
            }
        self.log_debug('write_to_dict %s', tempDict)
        return tempDict
    
    def connect(self):
        if self._serial_stop:
            raise ValueError('Serial Port in stop mode!')
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
        for node in self._ext_conf['ciss_nodes']:
            if 'id' not in node:
                self.log_error('Missing Ciss Node id in configuration')
                return False
            if node['id'] in self._ciss:
                self.log_error('Node ID %s already used!', node['id'])
                return False
            self._ciss[node['id']] = AppCissNode(node['id'], conf=node, logger=self.get_logger())
        return True
    
    def run_context(self):
        self.log_info('Run Context! ...')
        self._run = True
        print_all = True
        while self._run == True: 
            
            for id, ciss in self._ciss.items():               
                ciss.collect_sensor_stream_until(20, 5000)
                if print_all:
                    print_all = False
                else:
                    print_all = True                
                ciss.print_sensor_values(print_all)
                
        return True
    
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