import datetime
from qj import interval_ma60

def tj(qzz,ccc,ydd):
    """ 模拟统计 """
    ed = datetime.datetime.now() + datetime.timedelta(days=1)
    sd = str(ed - datetime.timedelta(days=60))[:10]
    ed = str(ed)[:10]

    data = interval_ma60('2018-01-03', ed, database='mongodb')
    ykAll = []  # 盈亏
    st_k,st_d = [],[]  # 开仓
    zd_k,zd_d = 0,0    # 做空、做多的单数
    yl_k,yl_d = 0,0    # 做空、做多的盈亏数量
    max_cc = 0  # 最大持仓
    cc_k,cc_d = 0,0  # 持仓

    # for _st,_et,_o,_h,_l,_c,*_ in data[1:]:
    #     if _h - _l >= 120:
    #         if _o > _c and cc_k<10:  # 阴波做空
    #             st_k.append((_et,_c))
    #             cc_k += 1
    #             cc_d = 0
    #             max_cc = cc_k if cc_k > max_cc else max_cc
    #             while st_d:
    #                 price = _c - st_d.pop()[1]
    #                 ykAll.append(price)
    #                 zd_k += 1
    #                 if price>0:
    #                     yl_k += 1
    #         if _o < _c and cc_d<10:  # 阳波做多
    #             st_d.append((_et,_c))
    #             cc_d += 1
    #             cc_k = 0
    #             max_cc = cc_d if cc_d > max_cc else max_cc
    #             while st_k:
    #                 price = st_k.pop()[1] - _c
    #                 ykAll.append(price)
    #                 zd_d += 1
    #                 if price > 0:
    #                     yl_d += 1

    data.pop(0)
    dc = []
    dc2 = [i[5] for i in data]
    short, long, phyd = 12, 26, 9
    for i,(d,_et,o,h,l,c,*_) in enumerate(data):
        dc.append({'ema_short': 0, 'ema_long': 0, 'diff': 0, 'dea': 0, 'macd': 0,
                   'var': 0,  # 方差
                   'std': 0,  # 标准差
                   'mul': 0,  # 异动
                   })
        if i == 1:
            ac = data[i - 1][5]
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
            ma = 60
            std_pj = sum(dc2[i - j] - data[i - j][2] for j in range(ma)) / ma
            dc[i]['var'] = sum((dc2[i - j] - data[i - j][2] - std_pj) ** 2 for j in range(ma)) / ma  # 方差 i-ma+1,i+1
            dc[i]['std'] = dc[i]['var'] ** 0.5  # 标准差
            price = c - o
            dc[i]['mul'] = _yd = round(price / dc[i]['std'], 2)

            if _yd < -ydd and o > c and cc_k<ccc:  # 阴波做空
                st_k.append((_et,c))
                cc_k += 1
                cc_d = 0
                max_cc = cc_k if cc_k > max_cc else max_cc
                while st_d:
                    price = c - st_d.pop()[1]
                    ykAll.append(price)
                    zd_k += 1
                    if price>0:
                        yl_k += 1
            if _yd > ydd and o < c and cc_d<ccc:  # 阳波做多
                st_d.append((_et,c))
                cc_d += 1
                cc_k = 0
                max_cc = cc_d if cc_d > max_cc else max_cc
                while st_k:
                    price = st_k.pop()[1] - c
                    ykAll.append(price)
                    zd_d += 1
                    if price > 0:
                        yl_d += 1
            if st_k and c-o>qzz:
                while st_k:
                    price = st_k.pop()[1] - c
                    ykAll.append(price)
                    zd_d += 1
                    if price > 0:
                        yl_d += 1
            if st_d and o-c>qzz:
                while st_d:
                    price = c - st_d.pop()[1]
                    ykAll.append(price)
                    zd_k += 1
                    if price>0:
                        yl_k += 1

    yl = sum(ykAll)
    print(f'盈利：{yl}点  去除6个点差盈利：{yl-(zd_k+zd_d)*6}')
    print(f'最大亏损：{min(ykAll)}点  最大盈利：{max(ykAll)}点  最大持仓：{max_cc}手')
    print(f'持仓： 空：{st_k}  多：{st_d}')
    print(f'空单：{zd_k}  多单：{zd_d}')
    print(f'空单盈利：{yl_k}  多单盈利：{yl_d}')
    print(f'胜率{(yl_k+yl_d)/(zd_k+zd_d)*100}')
    return [yl, yl-(zd_k+zd_d)*6, (yl_k+yl_d)/(zd_k+zd_d)*100,min(ykAll),max(ykAll),zd_k,zd_d,yl_k,yl_d]


if __name__ == '__main__':
    tj(80,8,3)
    # res = [['盈利','去点差盈利','胜率','最大亏损','最大盈利','空单','多单','空单盈利','多单盈利','波幅','手数','异动倍数']]
    # for j in range(40,150,10):
    #     for i in range(2,12):
    #         y = 1.5
    #         while y < 6:
    #             v = tj(j,i,y)
    #             v.append(j)
    #             v.append(i)
    #             v.append(y)
    #             res.append(v)
    #             print(f'qzz: {j}, ccc: {i}, ydd: {y}')
    #             with open('vv.txt','a') as f:
    #                 f.write(','.join([str(vwri) for vwri in v]))
    #                 f.write('\n')
    #             y += 0.5
    # print(res)
    # import json
    # with open('resdd.txt','w') as f:
    #     f.write(json.dumps(res))
