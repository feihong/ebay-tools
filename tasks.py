from pathlib import Path

from invoke import task
import arrow

import config
from util import render_to_file
from check_orders import OrderRequest


@task
def generate_report(ctx, send_text=False):
    report_dir = Path(config.REPORT_DIR)
    user_ids = [p[0] for p in config.EBAY_CREDENTIALS]
    render_to_file(report_dir / 'index.html', 'index.plim', user_ids=user_ids)

    for user_id, cred in config.EBAY_CREDENTIALS:
        request = OrderRequest(cred)
        orders = request.get_orders_detail()
        orders.sort(key=lambda x: x.PaidTime, reverse=True)

        render_to_file(
            report_dir / (user_id + '.html'),
            'orders.plim',
            user_id=user_id,
            updated_time=arrow.utcnow().to(config.TIME_ZONE),
            orders=orders)
