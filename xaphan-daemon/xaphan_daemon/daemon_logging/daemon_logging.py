"""
Module to establish login
"""

import logging
import logging.config
import logging.handlers


class LoggingMethod(object):
    """
    Logger class
    """
    def __init__(self, config_object):
        self.__config = config_object.get('logger')

    def setup_log(self):
        """
        Setups logger object for daemon daemon_logging
        """
        __log_location = '{location}/{name}.log'.format(location=self.__config.get('location',
                                                                                   '/var/log'),
                                                        name=self.__config.get('name',
                                                                               'xaphan-daemon'))
        __logger = logging.getLogger(self.__config.get('name', 'xaphan-daemon'))

        __logger_handlers = int(len(__logger.handlers))
        if __logger_handlers > 0:
            return __logger

        logging.basicConfig(filename=__log_location, level=logging.INFO)
        __logger = logging.getLogger(self.__config['name'])
        formatter = logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
                                      datefmt='%d-%m-%Y %H:%M:%S %z')

        file_handler = logging.handlers.TimedRotatingFileHandler(filename=__log_location,
                                                                 when='midnight',
                                                                 backupCount=int(
                                                                     self.__config.get(
                                                                         'rotation_time', 30)
                                                                 ))
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)

        __logger.addHandler(file_handler)

        return __logger
