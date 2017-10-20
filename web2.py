from pathlib import Path
from collections import OrderedDict, defaultdict

from flask import Flask, redirect, send_from_directory, url_for
from mako.lookup import TemplateLookup
from plim import preprocessor

import util


lookup = TemplateLookup(
    directories=['static'],
    preprocessor=preprocessor,
    strict_undefined=True,
)


def render_template(template_file, **kwargs):
    tmpl = lookup.get_template(template_file)
    return tmpl.render(**kwargs)


app = Flask(__name__)


@app.route('/')
def home():
    import orders
    pkg = orders.load_orders('orders.json')

    # Count the number of orders for each seller.
    seller_order_counts = OrderedDict()
    # Dict of orders keyed by buyer ID.
    orders_by_buyer = defaultdict(list)

    for username, orders in pkg['payload'].items():
        orders.sort(key=lambda x: x['PaidTime'])
        seller_order_counts[username] = len(orders)

        for order in orders:
            buyer_id = order['BuyerUserID']
            orders_by_buyer[buyer_id].append(order)

    # Filter out buyers with less than 2 orders and convert to list of tuples.
    multi_buyers = [
        (buyer_id, orders, util.get_total_weight_of_orders(orders))
        for buyer_id, orders in orders_by_buyer.items()
        if len(orders) > 1
    ]

    return render_template(
        'orders/index.plim',
        download_time=pkg['download_time'],
        seller_order_counts=seller_order_counts,
        multi_buyers=multi_buyers)


@app.route('/orders/<user>/')
def orders_for_user(user):
    from orders import load_orders
    pkg = load_orders('orders.json')

    orders = None
    for user_, orders_ in pkg['payload'].items():
        if user == user_:
            orders = orders_
            break

    orders.sort(key=lambda x: x['PaidTime'])
    return render_template(
        'orders/by_user.plim',
        download_time=pkg['download_time'],
        user=user,
        orders=orders)


@app.route('/commands/download-awaiting/')
def download_orders_awaiting_shipment():
    import orders
    orders.download_orders_awaiting_shipment
    return 'ok'


@app.route('/commands/write-packing/')
def write_packing_info_to_labels():
    from packinginfo import PackingInfoWriter
    writer = PackingInfoWriter(
        label_count=label_count
    )
    writer.write_output_file()
    return 'ok'
