#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Galera node state daemon
This is a simple daemon checking Galera node state.
"""

from __future__ import print_function

import argparse
import json
import logging
import re

from gevent.server import StreamServer
from gevent.wsgi import WSGIServer
from xaphan_daemon.config_parser import ConfigParser
from xaphan_daemon.daemon_logging import LoggingMethod
from xaphan_daemon.daemon_outputs import haproxy_text_answer, api_json_answer
from xaphan_daemon.galera_tests import GaleraNodeOperationTests

CONFIG = None


def xaphan_daemon(config):
    """
    Runs Galera checks
    :param config: configuration object
    :return: Galera node state object
    """
    __galera_tests = GaleraNodeOperationTests(config)
    response = {
        'health_percent': 0,
        'status': 'down',
        'message': 'lack of tests'
    }

    check_err = re.compile(r'^status_err.*')

    for check in __galera_tests.checks_list:
        effect = getattr(__galera_tests, check)()
        if effect == 'ok':
            response['health_percent'] = 100
            response['status'] = 'up'
            response['message'] = 'ok'
        elif effect == 'sql_err':
            logging.warning('%s is in state: %s', check, effect)
            response['health_percent'] = 0
            response['status'] = 'down'
            response['message'] = '{} is in state: {}'.format(check, effect)
            break
        elif check_err.match(effect):
            logging.warning('%s is in state: %s', check, effect)
            response['health_percent'] = 0
            response['status'] = 'down'
            response['message'] = '{} is in state: {}'.format(check, effect)
            break

    if response['message'] == 'lack of tests':
        logging.warning('0% down lack of tests')

    return response


def telnet_handler(socket, address):
    """
    Handler for socket communication
    :param address: telnet connection params
    :param socket: telnet socket
    """

    logging.debug('Connection on adress %s', address)
    node_status = xaphan_daemon(CONFIG)
    socket.send(haproxy_text_answer(**node_status))
    socket.close()


def wsgi_handler(env, start_response):
    """
    Handler for WSGI communication
    :param env: request variables
    :param start_response: response object
    :return:
    """

    if env['REQUEST_METHOD'] != 'GET':
        status = '400 Bad Request'
        response_body = json.dumps({'error': 'Bad Request'})
    else:
        if env.get('PATH_INFO', '') == '/':
            node_status = xaphan_daemon(CONFIG)
            response_body = api_json_answer(**node_status)

            if node_status.get('status') == 'down':
                status = '503 Service Unavailable'
            else:
                status = '200 OK'
        else:
            status = '404 Not found'
            response_body = json.dumps({'error': 'Route not found'})

    response_headers = [
        ('Content-Type', 'application/json'),
        ('Content-Length', str(len(response_body)))
    ]

    start_response(status, response_headers)

    return [response_body]


def daemon_establish():
    """
    Base class to establish daemon with parsed init params
    :return: working daemon
    """

    parser = argparse.ArgumentParser(description='Galera state daemon.')
    parser.add_argument('-c', '--config', help='config file path', type=str,
                        default='/etc/xaphan.yaml')
    parser.add_argument('-t', '--server_type', help='type of server to run', type=str,
                        default='telnet')

    args = parser.parse_args()

    global CONFIG
    CONFIG = ConfigParser(args.config).get()
    LoggingMethod(CONFIG).setup_log()

    if CONFIG.setdefault('daemon', {}).get(args.server_type):
        if args.server_type == 'telnet':
            connection_data = CONFIG.setdefault('daemon', {}).get(args.server_type)
            server = StreamServer((connection_data.get('ip'), int(connection_data.get('port'))),
                                  telnet_handler)
            server.serve_forever()
        elif args.server_type == 'api':
            connection_data = CONFIG.setdefault('daemon', {}).get(args.server_type)
            server = WSGIServer((connection_data.get('ip'), int(connection_data.get('port'))),
                                wsgi_handler)
            server.serve_forever()
        else:
            print('{} is wrong server type'.format(args.server_type))
            exit(1)
    else:
        print('{} is wrong server type'.format(args.server_type))
        exit(1)

if __name__ == "__main__":
    daemon_establish()
