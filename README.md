<h1>Xaphan daemon. A Python Galera deemon for Haproxy</h1>
<p>This is a simple daemon checking galera node state. <br />
Performed checks contains:
<ol>
<li>check if UUID of cluster and node is the same</li>
<li>check if node is connected to cluster</li>
<li>check if node is ready for operations</li>
</ol>
</p>
<p>Script can be configured by <em>YAML</em> file wich must be placed in <bold>/etc/xaphan.yaml</bold> (sample provided).</p>
<p>Script requires mysql user with proper permissions to perform checks (suggested permissions level is <bold>USAGE</bold>).</p>
<h2>Usage</h2>
<p>start daemon: </p>
<code> ./xaphandeamon.py start </code>
<p>stop daemon: </p>
<code> ./xaphandeamon.py stop </code>
<h2>Daemon defaults</h2>
<code>
            'mysql': <br />
                { <br />
                    'host': '127.0.0.1', <br />
                    'port': '3307', <br />
                    'user': 'checker', <br />
                    'pass': '' <br />
                }, <br />
            'daemon': <br />
                { <br />
                    'pid': '/var/run/xaphan-daemon.pid', <br />
                    'critical_log': '/var/log/xaphan-daemon-critical.log', <br />
                    'def_tty': '/dev/tty0', <br />
                    'host': '0.0.0.0', <br />
                    'port': '9988' <br />
                }, <br />
            'logger': <br />
                { <br />
                    'location': '/var/log/xaphan-daemon.log', <br />
                    'name': 'xaphan-log', <br />
                    'rotation_time': '30' <br />
                } <br />
</code>