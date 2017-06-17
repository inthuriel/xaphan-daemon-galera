##Xaphan daemon. 

###A Python Galera daemon with telnet and api interface
This is a simple daemon checking galera node state. <br>
Performed checks contains:
* check if UUID of cluster and node is the same
* check if node is connected to cluster
* check if node is ready for operations

Package installation provides ***xaphan_galera_daemon*** *$PATH* endpoint in linux based systems.

#### How to install

```bash
git clone https://github.com/inthuriel/xaphan-daemon-galera.git
pip install -e ./xaphan-daemon-galera/xaphan-daemon/
```

#### Usage
```bash
[user ~]~ xaphan_galera_daemon --help
usage: xaphan_galera_daemon [-h] [-c CONFIG] [-t SERVER_TYPE]

Galera state daemon.

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        config file path
  -t SERVER_TYPE, --server_type SERVER_TYPE
                        type of server to run
```

All start parameters are optional. Sample of config files is provied in this repository.
Currently two types of servers are available:

##### telnet
```bash
[user ~]~ xaphan_galera_daemon -t telnet
```

Output:

```bash
[user ~]~ telnet 127.0.0.1 9980
Trying 127.0.0.1...
Connected to localhost.
Escape character is '^]'.
0% DOWN node_connection_check is in state: sql_err
Connection closed by foreign host.
```
Response is in **HAproxy** format.

##### api
```bash
[user ~]~ xaphan_galera_daemon -t api
```

Output:
```bash
[user ~]~ curl -XGET -s 'http://localhost:9981/' | python -mjson.tool
{
    "endpoint": "node status",
    "name": "Xaphan Daemon",
    "node_status": {
        "health_percent": 0,
        "message": "node_connection_check is in state: sql_err",
        "status": "down"
    }
}
```

### Daemon defaults
```python
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
```

### Setup suggestions

* Daemon can be run by ***supervisorctl*** configuration.
* Default telnet response is good to implement in *HAproxy* environments.
