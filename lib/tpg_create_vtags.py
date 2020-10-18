#!/usr/bin/env python3
'''
Create Virtual Tags on ThingsPro Gateway 
Based on configuration file for initial setup. 
'''

'''
Change log
0.2.0 - 2020-10-10 - cg
    Resturcture +TpgEquipmentApp
    
0.1.0 - 2020-07-07 - cg
    Initial version
'''

__author__ = "Christian G."
__license__ = "MIT"
__version__ = '0.2.0'
__status__ = "beta"

import sys
import requests
import json

from .chgrcodebase import *

    
class AppTpgContext(AppContext):
    def __init__(self, args, **kwargs):
        AppContext.__init__(self, args, **kwargs)
        if self._config_file is None:
             self._config_file = 'sensor.json'
        self._ext_conf = {} 
        
    def init_context(self):
        self.log_info('Init Context! ...')
        
        self._ext_conf = AppContext.import_file(self._config_file, 'json', def_path='/conf')        
        if 'ciss_nodes' not in self._ext_conf \
            or 'tpg_vtag_template' not in self._ext_conf:
            self.log_error('Missing Ciss Node configuration!')
            return False
        
        return True

    def run_context(self):
        self.log_info('Run Context! ...') 
        
        equObj = TpgEquipmentApp('tpgAddEqu', mxapitoken = self.tpg_get_mx_api_token(),
                                            equname = self._ext_conf['tpg_vtag_template'],
                                            nodes = self._ext_conf['ciss_nodes'],
                                            logger = self.get_logger())
        
        curEqu = equObj.tpg_check_equipment()
        #print(json.dumps(curEqu, indent=4, sort_keys=True))
        if self._console_args.write_tags:
            if not equObj.tpg_create_equipment(curEqu):
                return False        
        return True
   
    def tpg_get_mx_api_token(self):
        return AppContext.import_file('/etc/mx-api-token', 'text')     


class TpgEquipmentApp(AppBase):
    def __init__(self, id='tpgEqu', **kwargs):
        AppBase.__init__(self, id, **kwargs)  
        self._mx_api_token = kwargs.get('mxapitoken', None) 
        self._equipment_name = kwargs.get('equname', None)
        self._nodes = kwargs.get('nodes', None)
        self._api_url = 'https://localhost/api/v1/mxc/custom/equipments'
        
        if not self._mx_api_token:
            raise AppBaseError('Missing MX API Token') 
        if not self._equipment_name:
            raise AppBaseError('Missing Equipment Name') 
        if not self._nodes:
            raise AppBaseError('Missing Node Tag information')
        return 
    
    def tpg_build_rest_header(self):
        rest_header = {
            "mx-api-token": self._mx_api_token,
            "Content-Type": "application/json"
        } 
        return rest_header        
    
    def tpg_get_vtag_info(self):
        rest_header = self.tpg_build_rest_header()        
        self.log_info('Querry current configured equipment!') 
        r = requests.get(
                self._api_url,
                headers=rest_header,
                verify=False)
        if r.status_code == 200:
            data = r.json()
            #print(json.dumps(data, indent=4, sort_keys=True))
            self.log_info('Query Equipments successfull')
        else:
            self.log_error('Host URL with error! http status code %s', r.status_code)
            return None  
        return data       

    def tpg_check_equipment(self):
        tmpEqu = self.tpg_get_vtag_info()
        if tmpEqu is None:
            return None
        return self.tpg_equipment_exists(tmpEqu, self._equipment_name)
    
    def tpg_equipment_exists(self, current_config, equipmentName):
        if isinstance(current_config, list):
            for entry in current_config:
                if 'equipmentName' in entry and entry['equipmentName'] == equipmentName:
                    self.log_info('Equipment Name %s already configured in ThingsPro!', equipmentName)
                    return entry 
        self.log_info('Equipment list not found!')
        return None

    def tpg_build_new_equipment(self, equipmentName, ciss_nodes, equid=None, excludeTags=[]):
        vtags = {
                    "equipmentName": equipmentName,
                    "equipmentTags": [ ]
                }   
        if equid is not None:
            vtags['id'] = equid
            
        for id, node in ciss_nodes.items():
            for sid, sensor in node['sensors'].items():
                if not sensor['enabled']:
                    self.log_info('Sensor %s disabled. Skipping', sensor['name'])
                    continue
                self.tpg_build_new_equ_tag(vtags, sensor, node['name'], sensor['name'], excludeTags)              
                if sid == 'Accl' or sid == 'Gyro' or sid == 'Magn':
                    for tag_name in [('%s_x'% sensor['name']), ('%s_y'% sensor['name']), ('%s_z'% sensor['name'])]:
                        self.tpg_build_new_equ_tag(vtags, sensor, node['name'], tag_name, excludeTags)  
                        
        self.log_info('Equipment %d tags created!', len(vtags['equipmentTags']))
        #print(json.dumps(vtags, indent=4, sort_keys=False))        
        return vtags
    
    def tpg_build_new_equ_tag(self, vtags, sensor, node_name, sensor_name, excludeTags=[]):
        if sensor['enable_statistics']: 
            value_list = ['current', 'min', 'max', 'mean', 'std']
        else:
            value_list = ['current']
        for what in value_list:
            tag_name = self.tpg_publish_tag_name(node_name, sensor_name, what)
            if tag_name in excludeTags:
                self.log_info('%s exclude tag %s', node_name, tag_name)
                continue
            tag = {                  
                "name": tag_name,
                "dataType": "uint32",
                "access": "rw",
                "size": 4,
                "description": "n/a"
            }  
            self.log_info('Adding to %s : %s', vtags['equipmentName'], tag)
            vtags['equipmentTags'].append(tag)                  
        return True
    
    def tpg_create_equipment(self, curEqu):
        
        if isinstance(curEqu, dict) and 'id' in curEqu:
            equid=curEqu['id']
            excludeTags = []
            #for tags in curEqu['equipmentTags']:
            #    excludeTags.append(tags['name'])
        else:
            equid=None
            excludeTags=[]
        
        newEqu = self.tpg_build_new_equipment(self._equipment_name, self._nodes, equid, excludeTags)
        
        #print(json.dumps(newEqu, indent=4, sort_keys=True))
                             
        if not self.tpg_write_new_equipment(newEqu):
            return False       
              
        return True
    
    def tpg_write_new_equipment(self, data):
        rest_header = self.tpg_build_rest_header()
        if 'id' in data:
            equID = data['id']
        else:
            equID = None
        
        if equID is None:            
            return self.tpg_add_equipment(data)   
        else:
            return self.tpg_update_equipment(equID, data)                 
        return True
    
    def tpg_add_equipment(self, data):
        self.log_debug('Add equipment tags!')
        rest_header = self.tpg_build_rest_header()           
        r = requests.post(
                self._api_url,
                headers=rest_header,
                json=data,
                verify=False
            )               
        if r.status_code == 200:     
            #resp_data = r.json()        
            #print(json.dumps(resp_data, indent=4, sort_keys=True))
            self.log_info('Added Equipment Tags to ThingsPro!')
        else:
            self.log_error('Host URL with error! http status code %s', r.status_code)
            return False                  
        return True
    
    def tpg_update_equipment(self, equID, data):
        self.log_debug('Update equipment %d tags!', equID)
        rest_header = self.tpg_build_rest_header()           
        r = requests.put(
                '%s/%s'% (self._api_url, equID),
                headers=rest_header,
                json=data,
                verify=False
            )               
        if r.status_code == 200:     
            #resp_data = r.json()        
            #print(json.dumps(resp_data, indent=4, sort_keys=True))
            self.log_info('Updated Equipment %d Tags in ThingsPro!', equID)
        else:
            self.log_error('Host URL with error! http status code %s', r.status_code)
            return False                  
        return True
    
    
    @staticmethod
    def tpg_publish_tag_name(node_name, sensor_name, which):
        tag_name = ('%s-%s-%s'% (node_name, sensor_name, which))
        return tag_name
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
    parser.add_argument("-w", dest="write_tags", action="store_true", help="Write new created Tags to ThingsPro!")
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
        my_app = AppTpgContext(cargs, 
                                app_name='vtag_add_app', 
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