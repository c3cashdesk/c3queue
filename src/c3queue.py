import csv
import os

import aiohttp_jinja2
import aiofiles
import jinja2
import pygal
from aiohttp import web
from dateutil import parser


DATA_PATH = ''
C3SECRET = os.environ.get('C3QUEUE_SECRET')


@aiohttp_jinja2.template('stats.html')
async def stats(request):
    data = await parse_data()
    max_duration = 0
    first_ping = data[0]['ping']
    for d in data:
        d['duration'] = round((d['pong'] - d['ping']).seconds / 60, 1)
    day_one_data = [d for d in data if d['ping'].day == 26]
    line_chart = pygal.Line(x_label_rotation=40, interpolate='cubic', show_legend=False, title='Waiting Time', height=300)
    line_chart.x_labels = map(lambda d: d.strftime('%H:%M'), [d['ping'] for d in day_one_data])
    line_chart.value_formatter = lambda x:  '{} minutes'.format(x)
    line_chart.add('Waiting time', [d['duration'] for d in day_one_data])
    return {'chart': line_chart.render(is_unicode=True)}


async def pong(request):
    if not 'Authorization' in request.headers or request.headers['Authorization'] != C3SECRET:
        return aiohttp_jinja2.render_template('405.html', request, {})
    try:
        data = await request.post()
    except:
        return aiohttp_jinja2.render_template('405.html', request, {})
    if 'ping' in data and 'pong' in data:
        try:
            ping = parser.parse(data['ping'])
            pong = parser.parse(data['pong'])
        except:
            return aiohttp_jinja2.render_template('405.html', request, {})
        else:
            await write_line(ping, pong)
            return web.Response(status=201)
    return aiohttp_jinja2.render_template('405.html', request, {'data': data})


async def data(request):
    async with aiofiles.open(DATA_PATH) as d:
        data = await d.read()
    return web.Response(text=data)


async def parse_data():
    result = []
    async with aiofiles.open(DATA_PATH) as d:
        async for row in d:
            if row.strip() == 'ping,pong':
                continue
            ping, pong = row.split(',')
            ping = parser.parse(ping.strip('"'))
            pong = parser.parse(pong.strip('"'))
            result.append({'ping': ping, 'pong': pong, 'rtt': (pong - ping) if (ping and pong) else None})
    return result


async def write_line(ping, pong):
    async with aiofiles.open(DATA_PATH, 'a') as d:
        await d.write('{},{}\n'.format(ping.isoformat(), pong.isoformat()))


async def get_data_path():
    global DATA_PATH
    DATA_PATH = os.environ.get('C3QUEUE_DATA', './c3queue.csv')
    if not os.path.exists(DATA_PATH):
        with aiofiles.open(DATA_PATH, 'w') as d:
            d.write('ping,pong\n')


async def main(argv):
    app = web.Application()
    app.add_routes([web.get('/', stats)])
    app.add_routes([web.post('/pong', pong)])
    app.add_routes([web.get('/data', data)])
    app.add_routes([web.static('/static', os.path.join(os.path.dirname(__file__), 'static'))])
    aiohttp_jinja2.setup(app, loader=jinja2.PackageLoader('c3queue', 'templates'))
    await get_data_path()
    return app
