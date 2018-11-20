import csv
import os

import aiohttp_jinja2
import aiofiles
import jinja2
from aiohttp import web
from dateutil import parser


DATA_PATH = ''


@aiohttp_jinja2.template('stats.html')
async def stats(request):
    data = await parse_data()
    return {'data': data}


def pong(request):
    return aiohttp_jinja2.render_template('405.html', request, {})


async def data(request):
    async with aiofiles.open(DATA_PATH) as d:
        data = await d.read()
    return web.Response(text=data)


async def parse_data():
    result = []
    async with aiofiles.open(DATA_PATH) as d:
        async for row in csv.DictReader(d):
            ping = parser.parse(row['ping'])
            pong = parser.parse(row['pong'])
            result.append({'ping': ping, 'pong': pong, 'rtt': (pong - ping) if (ping and pong) else None})
    return result


async def write_line(ping, pong):
    async with open(DATA_PATH, 'a') as d:
        d.write('{},{}\n'.format(ping.isoformat(), pong.isoformat()))


async def get_data_path():
    global DATA_PATH
    DATA_PATH = os.environ.get('C3QUEUE_DATA', './c3queue.csv')
    if not os.path.exists(DATA_PATH):
        with aiofiles.open(DATA_PATH, 'w') as d:
            d.write('ping,pong\n')


async def main(argv):
    app = web.Application()
    app.add_routes([web.get('/', stats)])
    app.add_routes([web.get('/pong', pong)])
    app.add_routes([web.get('/data', data)])
    aiohttp_jinja2.setup(app, loader=jinja2.PackageLoader('c3queue', 'templates'))
    await get_data_path()
    return app
