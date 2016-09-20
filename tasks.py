from pathlib import Path

from invoke import task
import arrow

import config
from util import render_to_file
import check_orders


@task
def generate_report(ctx, send_text=False):
    report_dir = Path(config.REPORT_DIR)
    user_ids = [p[0] for p in config.EBAY_CREDENTIALS]
    render_to_file(report_dir / 'index.html', 'index.plim', user_ids=user_ids)

    for user_id, cred in config.EBAY_CREDENTIALS:
        orders = list(check_orders.get_orders(cred))
        orders.sort(key=lambda x: x.PaidTime)

        render_to_file(
            report_dir / (user_id + '.html'),
            'orders.plim',
            user_id=user_id,
            updated_time=arrow.utcnow().to(config.TIME_ZONE),
            orders=orders,
            get_items=check_orders.get_items,
            get_address=check_orders.get_address)
