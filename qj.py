import os
import datetime
import pandas as pd

import hsic

# interval

def caches(func):
    data = {}
    def wapper(*args,**kwargs):
        key = f'{func.__name__}{args}{kwargs}'
        if key not in data:
            data[key] = func(*args,**kwargs)
        return data[key]
    return wapper

@caches
def interval_ma60(st=None, ed=None, database='mongodb'):
    """
    以60均线分波
    :param st: 开始日期
    :param ed: 终止日期
    :param database: 数据库类型
    :return: 计算结果列表
    """
    short, long, phyd = 12, 26, 9
    if st is None or ed is None:
        st = str(datetime.datetime.now()-datetime.timedelta(days=1))[:10]
        ed = str(datetime.datetime.now()+datetime.timedelta(days=1))[:10]
    if database == 'mongodb':
        data = hsic.mongo_data(st, ed)
    else:
        data = hsic.sql_data(st, ed)
    cou = []
    zts = [('开始时间', '结束时间', '开盘', '最高', '最低', '收盘', '成交量', '60均线上/下方(1/0)', 'K线数量',
            '涨/跌趋势(+/-)', '此波幅度', 'macd绿区', 'macd红区', '异动小于-1.5倍', '异动大于1.5倍')]
    dc2 = [i[4] for i in data]
    dc = []
    yddy, ydxy = 0, 0  # 异动
    _vol = 0  # 成交量

    def get_cou():
        st = cou[-2][0]
        ed = cou[-1][0]
        _O = dc2[st]
        _H = max(dc2[st:ed + 1])
        _L = min(dc2[st:ed + 1])
        _C = dc2[ed]
        jc = _H - _L
        zt = '+' if dc2[st:ed + 1].index(_H) > int((ed - st) / 2) else '-'
        # if 1: #jc > 50:
        _dc = dc[st:ed + 1]
        _macdg = len([_m for _m in range(len(_dc)) if (_m == 0 and _dc[_m]['macd'] < 0) or (_dc[_m]['macd'] < 0 and _dc[_m - 1]['macd'] > 0)])
        _macdr = len([_m for _m in range(len(_dc)) if (_m == 0 and _dc[_m]['macd'] > 0) or (_dc[_m]['macd'] > 0 and _dc[_m - 1]['macd'] < 0)])

        return (str(data[st][0]), str(data[i][0]), _O, _H, _L, _C, _vol, cou[-1][1], ed - st, zt, jc, _macdg, _macdr, ydxy, yddy)
    lend_ = len(data) - 1
    for i, (d, o, h, l, c, v) in enumerate(data):
        dc.append({'ema_short': 0, 'ema_long': 0, 'diff': 0, 'dea': 0, 'macd': 0,
                   'var': 0,  # 方差
                   'std': 0,  # 标准差
                   'mul': 0,  # 异动
                   })
        if i == 1:
            ac = dc2[i - 1]
            dc[i]['ema_short'] = ac + (c - ac) * 2 / short
            dc[i]['ema_long'] = ac + (c - ac) * 2 / long
            # dc[i]['ema_short'] = sum([(short-j)*da[i-j][4] for j in range(short)])/(3*short)
            # dc[i]['ema_long'] = sum([(long-j)*da[i-j][4] for j in range(long)])/(3*long)
            dc[i]['diff'] = dc[i]['ema_short'] - dc[i]['ema_long']
            dc[i]['dea'] = dc[i]['diff'] * 2 / phyd
            dc[i]['macd'] = 2 * (dc[i]['diff'] - dc[i]['dea'])
            # co = 1 if dc[i]['macd'] >= 0 else 0
        elif i > 1:
            dc[i]['ema_short'] = dc[i - 1]['ema_short'] * (short - 2) / short + c * 2 / short
            dc[i]['ema_long'] = dc[i - 1]['ema_long'] * (long - 2) / long + c * 2 / long
            dc[i]['diff'] = dc[i]['ema_short'] - dc[i]['ema_long']
            dc[i]['dea'] = dc[i - 1]['dea'] * (phyd - 2) / phyd + dc[i]['diff'] * 2 / phyd
            dc[i]['macd'] = 2 * (dc[i]['diff'] - dc[i]['dea'])

        if i >= 60:
            _m60 = round(sum(j for j in dc2[i - 59:i + 1]) / 60)

            ma = 60
            std_pj = sum(dc2[i - j] - data[i - j][1] for j in range(ma)) / ma
            dc[i]['var'] = sum((dc2[i - j] - data[i - j][1] - std_pj) ** 2 for j in range(ma)) / ma  # 方差 i-ma+1,i+1
            dc[i]['std'] = dc[i]['var'] ** 0.5  # 标准差
            price =  c - o
            dc[i]['mul'] = _yd = round(price / dc[i]['std'], 2)
            if _yd > 1.5:
                yddy += 1
            elif _yd < -1.5:
                ydxy += 1
            _vol += v
            if c >= _m60:
                if cou and cou[-1][1] != 0:  # and not is_bs(dc[i-10:i+1],_m60,'<'):
                    cou.append((i, 0))
                    zts.append(get_cou())
                    yddy, ydxy = 0, 0
                    _vol = 0
                elif not cou:
                    cou.append((i, 0))
                elif i == lend_:  # data[i][0].day != data[i - 1][0].day or (data[i][0].day == data[i - 1][0].day and str(data[i][0])[11:16]=='09:15') or
                    cou.append((i, 0))
                    zts.append(get_cou())
                    yddy, ydxy = 0, 0
                    _vol = 0
            else:
                if cou and cou[-1][1] != 1:  # and not is_bs(dc[i-10:i+1],_m60,'>'):
                    cou.append((i, 1))
                    zts.append(get_cou())
                    yddy, ydxy = 0, 0
                    _vol = 0
                elif not cou:
                    cou.append((i, 1))
                elif i == lend_:  # data[i][0].day != data[i - 1][0].day or (data[i][0].day == data[i - 1][0].day and str(data[i][0])[11:16]=='09:15') or
                    cou.append((i, 1))
                    zts.append(get_cou())
                    yddy, ydxy = 0, 0
                    _vol = 0

    return zts


def interval_macd(st=None, ed=None, database='mongodb'):
    """
        以 MACD 分波
        :param st: 开始日期
        :param ed: 终止日期
        :param database: 数据库类型
        :return: 计算结果列表
        """
    short, long, phyd = 12, 26, 9
    if st is None or ed is None:
        st = str(datetime.datetime.now()-datetime.timedelta(days=1))[:10]
        ed = str(datetime.datetime.now()+datetime.timedelta(days=1))[:10]
    if database == 'mongodb':
        data = hsic.mongo_data(st, ed)
    else:
        data = hsic.sql_data(st, ed)
    cou = []
    zts = [('开始时间', '结束时间', '开盘', '最高', '最低', '收盘', '成交量', 'macd红/绿区(1/0)', 'K线数量',
            '涨/跌趋势(+/-)', '此波幅度', '60均线下方', '60均线上方', '异动小于-1.5倍', '异动大于1.5倍')]
    dc2 = [i[4] for i in data]
    dc = []
    yddy, ydxy = 0, 0  # 异动
    _vol = 0  # 成交量
    _m60 = 0  # 60均线

    def get_cou():
        st = cou[-2][0]
        ed = cou[-1][0]
        _O = dc2[st]
        _H = max(dc2[st:ed + 1])
        _L = min(dc2[st:ed + 1])
        _C = dc2[ed]
        jc = _H - _L
        zt = '+' if dc2[st:ed + 1].index(_H) > int((ed - st) / 2) else '-'
        # if 1: #jc > 50:
        _dc = dc[st:ed + 1]
        # _ma60g = len([_m for _m in range(len(_dc)) if _C <= _m60])
        _ma60g = len([_m for _m in range(len(_dc)) if (_m == 0 and _C <= _dc[_m]['ma60']) or (_C <= _dc[_m]['ma60'] and dc2[st] > _dc[_m - 1]['ma60'])])
        _ma60r = len([_m for _m in range(len(_dc)) if (_m == 0 and _C > _dc[_m]['ma60']) or (_C > _dc[_m]['ma60'] and dc2[st] <= _dc[_m - 1]['ma60'])])

        return (str(data[st][0]), str(data[i][0]), _O, _H, _L, _C, _vol, cou[-1][1], ed - st, zt, jc, _ma60g, _ma60r, ydxy, yddy)

    macd = None
    lend_ = len(data) - 1
    for i, (d, o, h, l, c, v) in enumerate(data):
        dc.append({'ema_short': 0, 'ema_long': 0, 'diff': 0, 'dea': 0, 'macd': 0,
                   'var': 0,  # 方差
                   'std': 0,  # 标准差
                   'mul': 0,  # 异动
                   'ma60': 0,  # 60均线
                   })
        if i == 1:
            ac = dc2[i - 1]
            this_c = dc2[i]
            dc[i]['ema_short'] = ac + (this_c - ac) * 2 / short
            dc[i]['ema_long'] = ac + (this_c - ac) * 2 / long
            # dc[i]['ema_short'] = sum([(short-j)*da[i-j][4] for j in range(short)])/(3*short)
            # dc[i]['ema_long'] = sum([(long-j)*da[i-j][4] for j in range(long)])/(3*long)
            dc[i]['diff'] = dc[i]['ema_short'] - dc[i]['ema_long']
            dc[i]['dea'] = dc[i]['diff'] * 2 / phyd
            dc[i]['macd'] = 2 * (dc[i]['diff'] - dc[i]['dea'])
            # co = 1 if dc[i]['macd'] >= 0 else 0
        elif i > 1:
            n_c = dc2[i]
            dc[i]['ema_short'] = dc[i - 1]['ema_short'] * (short - 2) / short + n_c * 2 / short
            dc[i]['ema_long'] = dc[i - 1]['ema_long'] * (long - 2) / long + n_c * 2 / long
            dc[i]['diff'] = dc[i]['ema_short'] - dc[i]['ema_long']
            dc[i]['dea'] = dc[i - 1]['dea'] * (phyd - 2) / phyd + dc[i]['diff'] * 2 / phyd
            dc[i]['macd'] = 2 * (dc[i]['diff'] - dc[i]['dea'])

        dc[i]['ma60'] = _m60 = round(sum(j for j in dc2[i - 59:i + 1]) / 60) if i >= 60 else round(sum(j for j in dc2[0:i + 1]) / 60)


        ma = 60
        std_pj = sum(dc2[i - j] - data[i - j][1] for j in range(ma)) / ma
        dc[i]['var'] = sum((dc2[i - j] - data[i - j][1] - std_pj) ** 2 for j in range(ma)) / ma  # 方差 i-ma+1,i+1
        dc[i]['std'] = dc[i]['var'] ** 0.5  # 标准差
        price =  c - o
        dc[i]['mul'] = _yd = round(price / dc[i]['std'], 2)
        if _yd > 1.5:
            yddy += 1
        elif _yd < -1.5:
            ydxy += 1
        _vol += v
        _macd = 1 if dc[i]['macd'] > 0 else 0
        judge = data[i][0].day != data[i - 1][0].day or (data[i][0].day == data[i - 1][0].day and str(data[i][0])[11:16]=='09:15') or i == lend_
        if macd != _macd or judge:
            macd = _macd
            if macd > 0:
                if cou and cou[-1][1] != 0:  # and not is_bs(dc[i-10:i+1],_m60,'<'):
                    cou.append((i, 0))
                    zts.append(get_cou())
                    yddy, ydxy = 0, 0
                    _vol = 0
                elif not cou:
                    cou.append((i, 0))
                elif judge:
                    cou.append((i, 0))
                    zts.append(get_cou())
                    yddy, ydxy = 0, 0
                    _vol = 0
            else:
                if cou and cou[-1][1] != 1:  # and not is_bs(dc[i-10:i+1],_m60,'>'):
                    cou.append((i, 1))
                    zts.append(get_cou())
                    yddy, ydxy = 0, 0
                    _vol = 0
                elif not cou:
                    cou.append((i, 1))
                elif judge:
                    cou.append((i, 1))
                    zts.append(get_cou())
                    yddy, ydxy = 0, 0
                    _vol = 0

    return zts


def interval_change(st=None, ed=None, database='mongodb'):
    """
        以异动分波
        :param st: 开始日期
        :param ed: 终止日期
        :param database: 数据库类型
        :return: 计算结果列表
        """
    short, long, phyd = 12, 26, 9
    if st is None or ed is None:
        st = str(datetime.datetime.now() - datetime.timedelta(days=1))[:10]
        ed = str(datetime.datetime.now() + datetime.timedelta(days=1))[:10]
    if database == 'mongodb':
        data = hsic.mongo_data(st, ed)
    else:
        data = hsic.sql_data(st, ed)
    cou = []
    zts = [('开始时间', '结束时间', '开盘', '最高', '最低', '收盘', '成交量', '异动正/反(1/0)', 'K线数量',  # 60均线上/下方(1/0)
            '涨/跌趋势(+/-)', '此波幅度', 'macd绿区', 'macd红区', '异动小于-1.5倍', '异动大于1.5倍')]
    dc2 = [i[4] for i in data]
    dc = []
    yddy, ydxy = 0, 0  # 异动
    _vol = 0  # 成交量

    def get_cou():
        st = cou[-2][0]
        ed = cou[-1][0]
        _O = dc2[st]
        _H = max(dc2[st:ed + 1])
        _L = min(dc2[st:ed + 1])
        _C = dc2[ed]
        jc = _H - _L
        zt = '+' if dc2[st:ed + 1].index(_H) > int((ed - st) / 2) else '-'
        # if 1: #jc > 50:
        _dc = dc[st:ed + 1]
        _macdg = len([_m for _m in range(len(_dc)) if
                      (_m == 0 and _dc[_m]['macd'] < 0) or (_dc[_m]['macd'] < 0 and _dc[_m - 1]['macd'] > 0)])
        _macdr = len([_m for _m in range(len(_dc)) if
                      (_m == 0 and _dc[_m]['macd'] > 0) or (_dc[_m]['macd'] > 0 and _dc[_m - 1]['macd'] < 0)])

        return (
        str(data[st][0]), str(data[i][0]), _O, _H, _L, _C, _vol, cou[-1][1], ed - st, zt, jc, _macdg, _macdr, ydxy,
        yddy)
    lend_ = len(data) - 1
    for i, (d, o, h, l, c, v) in enumerate(data):
        dc.append({'ema_short': 0, 'ema_long': 0, 'diff': 0, 'dea': 0, 'macd': 0,
                   'var': 0,  # 方差
                   'std': 0,  # 标准差
                   'mul': 0,  # 异动
                   })
        if i == 1:
            ac = dc2[i - 1]
            this_c = dc2[i]
            dc[i]['ema_short'] = ac + (this_c - ac) * 2 / short
            dc[i]['ema_long'] = ac + (this_c - ac) * 2 / long
            # dc[i]['ema_short'] = sum([(short-j)*da[i-j][4] for j in range(short)])/(3*short)
            # dc[i]['ema_long'] = sum([(long-j)*da[i-j][4] for j in range(long)])/(3*long)
            dc[i]['diff'] = dc[i]['ema_short'] - dc[i]['ema_long']
            dc[i]['dea'] = dc[i]['diff'] * 2 / phyd
            dc[i]['macd'] = 2 * (dc[i]['diff'] - dc[i]['dea'])
            # co = 1 if dc[i]['macd'] >= 0 else 0
        elif i > 1:
            n_c = dc2[i]
            dc[i]['ema_short'] = dc[i - 1]['ema_short'] * (short - 2) / short + n_c * 2 / short
            dc[i]['ema_long'] = dc[i - 1]['ema_long'] * (long - 2) / long + n_c * 2 / long
            dc[i]['diff'] = dc[i]['ema_short'] - dc[i]['ema_long']
            dc[i]['dea'] = dc[i - 1]['dea'] * (phyd - 2) / phyd + dc[i]['diff'] * 2 / phyd
            dc[i]['macd'] = 2 * (dc[i]['diff'] - dc[i]['dea'])

        if i >= 60:
            # _m60 = round(sum(j for j in dc2[i - 59:i + 1]) / 60)

            ma = 60
            std_pj = sum(dc2[i - j] - data[i - j][1] for j in range(ma)) / ma
            dc[i]['var'] = sum((dc2[i - j] - data[i - j][1] - std_pj) ** 2 for j in range(ma)) / ma  # 方差 i-ma+1,i+1
            dc[i]['std'] = dc[i]['var'] ** 0.5  # 标准差
            price = c - o
            dc[i]['mul'] = _yd = round(price / dc[i]['std'], 2)
            if _yd > 1.5:
                yddy += 1
            elif _yd < -1.5:
                ydxy += 1
            _vol += v
            if _yd > 1.5:
                if cou and cou[-1][1] != 0:  # and not is_bs(dc[i-10:i+1],_m60,'<'):
                    cou.append((i, 0))
                    zts.append(get_cou())
                    yddy, ydxy = 0, 0
                    _vol = 0
                elif not cou:
                    cou.append((i, 0))
                elif data[i][0].day != data[i - 1][0].day or (
                        data[i][0].day == data[i - 1][0].day and str(data[i][0])[11:16] == '09:15') or i == lend_:
                    cou.append((i, 0))
                    zts.append(get_cou())
                    yddy, ydxy = 0, 0
                    _vol = 0
            elif _yd < -1.5:
                if cou and cou[-1][1] != 1:  # and not is_bs(dc[i-10:i+1],_m60,'>'):
                    cou.append((i, 1))
                    zts.append(get_cou())
                    yddy, ydxy = 0, 0
                    _vol = 0
                elif not cou:
                    cou.append((i, 1))
                elif data[i][0].day != data[i - 1][0].day or (
                        data[i][0].day == data[i - 1][0].day and str(data[i][0])[11:16] == '09:15') or i == lend_:
                    cou.append((i, 1))
                    zts.append(get_cou())
                    yddy, ydxy = 0, 0
                    _vol = 0

    return zts


def interval_yinyang(st=None, ed=None, database='mongodb'):
    """
        以阴阳线分波
        :param st: 开始日期
        :param ed: 终止日期
        :param database: 数据库类型
        :return: 计算结果列表
        """
    short, long, phyd = 12, 26, 9
    if st is None or ed is None:
        st = str(datetime.datetime.now() - datetime.timedelta(days=1))[:10]
        ed = str(datetime.datetime.now() + datetime.timedelta(days=1))[:10]
    if database == 'mongodb':
        data = hsic.mongo_data(st, ed)
    else:
        data = hsic.sql_data(st, ed)
    # data2 = []
    # _d,_o,_h,_l,_v = None,0,0,100**5,0
    # for i, (d, o, h, l, c, v) in enumerate(data):
    #     if _d is None:
    #         _d = d
    #         _o = o
    #     _h = h if h>_h else _h
    #     _l = l if l<_l else _l
    #     _v += v
    #     data_i = data[i-1]
    #     if i>0 and ((c-o>0 and data_i[4]-data_i[1]<=0) or (c-o<=0 and data_i[4]-data_i[1]>0)):
    #         data2.append((_d,_o,_h,_l,c,_v))
    #         _d, _o, _h, _l, _v = None, 0, 0, 100 ** 5, 0
    # data = data2
    cou = []
    zts = [('开始时间', '结束时间', '开盘', '最高', '最低', '收盘', '成交量', '60均线下方', '60均线上方',  # 60均线上/下方(1/0)
            '涨/跌趋势(+/-)', '此波幅度', 'macd绿区', 'macd红区', '异动小于-1.5倍', '异动大于1.5倍')]
    dc2 = [i[4] for i in data]
    dc = []
    yddy, ydxy = 0, 0  # 异动
    _vol = 0  # 成交量

    def get_cou():
        st = cou[-2][0]
        ed = cou[-1][0]
        _O = dc2[st]
        _H = max(dc2[st:ed + 1])
        _L = min(dc2[st:ed + 1])
        _C = dc2[ed]
        jc = _H - _L
        zt = '+' if dc2[st:ed + 1].index(_H) > int((ed - st) / 2) else '-'
        # if 1: #jc > 50:
        _dc = dc[st:ed + 1]
        _ma60g = len([_m for _m in range(len(_dc)) if
                      (_m == 0 and _C <= _dc[_m]['ma60']) or (_C <= _dc[_m]['ma60'] and dc2[st] > _dc[_m - 1]['ma60'])])
        _ma60r = len([_m for _m in range(len(_dc)) if
                      (_m == 0 and _C > _dc[_m]['ma60']) or (_C > _dc[_m]['ma60'] and dc2[st] <= _dc[_m - 1]['ma60'])])

        _macdg = len([_m for _m in range(len(_dc)) if
                      (_m == 0 and _dc[_m]['macd'] < 0) or (_dc[_m]['macd'] < 0 and _dc[_m - 1]['macd'] > 0)])
        _macdr = len([_m for _m in range(len(_dc)) if
                      (_m == 0 and _dc[_m]['macd'] > 0) or (_dc[_m]['macd'] > 0 and _dc[_m - 1]['macd'] < 0)])

        return (
        str(data[st][0]), str(data[i][0]), _O, _H, _L, _C, _vol, _ma60g, _ma60r, zt, jc, _macdg, _macdr, ydxy,
        yddy)

    lend_ = len(data) - 1
    for i, (d, o, h, l, c, v) in enumerate(data):
        dc.append({'ema_short': 0, 'ema_long': 0, 'diff': 0, 'dea': 0, 'macd': 0,
                   'var': 0,  # 方差
                   'std': 0,  # 标准差
                   'mul': 0,  # 异动
                   'ma60': 0,  # 60均线
                   })
        if i == 1:
            ac = dc2[i - 1]
            this_c = dc2[i]
            dc[i]['ema_short'] = ac + (this_c - ac) * 2 / short
            dc[i]['ema_long'] = ac + (this_c - ac) * 2 / long
            # dc[i]['ema_short'] = sum([(short-j)*da[i-j][4] for j in range(short)])/(3*short)
            # dc[i]['ema_long'] = sum([(long-j)*da[i-j][4] for j in range(long)])/(3*long)
            dc[i]['diff'] = dc[i]['ema_short'] - dc[i]['ema_long']
            dc[i]['dea'] = dc[i]['diff'] * 2 / phyd
            dc[i]['macd'] = 2 * (dc[i]['diff'] - dc[i]['dea'])
            # co = 1 if dc[i]['macd'] >= 0 else 0
        elif i > 1:
            n_c = dc2[i]
            dc[i]['ema_short'] = dc[i - 1]['ema_short'] * (short - 2) / short + n_c * 2 / short
            dc[i]['ema_long'] = dc[i - 1]['ema_long'] * (long - 2) / long + n_c * 2 / long
            dc[i]['diff'] = dc[i]['ema_short'] - dc[i]['ema_long']
            dc[i]['dea'] = dc[i - 1]['dea'] * (phyd - 2) / phyd + dc[i]['diff'] * 2 / phyd
            dc[i]['macd'] = 2 * (dc[i]['diff'] - dc[i]['dea'])
        dc[i]['ma60'] = _m60 = round(sum(j for j in dc2[i - 59:i + 1]) / 60) if i >= 60 else round(
            sum(j for j in dc2[0:i + 1]) / 60)
        price = c - o
        if i >= 60:
            # _m60 = round(sum(j for j in dc2[i - 59:i + 1]) / 60)
            ma = 60
            std_pj = sum(dc2[i - j] - data[i - j][1] for j in range(ma)) / ma
            dc[i]['var'] = sum((dc2[i - j] - data[i - j][1] - std_pj) ** 2 for j in range(ma)) / ma  # 方差 i-ma+1,i+1
            dc[i]['std'] = dc[i]['var'] ** 0.5  # 标准差

            dc[i]['mul'] = _yd = round(price / dc[i]['std'], 2)
            if _yd > 1.5:
                yddy += 1
            elif _yd < -1.5:
                ydxy += 1
        _vol += v
        if price > 0:
            if cou and cou[-1][1] != 0:  # and not is_bs(dc[i-10:i+1],_m60,'<'):
                cou.append((i, 0))
                zts.append(get_cou())
                yddy, ydxy = 0, 0
                _vol = 0
            elif not cou:
                cou.append((i, 0))
            elif data[i][0].day != data[i - 1][0].day or (
                    data[i][0].day == data[i - 1][0].day and str(data[i][0])[11:16] == '09:15') or i == lend_:
                cou.append((i, 0))
                zts.append(get_cou())
                yddy, ydxy = 0, 0
                _vol = 0
        else:
            if cou and cou[-1][1] != 1:  # and not is_bs(dc[i-10:i+1],_m60,'>'):
                cou.append((i, 1))
                zts.append(get_cou())
                yddy, ydxy = 0, 0
                _vol = 0
            elif not cou:
                cou.append((i, 1))
            elif data[i][0].day != data[i - 1][0].day or (
                    data[i][0].day == data[i - 1][0].day and str(data[i][0])[11:16] == '09:15') or i == lend_:
                cou.append((i, 1))
                zts.append(get_cou())
                yddy, ydxy = 0, 0
                _vol = 0
    return zts


head='''
<html><head><meta charset="UTF-8"><title></title>
<script type="text/javascript" src="http://www.a667.com:8000/static/js/jquery-1.7.1.min.js"></script>
<script type="text/javascript" src="http://www.a667.com:8000/static/js/echarts.min.js"></script></head>
<body>
<hr/><div id="show_hq_message" style="position:absolute;left:10px;font-weight:bold;"></div><br/><br/><br/>
<div id="main" style="width: auto;height: 680px;" align="center"></div>
</body><script>
        var myChart = echarts.init(document.getElementById('main'));
 //数据模型 time0 open1 close2 min3 max4 vol5 tag6 macd7 dif8 dea9
//['2015-10-19',18.56,18.25,18.19,18.56,55.00,0,-0.00,0.08,0.09] 
var data = splitData(
'''

tail = '''), zts='''

tail2 = ''', paramnames='''

tail3 = ''';
//数组处理
function splitData(rawData) {
  var datas = [],times = [],vols = [],macds = [],difs = [],deas = [];
  for (var i = 0; i < rawData.length; i++) {datas.push(rawData[i]);times.push(rawData[i].splice(0, 1)[0]);vols.push(rawData[i][4]);macds.push(rawData[i][6]);difs.push(rawData[i][7]);
      deas.push(rawData[i][8]);}
  return {datas: datas,times: times,vols: vols,macds: macds,difs: difs,deas: deas};
}
//分段计算
function fenduans(){
  var markLineData = [],idx = 0,tag = 0,vols = 0;
  for (var i = 0; i < data.times.length; i++) {
      //初始化数据
      if(data.datas[i][5] != 0 && tag == 0){
          idx = i; vols = data.datas[i][4]; tag = 1;
      }
      if(tag == 1){ vols += data.datas[i][4]; }
      if(data.datas[i][5] != 0 && tag == 1){
          markLineData.push([{
              xAxis: idx,
              yAxis: data.datas[idx][1]>data.datas[idx][0]?(data.datas[idx][3]).toFixed(2):(data.datas[idx][2]).toFixed(2),
              value: vols
          }, {
              xAxis: i,
              yAxis: data.datas[i][1]>data.datas[i][0]?(data.datas[i][3]).toFixed(2):(data.datas[i][2]).toFixed(2)
          }]);
          idx = i; vols = data.datas[i][4]; tag = 2;
      }
      //更替数据
      if(tag == 2){ vols += data.datas[i][4]; }
      if(data.datas[i][5] != 0 && tag == 2){
          markLineData.push([{
              xAxis: idx,
              yAxis: data.datas[idx][1]>data.datas[idx][0]?(data.datas[idx][3]).toFixed(2):(data.datas[idx][2]).toFixed(2),
              value: (vols/(i-idx+1)).toFixed(2)+' M'
          }, {
              xAxis: i,
              yAxis: data.datas[i][1]>data.datas[i][0]?(data.datas[i][3]).toFixed(2):(data.datas[i][2]).toFixed(2)
          }]);
          idx = i; vols = data.datas[i][4];
      }
  }
  return markLineData;
}
//MA计算公式
function calculateMA(dayCount) {
  var result = [];
  for (var i = 0, len = data.times.length; i < len; i++) {
      if (i < dayCount) {
          result.push('-');
          continue;
      }
      var sum = 0;
      for (var j = 0; j < dayCount; j++) {
          sum += data.datas[i - j][1];
      }
      result.push((sum / dayCount).toFixed(2));
  }
  return result;
}
var option = {
  title: {
      text: 'K线周期图表',
      left: 0
  },
  tooltip: {
      trigger: 'axis',
      axisPointer: {
          type: 'cross',//'line', //'shadow'
          textStyle:{
　　          align:'left'
　　　　    }
      },
        formatter: function(params, ticket, callback) {
            var _dt = params[0].name;
            var htmls = "";
            var htmls2 = '时间：'+_dt+"<br>";
            for (var i = 0, l = params.length; i < l; i++) {
                var p=params[i].value;
                if(p){
                    if(typeof(p)=='object'){
                        var nm=['','开盘价','收盘价','最低价','最高价','成交量','','MACD','DIFF','DEA'];
                        for(var j = 0; j < nm.length; j++){ // time0 open1 close2 min3 max4 vol5 tag6 macd7 dif8 dea9
                            if(j==0||j==6){
                                continue;
                            }
                            htmls2 += nm[j] + ': ' + p[j] +'<br>';
                        }                            
                    }
                }
            }
            for(var i=0;i<paramnames.length;i++){
                var K=paramnames[i],V=zts[_dt][i];
                /*if(V==0 and K.indexOf('数量')<0){
                    htmls += "<span style='color:green;'>"+ K + ": " + V +"</span>  ";
                }else if(V==1 and K.indexOf('数量')<0){
                    htmls += "<span style='color:red;'>"+ K + ": " + V +"</span>  ";
                }else{
                    htmls += K + ': ' + V +'  ';
                }*/
                htmls += K + ': ' + V +'  ';
                if(i%8==0 && i>0){ htmls += "</br>"; }
            }
            $("#show_hq_message").html(htmls);
            return htmls2;
        }
  },
  legend:{ //图例控件,点击图例控制哪些系列不显示
        data:['日K','MA5','MA10','MA20','MA30'],
        selected:{
            // 默认不显示
            'MA30': false,
        }
    },
  axisPointer: {   
                link: [{
                    xAxisIndex: [0] //生成十字轴，控制3个x轴
            }]
  },
  grid: [           {
      left: '3%',
      right: '1%',
      height: '60%'
  },{
      left: '3%',
      right: '1%',
      top: '71%',
      height: '10%'
  },{
      left: '3%',
      right: '1%',
      top: '82%',
      height: '14%'
  }],
  xAxis: [{
      type: 'category',
      data: data.times,
      scale: true,
      boundaryGap: false,
      axisLine: { onZero: false },
      splitLine: { show: false },
      splitNumber: 20,
      min: 'dataMin',
      max: 'dataMax'
  },{
      type: 'category',
      gridIndex: 1,
      data: data.times,
      axisLabel: {show: false}
  },{
      type: 'category',
      gridIndex: 2,
      data: data.times,
      axisLabel: {show: false}
  }],
  yAxis: [{
      scale: true,
      splitArea: {
          show: false
      }
  },{
      gridIndex: 1,
      splitNumber: 3,
      axisLine: {onZero: false},
      axisTick: {show: false},
      splitLine: {show: false},
      axisLabel: {show: true}
  },{
      gridIndex: 2,
      splitNumber: 4,
      axisLine: {onZero: false},
      axisTick: {show: false},
      splitLine: {show: false},
      axisLabel: {show: true}
  }],
  dataZoom: [{
          type: 'inside',
          xAxisIndex: [0, 0],
          start: 20,
          end: 100
    },{
          show: true,
          xAxisIndex: [0, 1],
          type: 'slider',
          top: '97%',
          start: 20,
          end: 100
    },{
      show: false,
      xAxisIndex: [0, 2],
      type: 'slider',
      start: 20,
      end: 100
  }],
  series: [{
          name: 'K线周期图表',
          type: 'candlestick',
          data: data.datas,
          itemStyle: {
              normal: {
                  color: '#ef232a',
                  color0: '#14b143',
                  borderColor: '#ef232a',
                  borderColor0: '#14b143'
              }
          },
      }, {
          name: 'MA5',
          type: 'line',
          data: calculateMA(5),
          smooth: true,
          lineStyle: {
              normal: {
                  opacity: 0.5
              }
          }
      },
            {
                name:'MA10',
                type:'line',
                data:calculateMA(10),
                smooth:true,
                lineStyle:{ //标线的样式
                    normal:{opacity:0.5}
                }
            },
            {
                name:'MA20',
                type:'line',
                data:calculateMA(20),
                smooth:true,
                lineStyle:{
                    normal:{opacity:0.5}
                }
            },
            {
                name:'MA30',
                type:'line',
                data:calculateMA(30),
                smooth:true,
                lineStyle:{
                    normal:{opacity:0.5}
                }
            },{
          name: 'Volumn',
          type: 'bar',
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: data.vols,
          itemStyle: {
              normal: {
                  color: function(params) {
                      var colorList;
                      if (data.datas[params.dataIndex][1]>data.datas[params.dataIndex][0]) {
                          colorList = '#ef232a';
                      } else {
                          colorList = '#14b143';
                      }
                      return colorList;
                  },
              }
          }
      },{
          name: 'MACD',
          type: 'bar',
          xAxisIndex: 2,
          yAxisIndex: 2,
          data: data.macds,
          itemStyle: {
              normal: {
                  color: function(params) {
                      var colorList;
                      if (params.data >= 0) {
                          colorList = '#ef232a';
                      } else {
                          colorList = '#14b143';
                      }
                      return colorList;
                  },
              }
          }
      },{
          name: 'DIF',
          type: 'line',
          xAxisIndex: 2,
          yAxisIndex: 2,
          data: data.difs
      },{
          name: 'DEA',
          type: 'line',
          xAxisIndex: 2,
          yAxisIndex: 2,
          data: data.deas
      }
  ]
};  
myChart.setOption(option);
    </script>
</html>
'''


def get_macd(data):
    short, long, phyd = 12, 26, 9
    cou = []
    hp = []
    dc = []
    data2 = []
    for i, (d, o, c, l, h, v) in enumerate(data):
        dc.append({'ema_short': 0, 'ema_long': 0, 'diff': 0, 'dea': 0, 'macd': 0})
        if i == 1:
            ac = data[i - 1][4]
            dc[i]['ema_short'] = ac + (c - ac) * 2 / short
            dc[i]['ema_long'] = ac + (c - ac) * 2 / long
            # dc[i]['ema_short'] = sum([(short-j)*da[i-j][4] for j in range(short)])/(3*short)
            # dc[i]['ema_long'] = sum([(long-j)*da[i-j][4] for j in range(long)])/(3*long)
            dc[i]['diff'] = dc[i]['ema_short'] - dc[i]['ema_long']
            dc[i]['dea'] = dc[i]['diff'] * 2 / phyd
            dc[i]['macd'] = 2 * (dc[i]['diff'] - dc[i]['dea'])
        elif i > 1:
            dc[i]['ema_short'] = dc[i - 1]['ema_short'] * (short - 2) / short + c * 2 / short
            dc[i]['ema_long'] = dc[i - 1]['ema_long'] * (long - 2) / long + c * 2 / long
            dc[i]['diff'] = dc[i]['ema_short'] - dc[i]['ema_long']
            dc[i]['dea'] = dc[i - 1]['dea'] * (phyd - 2) / phyd + dc[i]['diff'] * 2 / phyd
            dc[i]['macd'] = 2 * (dc[i]['diff'] - dc[i]['dea'])
        data2.append([d, o, c, l, h, v, 0, round(dc[i]['macd'], 2), round(dc[i]['diff'], 2), round(dc[i]['dea'], 2)])
    return data2


def main():
    # 起止日期设置
    ed = datetime.datetime.now() + datetime.timedelta(days=1)
    sd = str(ed - datetime.timedelta(days=6))[:10]
    ed = str(ed)[:10]

    zts = interval_ma60(sd, ed, database='sql')

    # 写入 CSV 文件
    with open('a.csv', 'w') as f:
        for i in zts:
            f.write(','.join([str(j) for j in i]))
            f.write('\n')

    # 写入 HTML
    d = [[i[0], i[2], i[5], i[4], i[3], i[6]] for i in zts[1:]]
    d = str(get_macd(d))  # 计算Macd
    parhead = str(list(zts[0]))  # 字段名称
    zts = str({i[0]: list(i) for i in zts[1:]})
    with open('qj.html', 'w', encoding='utf-8') as f:
        f.write(head)
        f.write(d)
        f.write(tail)
        f.write(zts)
        f.write(tail2)
        f.write(parhead)
        f.write(tail3)

    # 打开HTML文件
    os.system('start qj.html')

def test():
    data = interval_ma60('2018-08-01', '2018-08-06', database='sql')
    data_pd = pd.DataFrame(data[1:], columns=data[0])
    data_pd.to_pickle('data.pkl')
    print(data_pd.head())


if __name__ == '__main__':
    # main()
    test()