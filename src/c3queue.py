import datetime
import os
from collections import defaultdict

import aiofiles
import aiohttp_jinja2
import jinja2
import pygal
from aiohttp import web
from dateutil import parser

DATA_PATH = ""
C3SECRET = os.environ.get("C3QUEUE_SECRET")
LATEST = datetime.time(23, 59, 59)
EVENTS = {
    "33C3": "#01a89e",
    "34C3": "#a10632",
    "35C3": "#00A357",
    "36C3": "#fe5000",
    "37C3": "#ffffff",
}


def get_event(year):
    if isinstance(year, str):
        year = int(year)
    if year < 2020:
        return f"{year - 1983}C3"
    return f"{year - 1986}C3"


def get_style(filtered_events):
    style = pygal.style.DarkStyle
    style.colors = [EVENTS[e] for e in filtered_events]
    return style


def truncate_time(t):
    return t.replace(second=0, microsecond=0)


def merge_pings(ping1, ping2):
    ping1["pong"] = None
    previous_merges = ping1.get("contains", 1)
    ping1["duration"] = round(
        ((ping1["duration"] * previous_merges) + ping2["duration"])
        / (previous_merges + 1),
        1,
    )
    ping1["contains"] = previous_merges + 1
    return ping1


def structure_data(data, filtered_events=None):
    result = defaultdict(lambda: defaultdict(list))
    years = set()
    for entry in data:
        ping = entry["ping"].date()
        key = get_event(ping.year)
        if filtered_events and key not in filtered_events:
            continue
        entry["duration"] = round((entry["pong"] - entry["ping"]).seconds / 60, 1)
        entry["ping"] = datetime.time(
            hour=entry["ping"].hour, minute=(entry["ping"].minute // 5) * 5
        )
        years.add(key)
        if result[ping.day][key] and result[ping.day][key][-1]["ping"] == entry["ping"]:
            result[ping.day][key][-1] = merge_pings(result[ping.day][key][-1], entry)
        else:
            result[ping.day][key].append(entry)
    entry["year"] = ping.year
    entry["day"] = ping.day
    entry["event"] = key
    return {
        "data": result,
        "last_ping": entry,
    }


@aiohttp_jinja2.template("stats.html")
async def stats(request):
    try:
        filtered_events = request.query.getall("events")
    except KeyError:
        filtered_events = list(EVENTS.keys())
    data = await parse_data()
    data = structure_data(data, filtered_events=filtered_events)
    charts = []
    for day_number in sorted(list(data["data"])):
        line_chart = pygal.TimeLine(
            x_label_rotation=40,
            # it's not grat, but it's the best interpolation we have
            interpolate="cubic",
            title="Day {}".format(day_number - 26),
            height=300,
            style=get_style(filtered_events),
            js=["/static/pygal-tooltips.min.js"],
        )
        line_chart.value_formatter = lambda x: "{} minutes".format(x)
        line_chart.x_value_formatter = lambda x: x.strftime("%H:%M")
        values = data["data"][day_number]
        for year in sorted(list(values)):
            line_chart.add(year, [(d["ping"], d["duration"]) for d in values[year]])
        charts.append(line_chart.render(is_unicode=True))

    # Hiding individual lines only works when there is a Line chart present on the page
    # yeah, I don't know either
    chart = pygal.Line(height=0, js=["/static/pygal-tooltips.min.js"], title="IGNORE")
    charts.append(chart.render(is_unicode=True))
    return {
        "charts": charts,
        "last_ping": data["last_ping"],
        "event": list(EVENTS.keys())[-1],
        "events": EVENTS,
        "filtered_events": filtered_events,
    }


async def pong(request):
    if (
        "Authorization" not in request.headers
        or request.headers["Authorization"] != C3SECRET
    ):
        return aiohttp_jinja2.render_template("405.html", request, {})
    try:
        data = await request.post()
    except Exception:
        return aiohttp_jinja2.render_template("405.html", request, {})
    if "ping" in data and "pong" in data:
        try:
            ping = parser.parse(data["ping"])
            pong = parser.parse(data["pong"])
        except Exception:
            return aiohttp_jinja2.render_template("405.html", request, {})
        else:
            await write_line(ping, pong)
            return web.Response(status=201)
    return aiohttp_jinja2.render_template("405.html", request, {"data": data})


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
            if row.strip() == "ping,pong":
                continue
            ping, pong = row.split(",")
            ping = parser.parse(ping.strip('"'))
            pong = parser.parse(pong.strip('"'))
            result.append({"ping": ping, "pong": pong})
    return result


async def write_line(ping, pong):
    if not DATA_PATH:
        return
    async with aiofiles.open(DATA_PATH, "a") as d:
        await d.write("{},{}\n".format(ping.isoformat(), pong.isoformat()))


async def get_data_path():
    global DATA_PATH
    DATA_PATH = os.environ.get(
        "C3QUEUE_DATA", os.path.join(os.path.dirname(__file__), "c3queue.csv")
    )
    if not os.path.exists(DATA_PATH):
        try:
            with aiofiles.open(DATA_PATH, "w") as d:
                d.write("ping,pong\n")
        except Exception as e:
            print(str(e))


async def main(argv=None):
    app = web.Application()
    app.add_routes([web.get("/", stats)])
    app.add_routes([web.post("/pong", pong)])
    app.add_routes([web.get("/data", data)])
    app.add_routes(
        [web.static("/static", os.path.join(os.path.dirname(__file__), "static"))]
    )
    aiohttp_jinja2.setup(app, loader=jinja2.PackageLoader("c3queue", "templates"))
    await get_data_path()
    return app
