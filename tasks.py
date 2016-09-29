from pathlib import Path
from collections import OrderedDict, defaultdict

from invoke import task
import arrow

import config
import util
from check_orders import OrderRequest


@task
def generate_report(ctx):
    report_dir = Path(config.REPORT_DIR)
    item_map = util.get_item_map()
    # Count the number of orders for each seller.
    seller_order_counts = OrderedDict()
    # Count the number of orders for each buyer.
    buyer_order_counts = defaultdict(int)

    for user_id, cred in config.EBAY_CREDENTIALS:
        request = OrderRequest(cred)
        orders = request.get_orders_detail()
        orders.sort(key=lambda x: x.PaidTime, reverse=True)

        seller_order_counts[user_id] = len(orders)
        for order in orders:
            buyer_order_counts[order.BuyerUserID] += 1

        util.render_to_file(
            report_dir / (user_id + '.html'),
            'orders.plim',
            user_id=user_id,
            updated_time=util.local_now(),
            orders=orders,
            item_map=item_map)

    util.render_to_file(
        report_dir / 'index.html',
        'index.plim',
        updated_time=util.local_now(),
        seller_order_counts=seller_order_counts,
        buyer_order_counts=buyer_order_counts)

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
