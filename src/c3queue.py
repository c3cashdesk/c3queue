import csv
import datetime
import operator
import os
from collections import defaultdict

import aiohttp_jinja2
import aiofiles
import jinja2
import pygal
from aiohttp import web
from dateutil import parser


DATA_PATH = ''
C3SECRET = os.environ.get('C3QUEUE_SECRET')
LATEST = datetime.time(23, 59, 59)

CONGRESS_STYLE = pygal.style.DarkStyle
CONGRESS_STYLE.colors = ([
    '#01a89e',  # 33C3
    '#a10632',  # 34C3
    '#0084B0', '#00A357'  # 35C3
])


def truncate_time(t):
    return t.replace(second=0, microsecond=0)


def structure_data(data):
    result = defaultdict(lambda: defaultdict(list))
    for entry in data:
        ping = entry['ping'].date()
        entry['duration'] = round((entry['pong'] - entry['ping']).seconds / 60, 1)
        entry['ping'] = truncate_time(entry['ping'].time())
        result[ping.day]['{}C3'.format(ping.year - 1983)].append(entry)
        first_ping = result[ping.day]['first_ping']
        if not first_ping or first_ping > entry['ping']:
            result[ping.day]['first_ping'] = entry['ping']
    return result


@aiohttp_jinja2.template('stats.html')
async def stats(request):
    data = await parse_data()
    data = structure_data(data)
    charts = []
    for day_number, values in data.items():
        first_ping = values.pop('first_ping')
        all_x_values = sorted(list(set([y['ping'] for year in values for y in values[year]])))
        all_x_values = []
        full_values = {year: [] for year in values}
        value_keys = list(values.keys())
        while True:
            if not value_keys:
                break
            next_entry = min(value_keys, key=lambda x: values[x][0]['ping'] if values[x] else LATEST)
            next_ping = values[next_entry][0]['ping']
            all_x_values.append(next_ping)
            for year in value_keys:
                pings = values[year]
                if not pings:
                    continue
                if pings[0]['ping'] == next_ping:
                    full_values[year].append(pings.pop(0))
                else:
                    full_values[year].append({'duration': None})
                if not pings:
                    value_keys.remove(year)

        line_chart = pygal.Line(x_label_rotation=40, interpolate='cubic', title='Day {}'.format(day_number - 26), height=300, style=CONGRESS_STYLE)
        line_chart.x_labels = map(lambda d: d.strftime('%H:%M'), all_x_values)
        line_chart.value_formatter = lambda x:  '{} minutes'.format(x)
        for year, year_data in full_values.items():
            line_chart.add(year, [d['duration'] for d in year_data])
        charts.append(line_chart.render(is_unicode=True))
    return {'charts': charts}


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
    if not DATA_PATH:
        return
    async with aiofiles.open(DATA_PATH) as d:
        data = await d.read()
    return web.Response(text=data)


async def parse_data():
    result = []
    if not DATA_PATH:
        return result
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
    if not DATA_PATH:
        return
    async with aiofiles.open(DATA_PATH, 'a') as d:
        await d.write('{},{}\n'.format(ping.isoformat(), pong.isoformat()))


async def get_data_path():
    global DATA_PATH
    DATA_PATH = os.environ.get('C3QUEUE_DATA', os.path.join(os.path.dirname(__file__), 'c3queue.csv'))
    if not os.path.exists(DATA_PATH):
        try:
            with aiofiles.open(DATA_PATH, 'w') as d:
                d.write('ping,pong\n')
        except Exception as e:
            print(str(e))


async def main(argv=None):
    app = web.Application()
    app.add_routes([web.get('/', stats)])
    app.add_routes([web.post('/pong', pong)])
    app.add_routes([web.get('/data', data)])
    app.add_routes([web.static('/static', os.path.join(os.path.dirname(__file__), 'static'))])
    aiohttp_jinja2.setup(app, loader=jinja2.PackageLoader('c3queue', 'templates'))
    await get_data_path()
    return app
