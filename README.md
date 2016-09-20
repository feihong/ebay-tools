# EBay Tools


## Installation

```
git clone https://github.com/feihong/ebay-tools
cd ebay-tools
mkvirtualenv -p python3.5 ebay
pip install -r requirements.txt
```

# Crontab entry

Generate a report every hour, on the hour, between 8 am and 10 pm.

```
0 13-23,0-3 * * * source ~/.virtualenvs/ebay/bin/activate && python ~/ebay-tools/check_orders.py --send-text
```
