import json
from pathlib import Path
from collections import OrderedDict, defaultdict

from invoke import task
import arrow

import config
import util
import template_util


@task
def download_orders(ctx):
    """
    Download orders awaiting shipment.
    """
    import orders
    orders_dir = Path(config.ORDERS_DIR)
    result = {}

    for user_id, cred in config.EBAY_CREDENTIALS:
        request = orders.OrderRequest(cred)
        result[user_id] = request.get_orders_detail()

    with (orders_dir / 'orders.json').open('w') as fp:
        json.dump(result, fp, indent=2)


@task
def generate_report(ctx):
    """
    Generate HTML report from downloaded orders data.
    """
    orders_dir = Path(config.ORDERS_DIR)
    orders_file = orders_dir / 'orders.json'
    if not orders_file.exists():
        print('File {} was not found'.format(orders_file))
        return

    with orders_file.open() as fp:
        orders_dict = json.load(fp)

    # Get map of models -> location.
    item_map = util.get_item_map()
    # Count the number of orders for each seller.
    seller_order_counts = OrderedDict()
    # Count the number of orders for each buyer.
    buyer_order_counts = defaultdict(int)

    for user_id, orders in orders_dict.items():
        orders.sort(key=lambda x: x['PaidTime'])
        seller_order_counts[user_id] = len(orders)
        for order in orders:
            buyer_id = order['BuyerUserID']
            buyer_order_counts[buyer_id] += 1

        util.render_to_file(
            orders_dir / (user_id + '.html'),
            'orders.plim',
            user_id=user_id,
            updated_time=util.local_now(),
            orders=orders,
            item_map=item_map,
            util=template_util)

    util.render_to_file(
        orders_dir / 'index.html',
        'index.plim',
        updated_time=util.local_now(),
        seller_order_counts=seller_order_counts,
        buyer_order_counts=buyer_order_counts)


@task
def combine_pdfs(ctx):
    import combine_pdfs
    combine_pdfs.download_and_combine(config.GDRIVE_FOLDER)


@task
def send_email(ctx):
    count = 0
    body = []

    for user_id, cred in config.EBAY_CREDENTIALS:
        request = OrderRequest(cred)
        orders = list(request.get_orders())
        line = '{user_id} has {count} orders awaiting shipment'.format(
            user_id=user_id, count=len(orders))
        body.append(line)
        print(line)
        count += len(orders)

    if count > 0:
        util.send_email(
            recipient=config.EMAIL_ADDRESS,
            subject='[{:HH:mm}] {} orders awaiting shipment'.format(
                util.local_now(), count),
            body='\n'.join(body),
        )


@task
def show_users(ctx):
    for user_id, cred in config.EBAY_CREDENTIALS:
        print(user_id)


@task
def web(ctx):
    pass
