## Xaphan daemon. A Python Galera daemon for Haproxy
This is a simple daemon checking galera node state. <br>
Performed checks contains:
* check if UUID of cluster and node is the same
* check if node is connected to cluster
* check if node is ready for operations


Script can be configured by *YAML* file wich must be placed in **/etc/xaphan.yaml** (sample provided).
Script requires mysql user with proper permissions to perform checks (suggested permissions level is **USAGE**).
### Usage
start daemon:
```bash
./xaphandeamon.py start
```
stop daemon:
```bash
./xaphandeamon.py stop
```
### Daemon defaults
```python
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
         'critical_log': '/var/log/xaphan-daemon-critical.log', <br />
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
```