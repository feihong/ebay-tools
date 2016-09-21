from pathlib import Path

from invoke import task
import arrow

import config
import util
from check_orders import OrderRequest


@task
def generate_report(ctx, send_text=False):
    report_dir = Path(config.REPORT_DIR)
    user_ids = [p[0] for p in config.EBAY_CREDENTIALS]
    util.render_to_file(report_dir / 'index.html', 'index.plim', user_ids=user_ids)

    for user_id, cred in config.EBAY_CREDENTIALS:
        request = OrderRequest(cred)
        orders = request.get_orders_detail()
        orders.sort(key=lambda x: x.PaidTime, reverse=True)

        util.render_to_file(
            report_dir / (user_id + '.html'),
            'orders.plim',
            user_id=user_id,
            updated_time=util.local_now(),
            orders=orders)


@task
def send_email(ctx):
    body = []

    for user_id, cred in config.EBAY_CREDENTIALS:
        request = OrderRequest(cred)
        orders = list(request.get_orders())
        line = '{user_id} has {count} orders awaiting shipment'.format(
            user_id=user_id, count=len(orders))
        body.append(line)

    util.send_email(
        recipient=config.EMAIL_ADDRESS,
        subject='Orders awaiting shipment - {:HH:mm}'.format(util.local_now()),
        body='\n'.join(body),
    )
