import os

import aiohttp_jinja2
import jinja2
from aiohttp import web


@aiohttp_jinja2.template('stats.html')
def stats(request):
    return {}


def pong(request):
    return aiohttp_jinja2.render_template('405.html', request, {})


def main(argv):
    app = web.Application()
    app.add_routes([web.get('/', stats)])
    app.add_routes([web.get('/pong', pong)])
    aiohttp_jinja2.setup(app, loader=jinja2.PackageLoader('c3queue', 'templates'))
    return app
