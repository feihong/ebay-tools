from pathlib import Path
from collections import OrderedDict
from invoke import task
import arrow

import config
import util
from check_orders import OrderRequest


@task
def generate_report(ctx):
    report_dir = Path(config.REPORT_DIR)
    user_ids = OrderedDict()
    location_map = util.get_location_map()

    for user_id, cred in config.EBAY_CREDENTIALS:
        request = OrderRequest(cred)
        orders = request.get_orders_detail()
        orders.sort(key=lambda x: x.PaidTime, reverse=True)
        user_ids[user_id] = len(orders)

        util.render_to_file(
            report_dir / (user_id + '.html'),
            'orders.plim',
            user_id=user_id,
            updated_time=util.local_now(),
            orders=orders,
            location_map=location_map)

    util.render_to_file(
        report_dir / 'index.html',
        'index.plim',
        updated_time=util.local_now(),
        user_ids=user_ids.items())

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
