import json
from pathlib import Path
from collections import OrderedDict, defaultdict

from invoke import task, run
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
    orders.download_orders()


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
        download = json.load(fp)
        download_time = arrow.get(download['download_time']).to(config.TIME_ZONE)

    # Get map of models -> location.
    item_map = util.get_item_map()
    # Count the number of orders for each seller.
    seller_order_counts = OrderedDict()
    # Count the number of orders for each buyer.
    buyer_order_counts = defaultdict(int)

    for user_id, orders in download['content'].items():
        orders.sort(key=lambda x: x['PaidTime'])
        seller_order_counts[user_id] = len(orders)
        for order in orders:
            buyer_id = order['BuyerUserID']
            buyer_order_counts[buyer_id] += 1

        util.render_to_file(
            orders_dir / (user_id + '.html'),
            'orders.plim',
            user_id=user_id,
            download_time=download_time,
            orders=orders,
            item_map=item_map,
            util=template_util)

    util.render_to_file(
        orders_dir / 'index.html',
        'index.plim',
        download_time=download_time,
        seller_order_counts=seller_order_counts,
        buyer_order_counts=buyer_order_counts)


@task
def combine_pdfs(ctx):
    """
    Download PDFs from "Shipping Label Inbox" GDrive folder and concatenate them
    into a single PDF file.

    """
    import combine_pdfs
    combine_pdfs.download_and_combine(config.GDRIVE_FOLDER)


@task
def send_email(ctx):
    """
    Send an email notifying you of the number of orders awaiting shipment.

    """
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
def process_return_label(ctx, pdf_file):
    """
    Strip all unecessary data from return shipping label.

    """
    import shipping_label
    shipping_label.process_return_label(pdf_file)


@task
def show_users(ctx):
    """
    Show all users from the config file.

    """
    for user_id, cred in config.EBAY_CREDENTIALS:
        print(user_id)


@task
def web(ctx):
    """
    Run the web app.

    """
    run('muffin web run --bind=127.0.0.1:8000')
