import re
import time

import requests
from flask import Flask, Response, redirect, request
import argparse
import logging
import json

DEFAULT_LOG_PATH = './proxy.log'
DEFAULT_ALPHA = 0.5
DEFAULT_LISTEN_PORT = 7779
DEFAULT_SERVER_PORT = '../docker_setup/ser'
DEFAULT_DNS_PORT = 8877
DEFAULT_PORT = 0
app = Flask(__name__)

alpha = 0
current_T = {}
bit_rates = []
video_damu = {}
begin_time = 0
zan = 0
comment = []
dns_port = DEFAULT_DNS_PORT
default_port = 15641


def arg_parse():
    parser = argparse.ArgumentParser(description="deal with args")
    parser.add_argument('-l', dest='log', type=str, default=DEFAULT_LOG_PATH)
    parser.add_argument('-a', dest='alpha', type=float, default=DEFAULT_ALPHA)
    parser.add_argument('-p', dest='listen', type=int,
                        default=DEFAULT_LISTEN_PORT)
    parser.add_argument('-d', dest='dns', type=int,
                        default=DEFAULT_DNS_PORT)
    parser.add_argument('-P', dest='default', type=int, default=DEFAULT_PORT)
    return parser.parse_args()


@app.route('/example')
def simple():
    return Response(requests.get('http://www.example.com'))


def modify_request(message):
    """
    Here you should change the requested bit rate according to your computation of throughput.
    And if the request is for big_buck_bunny.f4m, you should instead request big_buck_bunny_nolist.f4m 
    for client and leave big_buck_bunny.f4m for the use in proxy.
    """


def request_dns():
    """
    Request dns server here.
    """
    if default_port == 0:
        req = requests.get(f'http://127.0.0.1:{dns_port}/dns')
        print(req.text)
        port = int(req.text)
    else:
        port = default_port
    return port


def calculate_throughput(port, new: float):
    if port in current_T:
        current_T[port] = alpha * new + (1 - alpha) * current_T[port]
    else:
        current_T[port] = new
    return current_T[port]


def get_bitrate(port):
    bitrate = 0
    if port in current_T:
        throughput = current_T[port]
        for rate in bit_rates:
            if rate * 1.5 <= throughput:
                bitrate = rate
            else:
                break
    else:
        bitrate = 10
    return bitrate


def init_logger(file_name, log_name, verbose=1):
    level_dict = {0: logging.DEBUG, 1: logging.INFO, 2: logging.WARNING}
    formatter = logging.Formatter(
        "[%(asctime)s][%(filename)s][%(levelname)s] %(message)s"
    )
    formatter = logging.Formatter(
        "%(message)s"
    )
    logger = logging.getLogger(log_name)
    logger.setLevel(level_dict[verbose])

    fh = logging.FileHandler(file_name, 'w')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # sh = logging.StreamHandler()
    # sh.setFormatter(formatter)
    # logger.addHandler(sh)

    return logger


@app.route('/')
def get_main():
    port = request_dns()
    return Response(requests.get(f'http://127.0.0.1:{port}'))


@app.route('/<file>')
def get_file(file):
    port = request_dns()
    response = Response(requests.get(f'http://127.0.0.1:{port}/{file}'))
    return response


# --------------------------------------------
@app.route('/zan/', methods=["POST"])
def get_zan():
    global zan
    on = request.form['on']
    print(on)
    if on == "true":
        zan += 1
    else:
        zan -= 1
    return "ok"


@app.route('/zan_num/', methods=["GET"])
def send_zan():
    return str(zan)


@app.route('/comment/', methods=["POST"])
def get_comment():
    time = request.form['t']
    mes = request.form['m']
    comment.append(mes + "#" + time)
    return "ok"


@app.route('/comment_get/', methods=["GET"])
def send_comment():
    return '\n'.join(comment)


@app.route('/danmku/', methods=["POST"])
def get_danmu():

    time = request.form['t']
    mes = request.form['m']
    print("get", time, mes)
    try:
        video_damu[time]
    except:
        video_damu[time] = []
    video_damu[time].append(mes)
    return "ok"


@app.route('/refresh/', methods=["GET"])
def send_danmus():
    time = request.args.get('t')
    try:
        video_damu[time]
    except:
        video_damu[time] = []

    re = '\n'.join(video_damu[time])
    print(time, ":", re)

    return re

@app.route('/exit/', methods=["POST"])
def exit():
    app.close()
# --------------------------------------------

@app.route('/vod/<file>')
def dir_file(file):
    port = request_dns()
    bitrate = 0
    if 'f4m' in file:
        response = requests.get(f'http://127.0.0.1:{port}/vod/{file}')
        data = str(response.text)
        pattern = re.compile(r'bitrate="(?P<bitrate>\d+)"')
        global bit_rates
        bit_rates = pattern.findall(data)
        bit_rates = [int(x) for x in bit_rates]
        bit_rates = sorted(bit_rates)
        file = 'big_buck_bunny_nolist.f4m'
    if 'Seg' in file:
        bitrate = get_bitrate(port)
        file = str(bitrate) + file[file.find('Seg'):]
    logger = logging.getLogger('proxy')
    start = time.time()
    response = requests.get(f'http://127.0.0.1:{port}/vod/{file}')
    finish = time.time()
    global begin_time
    if 'Seg' in file:
        length = float(response.headers['Content-Length'])
        new = length / (finish - start)
        new /= 1024
        new = round(new, 8)
        current = calculate_throughput(port, new)
        current = round(current, 8)
        # logger.info(
        #     f'time:{int(start - begin_time)}s\t duration:{round(finish - start, 8)}\t tput:{new}\t avg-tput:{current}\t bitrate:{bitrate}\t server-port:{port}\t chunkname:{file[file.find("Seg"):]}\t')
        logger.info(f'{start} {finish - start} {new} {current} {bitrate} {port} {file[file.find("Seg"):]}')
    return Response(response)


def load():
    f = open('./data.json', 'r')
    f1 = open('./comment.json', 'r')
    f2 = open('./zan.json', 'r')
    global video_damu
    global zan
    global comment

    content = f.read()
    video_damu = json.loads(content)
    content1 = f1.read()
    comment = json.loads(content1)
    content2 = f2.read()
    zan = json.loads(content2)
    f.close()


def save():
    b = json.dumps(video_damu)
    f1 = open('data.json', 'w')
    f1.write(b)
    f1.close()
    b = json.dumps(comment)
    f1 = open('comment.json', 'w')
    f1.write(b)
    f1.close()
    b = json.dumps(zan)
    f1 = open('zan.json', 'w')
    f1.write(b)
    f1.close()


if __name__ == '__main__':
    try:
        load()
        begin_time = time.time()
        args = arg_parse()
        alpha = args.alpha
        listen_port = args.listen
        dns_port = args.dns
        default_port = args.default
        init_logger(args.log, 'proxy')
        app.run('0.0.0.0', port=listen_port)
    finally:
        save()
