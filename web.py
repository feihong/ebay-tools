"""
To run:

muffin web run

"""
import muffin
from muffin_playground import Application


app = Application()
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
    # app.loop.run_in_executor()
    return 'ok'


@app.on_shutdown.append
async def on_shutdown(app):
    for socket in app.sockets:
        await socket.close()
