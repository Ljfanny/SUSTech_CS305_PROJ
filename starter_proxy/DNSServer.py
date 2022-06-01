import queue
import sys
import requests
from flask import Flask, Response, redirect
import argparse

ports_odd = queue.Queue()
ports_even = queue.Queue()
is_empty = False
app = Flask(__name__)
DEFAULT_SERVER_PATH = '10servers'
DEFAULT_PORT = 8877


# receive the request

@app.route('/dns')
def receive_req():
    port = route_robin()
    print(port)
    return port


def route_robin():
    global is_empty
    while True:
        if not ports_odd.empty() and not is_empty:
            prt = ports_odd.get()
            ports_even.put(prt)
            return prt
        elif not ports_even.empty():
            is_empty = True
            prt = ports_even.get()
            ports_odd.put(prt)
            return prt
        else:
            is_empty = False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="deal with args")
    parser.add_argument('-s', dest='server', type=str, default=DEFAULT_SERVER_PATH)
    parser.add_argument('-p', dest='port', type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    file_prefix = '/autograder/netsim/servers/'
    file_name = file_prefix + args.server
    port = args.port
    with open(file_name, 'r') as f:
        for line in f:
            ports_odd.put(line.strip("\n"))
    app.run('0.0.0.0', port=port)
