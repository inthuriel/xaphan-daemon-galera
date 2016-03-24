#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
import sys
import MySQLdb
import yaml
import os
import re
import SocketServer
import logging
import logging.handlers
import time
import psutil
from daemon import Daemon


class Config:
    """
    Create daemon configuration
    """
    def __init__(self, config='/etc/xaphan.yaml'):
        try:
            c_file = open(config)
            config_arr = yaml.safe_load(c_file)
            c_file.close()
        except (OSError, IOError) as e:
            config_arr = self._defaults()

        self._config = config_arr

    def get(self):
        return self._config

    @staticmethod
    def _defaults():
        arr = {
            'mysql':
                {
                    'host': '127.0.0.1',
                    'port': '3307',
                    'user': 'checker',
                    'pass': ''
                },
            'daemon':
                {
                    'pid': '/var/run/xaphan-daemon.pid',
                    'critical_log': '/var/log/xaphan-daemon-critical.log',
                    'def_tty': '/dev/tty0',
                    'host': '0.0.0.0',
                    'port': '9988'
                },
            'logger':
                {
                    'location': '/var/log/xaphan-daemon.log',
                    'name': 'xaphan-log',
                    'rotation_time': '30'
                }
        }
        return arr


class LoggerMethod:
    """
    Logger class
    """
    def __init__(self, log_config):
        self.logger = None
        self._config = log_config

    def setup_log(self):
        _log_location = self._config['location']
        self.logger = logging.getLogger(self._config['name'])

        if len(self.logger.handlers):
            return self.logger
        else:
            logging.basicConfig(level=logging.DEBUG, filename=os.devnull)
            self.logger = logging.getLogger(self._config['name'])
            formatter = logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s', datefmt='%d-%m-%Y %H:%M:%S %z')

            file_handler = logging.handlers.TimedRotatingFileHandler(filename=_log_location, when='midnight', backupCount=int(self._config['rotation_time']))
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.DEBUG)

            self.logger.addHandler(file_handler)

            return self.logger


class ServerRun(LoggerMethod):
    """
    Basic daemon server setup
    """
    def __init__(self, s_config):
        _logger_config = s_config['logger']
        _daemon_config = s_config['daemon']

        self._config = s_config
        self.logger = LoggerMethod(_logger_config).setup_log()

        self.socket_host = _daemon_config['host']
        self.socket_port = _daemon_config['port']

    def run(self):
        try:
            server = SocketServer.TCPServer((self.socket_host, int(self.socket_port)), ReqHandler)
            server.wresp = WrespMysqlNodeCheck(self._config)
            server.serve_forever()
            self.logger.info('Server starts on {0}:{1}'.format(self.socket_host, self.socket_port))
        except BaseException as e:
            msg = 'Server wont start on {0}:{1} with error: {2}'.format(self.socket_host, self.socket_port, e)
            self.logger.error(msg)
            raise BaseException(msg)


class ReqHandler(SocketServer.BaseRequestHandler):
    def handle(self):
        answ = self.server.wresp._answer_me()
        self.request.sendall('{} \n'.format(answ))
        self.request.close()
        return


class WrespMysqlNodeCheck(LoggerMethod):
    """
    Check of WRESP cluster state
    """
    def __init__(self, s_config):
        _logger_config = s_config['logger']
        _mysql_config = s_config['mysql']
        LoggerMethod.__init__(self, _logger_config)

        self.logger = self.setup_log()

        self.db_user = _mysql_config['user']
        self.db_pass = _mysql_config['pass']
        self.db_host = _mysql_config['host']
        self.db_port = int(_mysql_config['port'])
        self.connection = None

    def _answer_me(self):
        checks = [
            ['is_ready', self._ready_check()],
            ['is_synced', self._sync_check()],
            ['is_provided', self._provider_connected_check()]
        ]

        res = '0% DOWN no checks'
        check_err = re.compile('^status_err.*')

        for check in checks:
            if check[1] == 'ok':
                res = '100% UP'
            elif check[1] == 'sql_err':
                self.logger.warning("{0} is in state: {1}".format(check[0], check[1]))
                res = '0% DOWN {}'.format(check[1])
                break
            elif check_err.match(check[1]):
                self.logger.warning("{0} is in state: {1}".format(check[0], check[1]))
                res = '0% DOWN {}'.format(check[1])
                break

        if res == '0% DOWN no checks':
            self.logger.warning('0% down no checks')

        return res

    def _sync_check(self):
        """
        Checks if UUID of cluster and node is the same
        """
        try:
            self._sql_connect()
        except BaseException as e:
            return 'sql_err'

        cursor = self.connection.cursor()
        cursor.execute("SHOW STATUS LIKE 'wsrep_cluster_state_uuid'")
        cluster_result = cursor.fetchone()
        cursor.execute("SHOW STATUS LIKE 'wsrep_local_state_uuid'")
        local_result = cursor.fetchone()
        self._sql_disconnect()

        if cluster_result[1] == local_result[1]:
            answer = 'ok'
        else:
            answer = 'status_err'+self._sync_check.__name__

        return answer

    def _provider_connected_check(self):
        """
        Check if node is connected to cluster
        """
        try:
            self._sql_connect()
        except BaseException as e:
            return 'sql_err'

        cursor = self.connection.cursor()
        cursor.execute("SHOW STATUS LIKE 'wsrep_connected';")
        result = cursor.fetchone()
        self._sql_disconnect()

        if result[1] == 'ON':
            answer = 'ok'
        else:
            answer = 'status_err'+self._provider_connected_check.__name__

        return answer

    def _ready_check(self):
        """
        Check if node is ready for operations
        """
        try:
            self._sql_connect()
        except BaseException as e:
            return 'sql_err'

        cursor = self.connection.cursor()
        cursor.execute("SHOW STATUS LIKE 'wsrep_ready';")
        result = cursor.fetchone()
        self._sql_disconnect()

        if result[1] == 'ON':
            answer = 'ok'
        else:
            answer = 'status_err'+self._ready_check.__name__

        return answer

    def _sql_connect(self):
        if self.connection is not None and self.connection.open:
            return

        try:
            db = MySQLdb.connect(
                host=self.db_host,
                user=self.db_user,
                passwd=self.db_pass,
                port=self.db_port)
            self.connection = db
        except MySQLdb.Error as err:
            self.logger.error("Mysql error [{0}]: {1}".format(err[0], err[1]))
            self.connection = None
            raise

        return

    def _sql_disconnect(self):
        self.connection.close()
        return


class XaphanDaemon(Daemon):
    """
    Daemon init class
    """
    def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null', s_config=None):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile
        self._config = s_config

    def run(self):
        application = ServerRun(self._config)
        application.run()

    @staticmethod
    def connections_on_port(port):
        cnt = 0

        for connection in psutil.net_connections():
            laddr = connection[3]

            if laddr[1] == int(port):
                cnt += 1

        return cnt

if __name__ == "__main__":
    config = Config().get()
    logger = LoggerMethod(config['logger']).setup_log()
    daemon = XaphanDaemon(config['daemon']['pid'], stderr=config['daemon']['critical_log'], stdout=config['daemon']['def_tty'], s_config=config)

    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            try:
                daemon.start()
                logger.info('Application has been started')
            except BaseException as e:
                logger.error('Can\'t start application due to: {}'.format(e))
        elif 'stop' == sys.argv[1]:
            conn_info = {'port': config['daemon']['port'], 'host': config['daemon']['host']}
            daemon.stop()

            if daemon.connections_on_port(conn_info['port']) is not 0:
                logger.info('Total connections on port {} is {}'.format(conn_info['port'], daemon.connections_on_port(conn_info['port'])))
                l_cnt = 0
                while daemon.connections_on_port(conn_info['port']) is not 0:
                    c_cnt = daemon.connections_on_port(conn_info['port'])
                    logger.info('Number of connections on port {} is {}'.format(conn_info['port'], daemon.connections_on_port(conn_info['port'])))
                    if l_cnt != c_cnt:
                        sys.stdout.write('Closing {} remaining connections...\n'.format(c_cnt))
                        l_cnt = c_cnt
                    time.sleep(0.5)
                logger.info('Application has been stopped')
                sys.stdout.write('Application has been stopped.\n')
        elif 'restart' == sys.argv[1]:
            try:
                daemon.restart()
                logger.warning('Application has been restarted')
            except BaseException as e:
                logger.error('Can\'t restart application due to: {}'.format(e))
        else:
            print "Unknown command. Usage: {} start|stop|restart".format(sys.argv[0])
            logger.info('Bad script usage option: {}'.format(sys.argv[1]))
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: {} start|stop|restart".format(sys.argv[0])
        logger.info('Bad {} usage'.format(sys.argv[0]))
        sys.exit(2)