#!/usr/bin/env python2
'''
Publish Bosch CISS sensor to ThingsPro Gateway  

Change log
0.1.0 - 2020-07-07 - cg
    Initial version
'''

__author__ = "Christian G."
__license__ = "MIT"
__version__ = '0.1.0'
__status__ = "beta"

import sys

from lib.chgrcodebase import *
from lib.cissUsbSensor import *

from libmxidaf_py import TagV2, Tag, Time, Value


    
class TpgCissContext(AppCissContext):
    def __init__(self, args, **kwargs):
        AppCissContext.__init__(self, args, **kwargs) 
        
        self._modbus_obj = None
        self._tagV2_obj = None 
        self._vtag_tags = None   
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
        self._tagV2_obj = TagV2.instance()      

        return True
    
    def run_context(self):
        self.log_info('Run Context! ...')
        self._run = True                
        while self._run == True: 
            for id, ciss_node in self._ciss.items():
                ciss_node.collect_sensor_stream_until(100, self._tpg_publish_interval)
                ciss_node.print_sensor_values(False)
                self.tpg_publish(ciss_node)     
                self.log_info('Published Sensor data to TPG %s', self._vtag_template_name)           
        return True
    
    def tpg_publish(self, ciss_node):
        self.log_debug('tpg_publish')
        if not isinstance(ciss_node, AppCissNode):
            raise ValueError('Invalid Ciss Node object!')
        for s_id, sensor in ciss_node.get_sensors().items():
            self.tpg_publish_sensor(ciss_node, sensor)
            if isinstance(sensor, CissXyzSensor):
                self.tpg_publish_sensor(ciss_node, sensor.get_sensor('x'))
                self.tpg_publish_sensor(ciss_node, sensor.get_sensor('y'))
                self.tpg_publish_sensor(ciss_node, sensor.get_sensor('z'))              
        return True
        
    def tpg_publish_sensor(self, ciss_node, sensor):
        if sensor.value_timestamp is None:
            vtag = Tag(Value(sensor.value), Time.now(), sensor.unit)
        else:
            vtag = Tag(Value(sensor.value), Time.now(), sensor.unit)
        tag_name = ('%s-%s-current'% (ciss_node.name, sensor.name))
        self._tagV2_obj.publish(self._vtag_template_name, tag_name, vtag)            
        self.log_debug('tagV2 publish to %s tag %s = %s', self._vtag_template_name, tag_name, str(vtag.value()))
        
        return True
    
'''
'''
def main(assigned_args = None):  
    # type: (List)    
       
    try:    
        cargs = main_argparse(assigned_args)
        my_app = TpgCissContext(cargs, 
                                app_name='ciss_tpg', 
                                logger=AppContext.initLogger(cargs.verbose_level, cargs.File_level, None, True))       
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
    
    