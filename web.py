"""
To run:

muffin web run --bind=127.0.0.1:8000

"""
import asyncio

import muffin
from muffin_playground import Application

from logger import log, WebLogger


app = Application(client_debug=True)
app.task = None
app.sockets = set()
app.register_special_static_route(directory='static')


@app.register('/console/messages/')
async def status(request):
    resp = muffin.WebSocketResponse()
    await resp.prepare(request)
    app.sockets.add(resp)

    async for msg in resp: pass

    await resp.close()
    app.sockets.remove(resp)
    return resp


@app.register('/download-orders/')
async def download_orders(request):
    import orders
    await app.loop.run_in_executor(None, orders.download_orders)
    return 'ok'


@app.register('/orders/')
def orders(request):
    return app.render('static/orders/index.plim')


@app.on_startup.append
def on_startup(app):
    log.web_logger = WebLogger(app.loop, app.sockets)


@app.on_shutdown.append
async def on_shutdown(app):
    for socket in app.sockets:
        await socket.close()
