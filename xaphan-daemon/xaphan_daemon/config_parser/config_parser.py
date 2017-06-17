"""
Module to parse Xaphan daemon config
"""

import yaml


class ConfigParser(object):
    """
    Creates daemon configuration object
    """
    def __init__(self, c_path='/etc/xaphan.yaml'):
        try:
            with open(c_path) as c_file:
                config_arr = yaml.safe_load(c_file)
        except IOError:
            config_arr = self.__defaults()

        self.__config = config_arr

    def get(self):
        """
        Returns config object
        """
        return self.__config

    @staticmethod
    def __defaults():
        defaults = {
            'mysql':
                {
                    'host': '127.0.0.1',
                    'port': '3307',
                    'user': 'checker',
                    'pass': '',
                    'charset': 'utf8'
                },
            'daemon':
                {
                    'telnet': {
                        'ip': '0.0.0.0',
                        'port': '9980'
                    },
                    'api': {
                        'ip': '0.0.0.0',
                        'port': '9981'
                    }
                },
            'logger':
                {
                    'location': '/var/log',
                    'name': 'xaphan-daemon',
                    'rotation_time': '30'
                }
        }

        return defaults
