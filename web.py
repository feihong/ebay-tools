
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
import template_util
import config


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
    import orders
    pkg = orders.load_orders()

    # Count the number of orders for each seller.
    seller_order_counts = OrderedDict()
    # Count the number of orders for each buyer.
    buyer_order_counts = defaultdict(int)

    for user_id, orders in pkg['content'].items():
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
    pkg = orders.load_orders()
    user = request.match_info.get('user')

    # Get map of models -> location.
    item_map = util.get_item_map()

    for user_, orders in pkg['content'].items():
        if user == user_:
            orders.sort(key=lambda x: x['PaidTime'])
            break

    return app.render(
        'static/orders/by_user.plim',
        download_time=pkg['download_time'],
        user=user,
        orders=orders,
        item_map=item_map,
        util=template_util)


@app.on_startup.append
def on_startup(app):
    log.web_logger = WebLogger(app.loop, app.sockets)


@app.on_shutdown.append
async def on_shutdown(app):
    for socket in app.sockets:
        await socket.close()
