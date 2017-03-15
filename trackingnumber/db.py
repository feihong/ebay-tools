import sqlite3


class Database:
    def __init__(self, orders):
        self.conn = sqlite3.connect(':memory:')

    def executescript(sql):
        cur = self.conn.cursor()
        cur.executescript(
        self.conn.commit()

    def select(sql, fields=(), *params):
        cur = conn.cursor()
        cur.execute(sql.format(fields=', '.join(fields)), params)
        def transform(row):
            if fields:
                return dict(zip(fields, row))
            else:
                return row
        return [transform(row) for row in cur.fetchall()]


    def execute(sql, fields, params):
        cur = conn.cursor()
        if isinstance(params, dict):
            params = operator.itemgetter(fields)(kwargs)
        cur.execute(sql.format(fields=', '.join(fields)), params)
        conn.commit()
