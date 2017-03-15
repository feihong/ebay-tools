import sqlite3
import operator


class Database:
    def __init__(self):
        self.conn = sqlite3.connect(':memory:')

    def executescript(self, sql):
        cur = self.conn.cursor()
        cur.executescript(sql)
        self.conn.commit()

    def select(self, sql, fields=(), *params):
        cur = self.conn.cursor()
        cur.execute(sql.format(fields=', '.join(fields)), params)
        def transform(row):
            if fields:
                return dict(zip(fields, row))
            else:
                return row
        return [transform(row) for row in cur.fetchall()]

    def execute(self, sql, fields, params):
        cur = self.conn.cursor()
        if isinstance(params, dict):
            params = operator.itemgetter(*fields)(params)
        cur.execute(sql.format(fields=', '.join(fields)), params)
        self.conn.commit()
