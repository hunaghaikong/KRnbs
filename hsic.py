import pymongo
import datetime
import math
import pymysql

from util import sql_user,sql_pwd, mongo_user,mongo_pwd 


class MongoDBData:
    """ MongoDB 数据库的连接与数据查询处理类 """

    def __init__(self, db='HKFuture', table='future_1min'):
        self.db_name = db
        self.table = table
        self._coll = self.get_coll()

    def get_coll(self):
        """ 获取连接 """
        client = pymongo.MongoClient('mongodb://192.168.2.226:27017')

        client.admin.authenticate(mongo_user, mongo_pwd)
        self.db = client[self.db_name]
        coll = self.db[self.table]
        return coll

    def get_hsi(self, sd, ed, code='HSI'):
        """
        获取指定开始日期，结束日期，指定合约的恒指分钟数据
        :param sd: 开始日期
        :param ed: 结束日期
        :param code: 合约代码
        :return:
        """

        if isinstance(sd, str):
            sd = datetime.datetime.strptime(sd, '%Y-%m-%d')
        if isinstance(ed, str):
            ed = datetime.datetime.strptime(ed, '%Y-%m-%d')
        dates = set()
        start_dates = [sd]
        _month = sd.month
        _year = sd.year
        e_y = ed.year
        e_m = ed.month
        _while = 0

        while _year < e_y or (_year == e_y and _month <= e_m):
            _month = sd.month + _while
            _year = sd.year + math.ceil(_month / 12) - 1
            _month = _month % 12 if _month % 12 else 12
            code = code[:3] + str(_year)[2:] + ('0' + str(_month) if _month < 10 else str(_month))
            try:
                _ed = self.db['future_contract_info'].find({'CODE': code})[0]['EXPIRY_DATE']
            except:
                return
            if _ed not in start_dates:
                start_dates.append(_ed)
            _while += 1
            if sd >= _ed:
                continue
            _sd = start_dates[-2]

            if _sd > ed:
                return
            data = self._coll.find({'datetime': {'$gte': _sd, '$lt': _ed}, 'code': code},
                                   projection=['datetime', 'open', 'high', 'low', 'close','volume']).sort('datetime',
                                                                                                           1)  # 'HSI1808'

            _frist = True
            for i in data:
                date = i['datetime']
                if _frist:
                    _frist = False
                    exclude_time = str(date)[:10]
                    dates.add(datetime.datetime.strptime(exclude_time + ' 09:14:00', '%Y-%m-%d %H:%M:%S'))
                    dates.add(datetime.datetime.strptime(exclude_time + ' 12:59:00', '%Y-%m-%d %H:%M:%S'))
                if date not in dates:
                    dates.add(date)
                    if date > ed:
                        return
                    yield [date, i['open'], i['high'], i['low'], i['close'], i['volume']]



def mongo_data(st='2018-08-01', ed='2018-11-10'):
    mongo=MongoDBData()
    data = tuple(mongo.get_hsi(st, ed))
    return data


def sql_data(st='2018-11-08', ed='2018-11-10'):
    sql = f"SELECT DATETIME,OPEN,high,low,CLOSE,vol FROM wh_same_month_min WHERE prodcode='HSI' AND DATETIME>='{st}' AND DATETIME<='{ed}' ORDER BY DATETIME"
    conn = pymysql.connect(db='carry_investment', user=sql_user, passwd=sql_pwd, host='192.168.2.226',charset='utf8') 
    cur = conn.cursor()
    cur.execute(sql)
    conn.close()
    return cur.fetchall()