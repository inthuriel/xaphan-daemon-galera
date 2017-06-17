"""
Module providing Galera state tests for daemon
"""

import logging

import MySQLdb
from _mysql_exceptions import OperationalError

from ..daemon_logging import LoggingMethod


class GaleraNodeOperationTests(object):
    """
    Check of WSREP cluster state
    """
    def __init__(self, config):
        __mysql_config = config['mysql']

        LoggingMethod(config).setup_log()

        self.__mysql_connection_data = {
            'host': __mysql_config.get('host', 'localhost'),
            'user': __mysql_config.get('user', 'root'),
            'passwd': __mysql_config.get('pass', ''),
            'port': int(__mysql_config.get('port', 3306)),
            'charset':__mysql_config.get('charset', 'utf8')
        }

        self.checks_list = [func for func in dir(GaleraNodeOperationTests)
                            if callable(getattr(GaleraNodeOperationTests, func))
                            and not func.startswith("__")]

    def node_uuid_sync_check(self):
        """
        Checks if UUID of cluster and node is the same
        """
        try:
            __connection = MySQLdb.connect(**self.__mysql_connection_data)
        except OperationalError as err:
            logging.error("Mysql connection error: %s", err)
            return 'sql_err'

        __cursor = __connection.cursor(MySQLdb.cursors.DictCursor)
        __connection.autocommit(False)
        try:
            __cursor.execute("SHOW STATUS LIKE 'wsrep_cluster_state_uuid'")
            cluster_result = __cursor.fetchone()
            __cursor.execute("SHOW STATUS LIKE 'wsrep_local_state_uuid'")
            local_result = __cursor.fetchone()
            __connection.commit()
        except BaseException as err:
            __connection.rollback()
            logging.error("Something goes wrong, connection rollback: %s", err)
            return 'sql_err'
        finally:
            __connection.close()

        if cluster_result['Value'] == local_result['Value']:
            answer = 'ok'
        else:
            answer = 'status_err'+self.node_uuid_sync_check.__name__

        return answer

    def node_connection_check(self):
        """
        Check if node is connected to cluster
        """
        try:
            __connection = MySQLdb.connect(**self.__mysql_connection_data)
        except OperationalError as err:
            logging.error("Mysql connection error: %s", err)
            return 'sql_err'

        __cursor = __connection.cursor(MySQLdb.cursors.DictCursor)
        __connection.autocommit(False)

        try:
            __cursor.execute("SHOW STATUS LIKE 'wsrep_connected';")
            result = __cursor.fetchone()
        except BaseException as err:
            __connection.rollback()
            logging.error("Something goes wrong, connection rollback: %s", err)
            return 'sql_err'
        finally:
            __connection.close()

        if result['Value'] == 'ON':
            answer = 'ok'
        else:
            answer = 'status_err'+self.node_connection_check.__name__

        return answer

    def node_transaction_ready_check(self):
        """
        Check if node is ready for operations
        """
        try:
            __connection = MySQLdb.connect(**self.__mysql_connection_data)
        except OperationalError as err:
            logging.error("Mysql connection error: %s", err)
            return 'sql_err'

        __cursor = __connection.cursor(MySQLdb.cursors.DictCursor)
        __connection.autocommit(False)

        try:
            __cursor.execute("SHOW STATUS LIKE 'wsrep_ready';")
            result = __cursor.fetchone()
        except BaseException as err:
            __connection.rollback()
            logging.error("Something goes wrong, connection rollback: %s", err)
            return 'sql_err'
        finally:
            __connection.close()

        if result['Value'] == 'ON':
            answer = 'ok'
        else:
            answer = 'status_err'+self.node_transaction_ready_check.__name__

        return answer
