
"""
To run:

muffin web run --bind=127.0.0.1:8000

"""
import asyncio
from collections import OrderedDict, defaultdict

import muffin
from muffin_playground import Application

from logger import log, WebLogger
import util
import config


app = Application(client_debug=False)
app.future = None      # only allow one command at a time to run.
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
    future = run_command(orders.download_orders_awaiting_shipment)
    if future:
        await future
        return 'ok'
    else:
        return 'busy'


@app.register('/orders/')
def orders(request):
    import orders
    pkg = orders.load_orders('orders.json')

    # Count the number of orders for each seller.
    seller_order_counts = OrderedDict()
    # Count the number of orders for each buyer.
    buyer_order_counts = defaultdict(int)

    for user_id, orders in pkg['payload'].items():
        orders.sort(key=lambda x: x['PaidTime'])
        seller_order_counts[user_id] = len(orders)
        for order in orders:
            buyer_id = order['BuyerUserID']
            buyer_order_counts[buyer_id] += 1

    return app.render(
        'static/orders/index.plim',
        download_time=pkg['download_time'],
        seller_order_counts=seller_order_counts,
        buyer_order_counts=buyer_order_counts)


@app.register('/orders/{user}/')
def orders_for_user(request):
    import orders
    pkg = orders.load_orders('orders.json')
    user = request.match_info.get('user')

    for user_, orders in pkg['payload'].items():
        if user == user_:
            orders.sort(key=lambda x: x['PaidTime'])
            break

    return app.render(
        'static/orders/by_user.plim',
        download_time=pkg['download_time'],
        user=user,
        orders=orders)


@app.on_startup.append
def on_startup(app):
    log.web_logger = WebLogger(app.loop, app.sockets)


@app.on_shutdown.append
async def on_shutdown(app):
    for socket in app.sockets:
        await socket.close()


def run_command(func):
    """
    Run a command if no other command is currently running.

    """
    if app.future is None:
        future = app.loop.run_in_executor(None, func)

        def on_done(future):
            app.future = None
        future.add_done_callback(on_done)

        app.future = future
        return future
    else:
        return None
