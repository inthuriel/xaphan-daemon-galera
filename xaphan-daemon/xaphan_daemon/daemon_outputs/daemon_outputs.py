"""
Module providing response formatters for daemon
"""

import json
from collections import OrderedDict


def haproxy_text_answer(health_percent, status, message):
    """
    Builds answer in hapoxy format
    """

    return '{health_percent}% {status} {message}\n'.format(health_percent=health_percent,
                                                           status=status.upper(),
                                                           message=message)


def api_json_answer(health_percent, status, message):
    """
    Builds answer in api way - json formatted
    """
    answer_data = OrderedDict()
    answer_data.setdefault('health_percent', health_percent)
    answer_data.setdefault('status', status)
    answer_data.setdefault('message', message)

    output = OrderedDict()
    output.setdefault('name', 'Xaphan Daemon')
    output.setdefault('endpoint', 'node status')
    output.setdefault('node_status', answer_data)

    return json.dumps(output)
