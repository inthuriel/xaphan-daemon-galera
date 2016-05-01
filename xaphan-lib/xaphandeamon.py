#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Galera daemon for Haproxy
This is a simple daemon checking galera node state.
Usage  ./xaphandeamon.py {start|stop|restart}
"""
import os
import sys
import re
import time
import SocketServer
import logging
import logging.handlers
import atexit
from signal import SIGTERM
import MySQLdb
import yaml
import psutil
reload(sys)
sys.path.insert(0, os.path.dirname(__file__))


class Daemon(object):
    """
    A generic daemon class.

    Usage: subclass the Daemon class and override the run() method
    """

    def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null',
                 stderr='/dev/null'):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile

    def daemonize(self):
        """
        do the UNIX double-fork magic, see Stevens' "Advanced
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """
        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                sys.exit(0)
        except OSError, e:
            sys.stderr.write(
                "fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # decouple from parent environment
        os.chdir("/")
        os.setsid()
        os.umask(0)

        # do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # exit from second parent
                sys.exit(0)
        except OSError, e:
            sys.stderr.write(
                "fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        se = file(self.stderr, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # write pidfile
        atexit.register(self.delpid)
        pid = str(os.getpid())
        file(self.pidfile, 'w+').write("%s\n" % pid)

    def delpid(self):
        """
        removes pidfile
        """
        os.remove(self.pidfile)

    def start(self):
        """
        Start the daemon
        """
        # Check for a pidfile to see if the daemon already runs
        try:
            pf = file(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if pid:
            message = "pidfile %s already exist. Daemon already running?\n"
            sys.stderr.write(message % self.pidfile)
            sys.exit(1)

        # Start the daemon
        self.daemonize()
        self.run()

    def stop(self):
        """
        Stop the daemon
        """
        # Get the pid from the pidfile
        try:
            pf = file(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if not pid:
            message = "pidfile %s does not exist. Daemon not running?\n"
            sys.stderr.write(message % self.pidfile)
            return  # not an error in a restart

        # Try killing the daemon process
        try:
            while 1:
                os.kill(pid, SIGTERM)
                time.sleep(0.1)
        except OSError, err:
            err = str(err)
            if err.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                print str(err)
                sys.exit(1)

    def restart(self):
        """
        Restart the daemon
        """
        self.stop()
        self.start()

    def run(self):
        """
        You should override this method when you subclass Daemon. It will be called after the process has been
        daemonized by start() or restart().
        """


class Config(object):
    """
    Create daemon configuration
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
        """
        Default values of config object
        """
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
                    'pid': '/tmp/xaphan-daemon.pid',
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


class LoggerMethod(object):
    """
    Logger class
    """
    def __init__(self, log_config):
        self.__config = log_config

    def setup_log(self):
        """
        Setups logger object for daemon logging
        """
        __log_location = self.__config['location']
        __logger = logging.getLogger(self.__config['name'])

        if len(__logger.handlers):
            return __logger
        else:
            logging.basicConfig(level=logging.DEBUG, filename=os.devnull)
            __logger = logging.getLogger(self.__config['name'])
            formatter = logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s', datefmt='%d-%m-%Y %H:%M:%S %z')

            file_handler = logging.handlers.TimedRotatingFileHandler(filename=__log_location, when='midnight', backupCount=int(self.__config['rotation_time']))
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.DEBUG)

            __logger.addHandler(file_handler)

            return __logger


class ServerRun(object):
    """
    Basic daemon server setup
    """
    def __init__(self, s_config):
        __logger_config = s_config['logger']
        __daemon_config = s_config['daemon']

        self.__config = s_config
        self.__logger = LoggerMethod(__logger_config).setup_log()

        self.__socket_host = __daemon_config['host']
        self.__socket_port = __daemon_config['port']

    def start_server(self):
        """
        Starts server on defined host and port to answer haproxy requests
        """
        try:
            server = SocketServer.TCPServer((self.__socket_host, int(self.__socket_port)), ReqHandler)
            server.wresp = WrespMysqlNodeCheck(self.__config)
            server.serve_forever()
            self.__logger.info('Server starts on %s:%s', self.__socket_host, self.__socket_port)
        except BaseException as exception:
            self.__logger.error('Server wont start on %s:%s with error: %s', self.__socket_host, self.__socket_port, exception)
            raise


class ReqHandler(SocketServer.BaseRequestHandler):
    """
    Class with handle method send to server
    This class handles requests and calls methods from other classes
    if request is held
    """
    def handle(self):
        """
        Basic server request method
        """
        answ = self.server.wresp.answer_me()
        self.request.sendall('{} \n'.format(answ))
        self.request.close()
        return


class WrespMysqlNodeCheck(object):
    """
    Check of WRESP cluster state
    """
    def __init__(self, s_config):
        __logger_config = s_config['logger']
        __mysql_config = s_config['mysql']
        log = LoggerMethod(__logger_config)

        self.__logger = log.setup_log()

        self.__db_user = __mysql_config['user']
        self.__db_pass = __mysql_config['pass']
        self.__db_host = __mysql_config['host']
        self.__db_port = int(__mysql_config['port'])
        self.__connection = None

    def answer_me(self):
        """
        Builds anwer for hapoxy to inform it if backend is down or not
        """
        checks = (
            ('is_ready', self.__ready_check()),
            ('is_synced', self.__sync_check()),
            ('is_provided', self.__provider_connected_check())
        )

        res = '0% DOWN no checks'
        check_err = re.compile(r'^status_err.*')

        for check in checks:
            if check[1] == 'ok':
                res = '100% UP'
            elif check[1] == 'sql_err':
                self.__logger.warning('%s is in state: %s', check[0], check[1])
                res = '0% DOWN {}'.format(check[1])
                break
            elif check_err.match(check[1]):
                self.__logger.warning('%s is in state: %s', check[0], check[1])
                res = '0% DOWN {}'.format(check[1])
                break

        if res == '0% DOWN no checks':
            self.__logger.warning('0% down no checks')

        return res

    def __sync_check(self):
        """
        Checks if UUID of cluster and node is the same
        """
        try:
            self.__sql_connect()
        except BaseException:
            return 'sql_err'

        cursor = self.__connection.cursor()
        cursor.execute("SHOW STATUS LIKE 'wsrep_cluster_state_uuid'")
        cluster_result = cursor.fetchone()
        cursor.execute("SHOW STATUS LIKE 'wsrep_local_state_uuid'")
        local_result = cursor.fetchone()
        self.__sql_disconnect()

        if cluster_result[1] == local_result[1]:
            answer = 'ok'
        else:
            answer = 'status_err'+self.__sync_check.__name__

        return answer

    def __provider_connected_check(self):
        """
        Check if node is connected to cluster
        """
        try:
            self.__sql_connect()
        except BaseException:
            return 'sql_err'

        cursor = self.__connection.cursor()
        cursor.execute("SHOW STATUS LIKE 'wsrep_connected';")
        result = cursor.fetchone()
        self.__sql_disconnect()

        if result[1] == 'ON':
            answer = 'ok'
        else:
            answer = 'status_err'+self.__provider_connected_check.__name__

        return answer

    def __ready_check(self):
        """
        Check if node is ready for operations
        """
        try:
            self.__sql_connect()
        except BaseException:
            return 'sql_err'

        cursor = self.__connection.cursor()
        cursor.execute("SHOW STATUS LIKE 'wsrep_ready';")
        result = cursor.fetchone()
        self.__sql_disconnect()

        if result[1] == 'ON':
            answer = 'ok'
        else:
            answer = 'status_err'+self.__ready_check.__name__

        return answer

    def __sql_connect(self):
        if self.__connection is not None and self.__connection.open:
            return

        try:
            database_conn = MySQLdb.connect(
                host=self.__db_host,
                user=self.__db_user,
                passwd=self.__db_pass,
                port=self.__db_port)
            self.__connection = database_conn
        except self.__connection.Error as err:
            self.__logger.error("Mysql error [%s]: %s", err[0], err[1])
            self.__connection = None
            raise

        return

    def __sql_disconnect(self):
        self.__connection.close()
        return


class XaphanDaemon(Daemon):
    """
    Daemon init class
    """
    def __init__(self, pidfile, s_config=None):
        self.__config = s_config
        self.stdin = '/dev/null'
        self.stdout = self.__config['daemon']['def_tty']
        self.stderr = self.__config['daemon']['critical_log']
        self.pidfile = pidfile
        super(XaphanDaemon, self).__init__(self.pidfile)

    def run(self):
        application = ServerRun(self.__config)
        application.start_server()

    @staticmethod
    def connections_on_port(port):
        """
        Counts open connections on given port
        """
        cnt = 0

        for connection in psutil.net_connections():
            laddr = connection[3]

            if laddr[1] == int(port):
                cnt += 1

        return cnt


class StartDaemon(object):
    """
    Class provides logic to execute start / stop statements of daemon
    """
    def __init__(self):
        self.__config = Config().get()
        self.__logger = LoggerMethod(self.__config['logger']).setup_log()
        self.__daemon = XaphanDaemon(self.__config['daemon']['pid'],
                                     s_config=self.__config)

    def execute(self, command):
        """
        Method executes start / stop / restart statements
        """
        if command not in ['start', 'stop', 'restart']:
            print "usage: {} start|stop|restart".format(command)
            self.__logger.info('Bad %s usage', command)
            sys.exit(2)

        if command == 'start':
            self.__daemon.start()
            self.__logger.info('Application has been started')

        elif command == 'stop':
            conn_info = {'port': self.__config['daemon']['port'],
                         'host': self.__config['daemon']['host']}
            self.__daemon.stop()

            if self.__daemon.connections_on_port(conn_info['port']) is not 0:
                self.__logger.info('Total connections on port %s is %s',
                                   conn_info['port'],
                                   self.__daemon.connections_on_port(
                                       conn_info['port']))
                last_time_connections_count = 0
                while self.__daemon.connections_on_port(conn_info['port']) is not 0:
                    connections_count = self.__daemon.connections_on_port(
                        conn_info['port'])
                    if last_time_connections_count != connections_count:
                        self.__logger.info(
                            'Number of connections on port %s is %s',
                            conn_info['port'],
                            self.__daemon.connections_on_port(
                                conn_info['port']))
                        print >> sys.stdout, \
                            'Closing {} remaining connections...'.format(
                                connections_count)
                        last_time_connections_count = connections_count
                    time.sleep(0.1)
                self.__logger.info('Application has been stopped')
                print >> sys.stdout, 'Application has been stopped.'
        elif command == 'restart':
            self.__daemon.restart()
            self.__logger.warning('Application has been restarted')
        sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) == 2:
        START_IT = StartDaemon()
        START_IT.execute(sys.argv[1])
    else:
        print "Unknown command. Usage: {} start|stop|restart".format(sys.argv[0])
        sys.exit(2)
