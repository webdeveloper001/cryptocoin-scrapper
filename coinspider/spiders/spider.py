import scrapy
import pprint
import csv
import string
import psycopg2
import coinspider.env as env


class FormatDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"

class CoinSpider(scrapy.Spider):
    name = "coin"

    def __init__(self):
        """
        Connect Db & Execute Test fetch :   get all table names.
        """
        pprint.pprint(env.db);
        self.conn = psycopg2.connect(
            host=env.db['host'], 
            database=env.db['database'], 
            user=env.db['user'], 
            password=env.db['password']
        )
        self.cursor = self.conn.cursor()
        self.cursor.execute("select relname from pg_class where relkind='r' and relname !~ '^(pg_|sql_)';")
        pprint.pprint(self.cursor.fetchall())
        self.conn.rollback();

    def start_requests(self):
        urls = [
            "https://coinmetrics.io/data/btc.csv",
            "https://coinmetrics.io/data/bch.csv",
            "https://coinmetrics.io/data/ltc.csv",
            "https://coinmetrics.io/data/eth.csv",
            "https://coinmetrics.io/data/xem.csv",
            "https://coinmetrics.io/data/dcr.csv",
            "https://coinmetrics.io/data/zec.csv",
            "https://coinmetrics.io/data/dash.csv",
            "https://coinmetrics.io/data/doge.csv",
            "https://coinmetrics.io/data/etc.csv",
            "https://coinmetrics.io/data/pivx.csv",
            "https://coinmetrics.io/data/xmr.csv",
            "https://coinmetrics.io/data/vtc.csv",
            "https://coinmetrics.io/data/xvg.csv",
            "https://coinmetrics.io/data/dgb.csv",
            "https://coinmetrics.io/data/btg.csv",
            "https://coinmetrics.io/data/eos.csv",
            "https://coinmetrics.io/data/trx.csv",
            "https://coinmetrics.io/data/icx.csv",
            "https://coinmetrics.io/data/ppt.csv",
            "https://coinmetrics.io/data/omg.csv",
            "https://coinmetrics.io/data/bnb.csv",
            "https://coinmetrics.io/data/snt.csv",
            "https://coinmetrics.io/data/wtc.csv",
            "https://coinmetrics.io/data/rep.csv",
            "https://coinmetrics.io/data/zrx.csv",
            "https://coinmetrics.io/data/veri.csv",
            "https://coinmetrics.io/data/bat.csv",
            "https://coinmetrics.io/data/knc.csv",
            "https://coinmetrics.io/data/gnt.csv",
            "https://coinmetrics.io/data/fun.csv",
            "https://coinmetrics.io/data/gno.csv",
            "https://coinmetrics.io/data/salt.csv"
        ]
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def create_table_if_not_exists(self, table, key_fields = []):
        """
        CREATE TABLE for specific cryptocurrency. 
        e.g btc, bch, ltc 
        *Important* Coin Name IS Table Name
        """
        fields = ""
        for idx in range(len(key_fields)):
            type_str = "DECIMAL"
            if(idx == 0):
                type_str = "DATE"
            fields = fields + key_fields[idx] + " " + type_str
            if(idx != len(key_fields) - 1):
                fields = fields + ","

        query = 'CREATE TABLE IF NOT EXISTS ' + table + '(' + fields + ");"
        self.cursor.execute(query)
        self.conn.commit()
        pprint.pprint(query)

    def compare_diff_push(self, table, records, key_fields):
        """
        Compare Diff on specific table and fetched data. 
        Grab the last point (probably yesterday) and insert new records from the point.
        Will be executed and push data on daily basis.
        """
        query = 'SELECT * FROM '+ table + ' ORDER BY date DESC LIMIT 1'
        self.cursor.execute(query)
        last_record = self.cursor.fetchone()
        idx = 0
        if last_record:
            for row in records:
                idx = idx + 1
                if row[key_fields[0]] == last_record[0].strftime("%Y-%m-%d"):
                    break

        pprint.pprint(idx)

        if idx != len(records):
            for row in records[idx:]:
                query = "INSERT INTO " + table + " ("
                for idx in range(len(key_fields)):
                    query = query + key_fields[idx]
                    if(idx != len(key_fields) - 1):
                        query = query + ","
                query = query + ") VALUES ("
                for idx in range(len(key_fields)):
                    if(idx == 0):
                        query = query + "'"+row[key_fields[idx]]+"'"
                    else:
                        query = query + row[key_fields[idx]]
                    if(idx != len(key_fields) - 1):
                        query = query + ", "
                query = query + ");"


                # query = "INSERT INTO {table} (date, txVolume, txCount, marketcap, price, exchangeVolume, generatedCoins, fees) VALUES ('{date}', {txVolume}, {txCount}, {marketcap}, {price}, {exchangeVolume}, {generatedCoins}, {fees})"
                # formatter = string.Formatter()
                # mapping = FormatDict(table = table,
                #     date= row[0],
                #     txVolume= row[1],
                #     txCount= row[2],
                #     marketcap= row[3],
                #     price= row[4],
                #     exchangeVolume= row[5],
                #     generatedCoins= row[6],
                #     fees= row[7])
                # query = formatter.vformat(query, (), mapping)

                pprint.pprint(query)

                self.cursor.execute(query)
                self.conn.commit();
        else:
            pprint.pprint("Table "+table+" is up to date")

    def parse(self, response):
        page = response.url.split("/")[-1].split(".")[0]  # page = coin name
        data = response.body # csv body
        result = [row for row in csv.reader(data.splitlines(), delimiter=',')] # fetch data part of csv

        records = []

        key_fields = []
        for row in result[0]:
            key_fields.append(row.strip().split('(')[0])

        for row in result[1:]:
            item = {}
            idx = 0
            for idx in range(len(key_fields)):
                item[key_fields[idx]] = row[idx]
            records.append(item)

        self.create_table_if_not_exists(page, key_fields)

        self.compare_diff_push(page, records, key_fields)

        pprint.pprint(page)
