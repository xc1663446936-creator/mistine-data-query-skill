import importlib.util
import pathlib
import sqlite3
import tempfile
import types
import unittest


SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "skills/mistine-data-query/scripts/shop_order_query.py"
spec = importlib.util.spec_from_file_location("order_query", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class OrderQueryTests(unittest.TestCase):
    def make_db(self, path):
        connection = sqlite3.connect(path)
        connection.executescript("""
            CREATE TABLE import_runs(run_id INTEGER, started_at TEXT, finished_at TEXT, command TEXT, status TEXT, error_count INTEGER);
            INSERT INTO import_runs VALUES(1,'2026-09-29 09:00:00','2026-09-29 09:01:00','test','SUCCESS',0);
            CREATE TABLE orders(pay_time TEXT);
            INSERT INTO orders VALUES('2026-09-28 12:00:00');
            CREATE TABLE items(shop_name TEXT,order_id TEXT,pay_time TEXT,project_scope TEXT,sale_channel TEXT,account_nickname TEXT,
                product_id TEXT,sku_code TEXT,gmv REAL,refund_amount REAL,gsv REAL,quantity INTEGER,aftersale_reason TEXT);
            CREATE VIEW v_order_item_metrics AS SELECT *, substr(pay_time,1,10) AS pay_date, substr(pay_time,1,7) AS pay_month,
                '' AS product_code,'' AS product_name,'' AS platform_sku_id,'' AS product_attributes FROM items;
            INSERT INTO items VALUES('底彩店','o1','2026-09-28 12:00:00','自播','关联账号','直播间A','p1','s1',100,10,90,1,'原因A');
            INSERT INTO items VALUES('底彩店','o1','2026-09-28 12:00:00','自播','关联账号','直播间A','p2','s2',50,0,50,2,'');
            INSERT INTO items VALUES('防晒店','o1','2026-09-28 12:00:00','达播','机构推广','达人B','p3','s3',200,50,150,1,'原因B');
            INSERT INTO items VALUES('底彩店','o2','2026-09-28 12:00:00','自播','自然成交','','p1','s1',50,0,50,1,'');
        """)
        connection.close()

    def args(self, path, **kwargs):
        defaults = dict(command="query", db_path=str(path), date="2026-09-28", start=None, end=None,
                        scope="全部", grain="summary", shop=None, channel=None, product_id=None,
                        sku_code=None, account=None, sort="gmv", limit=100, expected_min_run=0)
        defaults.update(kwargs)
        return types.SimpleNamespace(**defaults)

    def test_cross_shop_order_identity_and_amounts(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "orders.sqlite3"
            self.make_db(path)
            result = module.local_run(self.args(path), "local_primary")
            data = result["data"][0]
            self.assertEqual((data["gmv"], data["refund_amount"], data["gsv"]), (400, 60, 340))
            self.assertEqual(data["order_count"], 3)  # o1 in two shops is two orders; two items in one is one.
            self.assertEqual(data["item_count"], 4)
            self.assertEqual(data["sales_quantity"], 5)
            self.assertEqual(data["refund_rate"], 0.15)

    def test_scope_and_channel_filters(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "orders.sqlite3"
            self.make_db(path)
            self.assertEqual(module.local_run(self.args(path, scope="自播"), "local_primary")["data"][0]["gmv"], 200)
            self.assertEqual(module.local_run(self.args(path, scope="达播"), "local_primary")["data"][0]["gmv"], 200)
            with self.assertRaisesRegex(ValueError, "冲突"):
                module.local_run(self.args(path, scope="自播", channel="机构推广"), "local_primary")

    def test_read_only_and_failed_batch_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "orders.sqlite3"
            self.make_db(path)
            connection = module.connect_ro(path)
            with self.assertRaises(sqlite3.OperationalError):
                connection.execute("DELETE FROM items")
            connection.close()
            connection = sqlite3.connect(path)
            connection.execute("INSERT INTO import_runs VALUES(2,'2026-09-29 10:00:00',NULL,'test','RUNNING',0)")
            connection.commit()
            connection.close()
            with self.assertRaisesRegex(ValueError, "停止输出业务数据"):
                module.local_run(self.args(path), "local_primary")
            status = module.local_run(self.args(path, command="status"), "local_primary")
            self.assertFalse(status["latest_import_healthy"])

    def test_date_bounds_and_sql_parameterization(self):
        args = self.args("/nonexistent", start="2026-09-01", end="2026-09-20", date=None,
                         product_id="p1' OR 1=1 --")
        start, end = module.period(args)
        self.assertEqual((start, end), ("2026-09-01 00:00:00", "2026-09-21 00:00:00"))
        sql, params = module.build_query(args, start, end)
        self.assertNotIn(args.product_id, sql)
        self.assertIn(args.product_id, params)


if __name__ == "__main__":
    unittest.main()
