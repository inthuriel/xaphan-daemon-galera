"""
Module providing response formatters for daemon
"""

from .daemon_outputs import haproxy_text_answer, api_json_answer

__all__ = ['haproxy_text_answer', 'api_json_answer']
