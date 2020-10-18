#!/usr/bin/env python2
'''
Publish Bosch CISS sensor to ThingsPro Gateway  
'''

'''
Change log
0.3.1 - 2020-08-05 - cg
    Add VTag auto create
    
0.3.0 - 2020-08-05 - cg
    Restructure/Updates
    
0.2.0 - 2020-07-07 - cg
    Initial version
'''

__author__ = "Christian G."
__license__ = "MIT"
__version__ = '0.3.1'
__status__ = "beta"

import sys

from lib.chgrcodebase import *
from lib.cissUsbSensor import *
from lib.tpg_create_vtags import TpgEquipmentApp

from libmxidaf_py import TagV2, Tag, Time, Value


    
class TpgCissContext(AppCissContext):
    def __init__(self, args, **kwargs):
        AppCissContext.__init__(self, args, **kwargs) 
        
        self._tagV2_obj = None 
        self._vtag_tags_published = 0   
        self._vtag_template_name = None
        
        self._tpg_publish_interval = 30000 # ms
        return 
        
    def init_context(self):
        if not AppCissContext.init_context(self):
            return False
                
        if 'tpg_vtag_template' not in self._ext_conf:
            self.log_error('Missing TPG Virtual Tag Template Name!')
            return False            
        self._vtag_template_name = self._ext_conf['tpg_vtag_template'] 
        self.log_info('Virtual Tag Device set to %s', self._vtag_template_name)
           
        if 'tpg_publish_interval' in self._ext_conf:         
            self._tpg_publish_interval = int(self._ext_conf['tpg_publish_interval'])*1000            
        self.log_info('Publish interval set to %s ms', self._tpg_publish_interval)  
        if self._console_args.publish_interval != None:
            self._tpg_publish_interval =  self._console_args.publish_interval*1000  
            self.log_info('Publish interval set to %s ms, from console arg!', self._tpg_publish_interval)     
        self._tagV2_obj = TagV2.instance()      
        
        equObj = TpgEquipmentApp('tpgAddEqu', mxapitoken = self.tpg_get_mx_api_token(),
                                            equname = self._ext_conf['tpg_vtag_template'],
                                            nodes = self._ext_conf['ciss_nodes'],
                                            logger = self.get_logger())
        
        curEqu = equObj.tpg_check_equipment()
        if not equObj.tpg_create_equipment(curEqu):
            return False 

        return True
    
    def on_sensor_upate_callback(self, sensor):
        self.log_debug('Sensor %s Update! %s = %s', sensor.name, sensor.value_timestamp, sensor.value)
        return self.tpg_publish_sensor(sensor)
  
    
    def run_context(self):
        self.log_info('Run Context! ...')
        
        if self._tpg_publish_interval == 0:
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
            time.sleep(self._tpg_publish_interval/1000)
            for id, ciss in self._ciss.items(): 
                if not ciss.thread_is_alive() and self._run is True:
                    self.log_error('Sensor %s Read Thread not alive! Restart', ciss.name)
                    ciss.start_read_thread()
                    continue
                ciss.calc_statistics()                       
                if self._logger_level <= AppLogLevel.DEBUG.value:          
                    ciss.print_sensor_values(True)
                if self._tpg_publish_interval != 0:
                    self.tpg_publish(ciss)             
                            
        return True
    
    def run_loop(self):        
        self._run = True
        print_all = 10
        
        while self._run is True:             
            for id, ciss in self._ciss.items():           
                ciss.read_sensor_stream_until(100, self._tpg_publish_interval, 0.01)
                ciss.calc_statistics()
                if self._logger_level <= AppLogLevel.DEBUG.value:
                    if print_all >= 10:
                        ciss.print_sensor_values(True) 
                        print_all = 0
                    print_all += 1
                if self._tpg_publish_interval != 0:
                    self.tpg_publish(ciss) 
                        
        return True    
    
    def tpg_publish(self, ciss_node):
        self.log_debug('tpg_publish')
        if not isinstance(ciss_node, AppCissNode):
            raise ValueError('Invalid Ciss Node object!')
        for s_id, sensor in ciss_node.get_sensors().items():
            self.tpg_publish_sensor(sensor)
            if isinstance(sensor, CissXyzSensor) and (sensor.publish & 0x04):
                self.tpg_publish_sensor(sensor.get_sensor('x'))
                self.tpg_publish_sensor(sensor.get_sensor('y'))
                self.tpg_publish_sensor(sensor.get_sensor('z'))  
        self._vtag_tags_published += 1
        self.log_info('Published %s Sensor data to TPG %s (%d)', ciss_node.name, self._vtag_template_name, self._vtag_tags_published) 

        return True
        
    def tpg_publish_sensor(self, sensor): 
        if not sensor.publish:
            return True      
        if sensor.value_timestamp is None:           
             at = Time.now()
        else:
             # ToDo
             at = Time.now()
        if (sensor.publish & 0x02):
            if sensor.statistics: 
                value_list = ['current', 'min', 'max', 'mean', 'std']
            else:
                value_list = ['current', 'min', 'max']
        else:
            value_list = ['current']
        for what in value_list:
            tValue = Value(int(sensor.get_value(what)))    
            vtag = Tag(tValue, at, sensor.unit)
            tag_name = TpgEquipmentApp.tpg_publish_tag_name(sensor.ciss_node.name, sensor.name, what)
            self._tagV2_obj.publish(self._vtag_template_name, tag_name, vtag)            
            self.log_debug('tagV2 publish to %s tag %s = %s', self._vtag_template_name, tag_name, str(vtag.value()))
        return True
    
    def tpg_get_mx_api_token(self):
        return AppContext.import_file('/etc/mx-api-token', 'text') 
    
#    @staticmethod
#    def tpg_publish_tag_name(node_name, sensor_name, which):
#        tag_name = ('%s-%s-%s'% (node_name, sensor_name, which))
#        return tag_name
    

    
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
    parser.add_argument("-i", dest="publish_interval", metavar="Publish Interval", type=int, help="Overwrite publish interval!")
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
        my_app = TpgCissContext(cargs, 
                                app_name='ciss_tpg', 
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
    
    