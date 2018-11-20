import csv
import os

import aiohttp_jinja2
import jinja2
from aiohttp import web
from dateutil import parser


DATA_PATH = ''


@aiohttp_jinja2.template('stats.html')
def stats(request):
    return {}


def pong(request):
    return aiohttp_jinja2.render_template('405.html', request, {})


def data(request):
    with open(DATA_PATH) as d:
        data = d.read()
    return web.Response(text=data)


def parse_data():
    result = []
    with open(DATA_PATH) as d:
        for row in csv.DictReader(d):
            ping = parser.parse(row['ping'])
            pong = parser.parse(row['pong'])
            result.append({'ping': ping, 'pong': pong, 'rtt': (pong - ping) if (ping and pong) else None})
    return result


def write_line(ping, pong):
    with open(DATA_PATH, 'a') as d:
        d.write('{},{}\n'.format(ping.isoformat(), pong.isoformat()))


def get_data_path():
    global DATA_PATH
    DATA_PATH = os.environ.get('C3QUEUE_DATA', './c3queue.csv')
    if not os.path.exists(DATA_PATH):
        with open(DATA_PATH, 'w') as d:
            d.write('ping,pong\n')


def main(argv):
    app = web.Application()
    app.add_routes([web.get('/', stats)])
    app.add_routes([web.get('/pong', pong)])
    app.add_routes([web.get('/data', data)])
    aiohttp_jinja2.setup(app, loader=jinja2.PackageLoader('c3queue', 'templates'))
    get_data_path()
    return app
