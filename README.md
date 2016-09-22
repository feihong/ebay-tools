# EBay Tools


## Installation

```
git clone https://github.com/feihong/ebay-tools
cd ebay-tools
mkvirtualenv -p python3.5 ebay
pip install -r requirements.txt
```

# Crontab entry

Send an email reporting how many orders are awaiting shipping, every hour between 8 am and 10 pm.

```
0 13-23,0-3 * * * source ~/.virtualenvs/ebay/bin/activate && cd ebay-tools && inv send_email
```
