#!/usr/bin/env python3
'''
App Template 

Base class implementations  
'''

'''
Change log
1.0.0 - 2020-03-01 - cg
    Initial version
'''

__author__ = "chgrCode"
__license__ = "MIT"
__version__ = '1.0.0'
__maintainer__ = "chgrCode"
__credits__ = ["..."]
__status__ = "beta"

import os 
import sys
import traceback
import signal
import platform
import datetime
import time
from enum import IntEnum


'''
'''
class AppErrorCode(IntEnum):
    OK = 0
    ERROR = 1
    EXCEPTION = ERROR + 1
    TIMEOUT = ERROR + 2

'''
'''
class AppLogLevel(IntEnum):
    CRITICAL = 50
    ERROR = 40
    WARNING = 30
    INFO = 20
    DEBUG = 10
    NOTSET = 0

class AppTimerError(Exception):
    """A custom exception used to report errors in use of AppTimer class"""
       
class AppTimer(object):
    timers = dict()
    
    def __init__(self, name=None):
        self._start_time = None
        self._end_time = None
        self._elapsed_time = None
        self.name = name
        # Add new named timers to dictionary of timers
        if name:
            self.timers.setdefault(name, 0)
        return
    
    @staticmethod
    def timer():
        return (time.time()*1000)
    
    def start(self):
        """Start a new timer"""
        if self._start_time is not None:
            raise AppTimerError('Timer is running. Use .stop() to stop it')
        self._elapsed_time = None
        self._end_time = None
        self._start_time = self.timer()
        

    def stop(self):
        """Stop the timer, and report the elapsed time"""
        if self._start_time is None:
            raise AppTimerError('Timer is not running. Use .start() to start it')
        self._end_time = self.timer()
        self._elapsed_time = self._end_time - self._start_time
        self._start_time = None
        if self.name:
            self.timers[self.name] += self._elapsed_time
        return self._elapsed_time
    
    def is_elapsed(self, timeout):
        if self._start_time is None:
            raise AppTimerError('Timer is not running. Use .start() to start it')        
        self._elapsed_time = self.timer() - self._start_time
        if (self._elapsed_time) >= timeout:
            return True
        else:
            return False
        
    def get_elapsed(self, name = None):
        if name is not None:
            if name in self.timers:
                return self.timers[name]
            else:
                raise AppTimerError('Timer %s unknown!'% name)
        else:
            if self._elapsed_time is None:
                self.is_elapsed(0)
            return self._elapsed_time
            
class AppBaseError(Exception):
    """A custom exception used to report errors in use of AppBase class"""
    
class AppBase(object):        
    ''' Default App Base class constructor '''
    def __init__(self, id='base', **kwargs):
        """
        @param id, kwargs: ....
        @type id: str, 
        @return None: ...
        @rtype: ...
        @raise e: ...
        http://epydoc.sourceforge.net/manual-fields.html#module-metadata-variables
        """            
        self._logger = kwargs.get('logger', None)
        self._logger_level = AppLogLevel.NOTSET.value
        self._base_id = id
        self._error = AppErrorCode.OK.value
        self._error_str = ''
        self._logger_extra = {'base_id': self._base_id}
        return
    
    def get_base_id(self):
        return self._base_id
    
    def set_base_id(self, id):
        self._base_id = id
        return self._base_id
       
    def set_error_str(self, error, error_str):  
        self._error = error
        self._error_str = error_str  
        self.log_debug('set_error_str(%s, %s)', error, error_str) 
        return True    
    
    def get_error_str(self):
        return self._error_str 
       
    def get_error2str(self, error = None):
        if error == None:
            error = self._error
        if isinstance(error, 'AppErrorCode'):
            return error.name
        else:
            errorStr = ('eCode%s'% error)
        #ToDo make a short text version of the error
        return errorStr
    
    def get_error(self):
        return self._error
    
    def has_error(self, error=None):
        if error != None:
            if self._error == error:
                return True
        else:
            if self._error != AppErrorCode.OK.value:
                return True                
        return False
        
    def clear_error(self):
        self.log_debug('Clearing Error %s, %s!', self._error, self._error_str)
        self._error = AppErrorCode.OK.value
        self._error_str = ''
        
    def print_msg(self, level, msg, *args, **kwargs):
        if self._logger_level <= level:
            print ((msg % args)% kwargs)
        
    def set_logger(self, logger):
        # type: (logging.Logger)
        self._logger = logger
        return True
        
    def get_logger(self):
        return self._logger
       
    def log_debug(self, msg, *args, **kwargs):
        if self._logger != None:
            self._logger.debug(msg, *args, extra=self._logger_extra, **kwargs)
        else:
            self.print_msg(AppLogLevel.DEBUG, msg, *args, **kwargs)
        return True
        
    def log_info(self, msg, *args, **kwargs):
        if self._logger != None:
            self._logger.info(msg, *args, extra=self._logger_extra, **kwargs)
        else:
            self.print_msg(AppLogLevel.INFO, msg, *args, **kwargs)            
        return True
        
    def log_warning(self, msg, *args, **kwargs):
        if self._logger != None:
            self._logger.warning(msg, *args, extra=self._logger_extra, **kwargs)
        else:
            self.print_msg(AppLogLevel.WARNING, msg, *args, **kwargs)             
        return True
        
    def log_error(self, msg, *args, **kwargs):
        if self._logger != None:
            self._logger.error(msg, *args, extra=self._logger_extra, **kwargs)
        else:
            self.print_msg(AppLogLevel.ERROR, msg, *args, **kwargs)             
        return True
        
    def log_critical(self, msg, *args, **kwargs):
        if self._logger != None:
            self._logger.critical(msg, *args, extra=self._logger_extra, **kwargs) 
        else:
            self.print_msg(AppLogLevel.CRITICAL, msg, *args, **kwargs)               
        return True 
        
    def log_exception(self, msg, *args, **kwargs):
        if self._logger != None:
            self._logger.exception(msg, *args, extra=self._logger_extra, **kwargs)   
        else:
            msg = msg + "\n" + traceback.format_exc()
            self.print_msg(AppLogLevel.ERROR, msg, *args, **kwargs)             
        return True 

    @staticmethod
    def vlevel_2_log_level(verbose_level):
        if verbose_level >= 3:
            level = AppLogLevel.DEBUG
        elif verbose_level == 2:
            level = AppLogLevel.INFO
        else:
            level = AppLogLevel.ERROR
        return level
                   
 
class AppContext(AppBase):
    
    def __init__(self, argc, **kwargs):
        AppBase.__init__(self, kwargs.get('app_name', 'Context'), **kwargs)
        self._console_args = argc
        self._config_file = argc.config_file      
        self._run = False   
        if argc.verbose_level != None:
            self._logger_level = AppBase.vlevel_2_log_level(argc.verbose_level)
            self.log_info('Enable Console debug verbose level %d', argc.verbose_level)
            self.log_debug('Console Args: %s', str(argc))
        signal.signal(signal.SIGINT, self.signal_exit_gracefully)
        signal.signal(signal.SIGTERM, self.signal_exit_gracefully)          
        return
    
   
    @staticmethod
    def initLogger(console_level, file_level, logger_file, enable_global=False):    
        import logging.handlers
        if enable_global:
            logging._srcfile = None
            global_level = logging.ERROR
            if console_level != None:
                global_level = AppBase.vlevel_2_log_level(console_level)

            logging.basicConfig(format='%(asctime)s - %(name)s.%(threadName)s : %(levelname)+7s : %(message)s',
                                level = global_level, 
                                handlers=[logging.NullHandler()])   

        _logger = logging.getLogger(__name__)
        _logger.propagate = False
        if console_level != None: 
            level = AppBase.vlevel_2_log_level(console_level)
            logFormatStr = '[%(levelname)+7s] %(asctime)s,%(msecs)d - %(threadName)s[%(base_id)s] : %(message)s'           
            ch = logging.StreamHandler(sys.stdout)
            ch.setLevel(level)
            ch.setFormatter(logging.Formatter(logFormatStr, datefmt='%I:%M:%S'))            
            _logger.addHandler(ch)
            logging.info('Enabled Verbose logging level %s!', level)  
                    
        if file_level != None:
            if logger_file == None:
                logger_file = '%s.log'% __name__                
            logFormatStr = '%(asctime)s - %(name)s.%(threadName)s[%(base_id)s] : %(levelname)+7s : %(message)s'
            logrotate = logging.handlers.RotatingFileHandler(
                    logger_file, maxBytes=(1024*1024*10), backupCount=5)
            logrotate.setLevel(file_level)
            logrotate.setFormatter(logging.Formatter(logFormatStr))     
            _logger.addHandler(logrotate)            
            logging.debug('Enabled File logging Level %s to %s!', file_level, logger_file)       
        
        return _logger
    
    @staticmethod
    def import_file(file, type, def_path='/conf'):         
        if not os.access(file, os.R_OK):
            mydir = os.path.dirname(os.path.realpath(__file__))
            mydir = os.path.dirname(sys.argv[0])
            confdir = os.path.abspath(mydir + def_path)
            def_file = os.path.join(confdir, file) 
            if not os.access(def_file, os.R_OK):
                raise AppBaseError('Missing configuration file [%s]!'% file)
            else:
                file = def_file                  
        if type == 'text': 
            h_file = open(file) 
            _ext_content = h_file.read() 
            h_file.close()                  
        elif type == 'json':
            import json
            h_file = open(file)
            _ext_content = json.load(h_file)
            h_file.close()
        else:
            raise AppBaseError('File Type %s not supported!'% type)
        return _ext_content 

    @staticmethod
    def create_working_dir(working_dir, default_name):
        if working_dir == None or not working_dir:
            working_dir = os.path.join(os.getcwd(), '%s_data'% default_name) 
        if not os.path.isdir(working_dir):
            dir_path = os.path.realpath(working_dir)
            os.makedirs(dir_path)
            working_dir = dir_path
        return working_dir    
    
    @staticmethod
    def create_tmp_dir(tmp_name=__name__):
        tmp_dir = os.path.join(tempfile.gettempdir(), tmp_name)
        if not os.path.isdir(tmp_dir):
            os.makedirs(tmp_dir)
        return tmp_dir
       
    def init_context(self):
        self.log_info('Init Context! ...')
        return True
    
    def run_context(self):
        self.log_info('Run Context! ...')  
        self._run = True               
        return True
    
    def do_exit(self, reason):
        return True
    
    def exit_context(self, reason):
        if isinstance(reason, Exception):
            exit_code = AppErrorCode.EXCEPTION.value
        else:
            exit_code = int(reason)  
        self.log_debug('Exit Context! ...')
        self._run = False
        
        if not self.do_exit(reason):
            self.log_error('Failed to clean exit App!')
                   
        self.log_info('Exit Context done! Reason [%s], with exit code %d!', str(reason), exit_code)           
        return exit_code
    
    def stop_run_context(self, reason):
        self.log_info('%s, Stopping ...', reason)
        self._run = False
        return True
    
    def signal_exit_gracefully(self, signum, frame):
        self.stop_run_context(signum)   


