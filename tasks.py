import json
from datetime import datetime
from pathlib import Path
from collections import OrderedDict, defaultdict
import subprocess

from invoke import task
import arrow

import config
import util
from misc_tasks import *


def run(cmd):
    subprocess.call(cmd, shell=True)


@task
def download_orders_awaiting_shipment(ctx):
    """
    Download orders awaiting shipment.

    """
    import orders
    orders.download_orders_awaiting_shipment()


@task
def download_shipped_orders(ctx):
    """
    Download orders that have been marked as shipped.

    """
    import orders
    orders.download_shipped_orders()


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
            orders=orders)

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
def combine_pdfs_for_print(ctx):
    """
    Download PDFs from "Shipping Label Inbox" GDrive folder and combine them
    into a single PDF file, with 2 labels per page.

    """
    import combine_pdfs
    combine_pdfs.combine_for_print(config.GDRIVE_FOLDER)


@task
def crop_shipping_label(ctx, pdf_file):
    """
    Crop a shipping label PDF so that the order details are no longer visible.
    """
    from shipping_label import crop_shipping_label
    crop_shipping_label(pdf_file)


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
def rebuild_item_model_csv(ctx):
    """
    Rebuild the item_model.csv file

    """
    import items
    items.rebuild_item_model_csv('item_model.csv')


@task
def download_item_shipping_data(ctx):
    """
    Download item's shipping data to item_shipping.csv.

    """
    import items
    items.download_item_shipping_data('item_shipping.csv')


@task
def show_users(ctx):
    """
    Show all users from the config file.

    """
    for user_id, cred in config.EBAY_CREDENTIALS:
        print(user_id)


@task
def generate_simple_orders_file(ctx):
    from trackingnumber import mapper
    mapper.generate_simple_orders_file()


@task
def print_tracking_numbers(ctx):
    """
    Print all tracking numbers from shipping label PDFs in current directory.

    """
    from trackingnumber.extractor import TrackingNumberExtractor
    extractor = TrackingNumberExtractor('.')
    tracking_numbers = extractor.get_tracking_numbers()
    for i, tn_list in enumerate(tracking_numbers, 1):
        print('Page {}:'.format(i))
        for tn in tn_list:
            print('- {}'.format(tn))


@task
def write_packing_info_to_labels(ctx, skip_download=False,
                                      label_count=None):
    """
    Read all shipping label PDFs in current directory and output a consolidated
    shipping label PDF that contains packing information.

    """
    if not skip_download:
        import orders
        orders.download_shipped_orders()

    # from trackingnumber import mapper
    # mapper.generate_simple_orders_file()

    from packinginfo import PackingInfoWriter
    writer = PackingInfoWriter(
        label_count=label_count,
        # simple_orders_file='orders/shipped_orders_simple.json'
    )
    # writer.write_output_file('test+packing.pdf')
    writer.write_output_file()


@task
def download_item_location_csv(ctx):
    """
    Download the latest versions of item_location.csv and item_model.csv from
    Google Drive.

    """
    import gsheet
    gsheet.download_item_location_csv()


@task
def web(ctx):
    """
    Run the web app.

    """
    # run('muffin web run --bind=127.0.0.1:8000')
    from web2 import app
    app.run(port=8000, debug=True)
