# coding=utf-8
import datetime
import json
import os

import pandas as pd
import requests


def safe_byte2str(byteobj):
    if isinstance(byteobj, bytes):
        return byteobj.decode()
    assert isinstance(byteobj, str)
    return byteobj


def download_and_save_corplist(path):
    krx_corplist = download_krx_corplist()
    etf_corplist = download_etf_corplist()
    extra_corplist = {
        "삼성전자우": "005935",
    }

    corplist = {
        **krx_corplist,
        **etf_corplist,
        **extra_corplist,
    }

    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))

    with open(path, "w") as f:
        json.dump(corplist, f)


def download_krx_corplist():
    ret = {}

    code_df = pd.read_html(
        'http://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13',
        header=0)[0]
    code_df.종목코드 = code_df.종목코드.map('{:06d}'.format)
    code_df = code_df[['회사명', '종목코드']]
    for idx, each in code_df.회사명.items():
        ret[each] = code_df.종목코드[idx]

    return ret


def download_etf_corplist():
    ret = {}

    url = "http://kind.krx.co.kr/disclosure/disclosurebystocktype.do?method=searchDisclosureByStockTypeEtf"
    res = requests.get(url)
    for eachline in safe_byte2str(res.content).splitlines():
        eachline = eachline.strip()
        if "<option value=\"\">전체</option>" in eachline:
            continue

        if "<option value=" in eachline:
            eachline = eachline.replace("<option value=\"", '')
            corpcode_idx_ed = eachline.find("\">")
            corpcode = eachline[:corpcode_idx_ed]

            eachline = eachline[corpcode_idx_ed + len("\">"):]
            corpname = eachline.replace("</option>", '')

            corpcode = ''.join([each for each in corpcode if each.isdigit()])

            ret[corpname] = corpcode

    return ret


def get_corplist(force_refresh=False):
    filepath = os.path.join("data", "corplist.json")
    if force_refresh or (not os.path.exists(filepath)):
        download_and_save_corplist(filepath)

    with open(filepath, 'r') as f:
        return json.loads(f.read())


def get_corpcode_or_none(corpname):
    corplist = get_corplist()
    # print(corplist)
    for eachname, eachcode in corplist.items():
        # print(eachname, eachcode)
        if eachname.upper() == corpname.upper():
            return eachcode
    # exit(1)


def get_price_datalist(corpname, from_date, to_date):
    corpcode = get_corpcode_or_none(corpname)

    ret = {}

    page = 1
    while True:
        url = "https://finance.naver.com/item/sise_day.nhn?code={}&page={}".format(corpcode, page)
        for idx, each in pd.read_html(url)[0].dropna().iterrows():
            each_date = datetime.datetime.strptime(each.날짜, "%Y.%m.%d").date()
            if each_date < from_date:
                return ret

            if each_date > to_date:
                continue

            ret[each_date.strftime("%Y-%m-%d")] = each.종가
        page += 1


def get_price_data(corpcode, curr_date):
    if corpcode is None:
        return None

    page = 1
    while True:
        url = "https://finance.naver.com/item/sise_day.nhn?code={}&page={}".format(corpcode, page)
        for idx, each in pd.read_html(url)[0].dropna().iterrows():
            each_date = datetime.datetime.strptime(each.날짜, "%Y.%m.%d").date()
            if each_date <= curr_date:
                # print("each_date=[{}]".format(each_date))
                # print("curr_date=[{}]".format(curr_date))
                return each.종가

        page += 1


def str2date(strdate):
    return datetime.datetime.strptime(strdate, "%Y-%m-%d").date()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='get stockprice with corpname')
    parser.add_argument('corpname', type=str, help='corpname')
    parser.add_argument('--date', type=str, required=True, help='YYYY-MM-DD')
    parser.add_argument('--save-dir', type=str, required=True, help='YYYY-MM-DD')

    parsed = parser.parse_args()
    corpname = parsed.corpname
    save_dir = parsed.save_dir
    date_as_str = parsed.date

    date = str2date(date_as_str)

    corpcode = get_corpcode_or_none(corpname)
    value = get_price_data(corpcode, date)

    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    with open(os.path.join(save_dir, "{}-{}".format(corpcode, date_as_str.replace('-', ''))), 'w') as f:
        json.dump({"value": value}, f)

