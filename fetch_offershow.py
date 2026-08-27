#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OfferShow 热门薪资抓取（公开接口，无需登录）
接口: POST https://offershow.cn/offershow/uuid/get_top_salary_web
参数: {hot_type, offset, limit}  hot_type=1/2/3 为不同热门分类
输出: offershow_data.js (window.OFFERSHOW_DATA)
注: 公开接口低频访问（3次/30分钟），仅个人求职参考展示
"""
import json, os, sys, time, urllib.request, urllib.parse

OUT_DIR = os.environ.get('QIUZHAO_OUT_DIR', os.path.dirname(os.path.abspath(__file__)))
API = 'https://offershow.cn/offershow/uuid/get_top_salary_web'
HDRS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
    'Referer': 'https://offershow.cn/',
    'appVersion': '2',
    'Content-Type': 'application/x-www-form-urlencoded',
}

def fetch_top(hot_type, offset, limit, retries=3):
    body = urllib.parse.urlencode({'hot_type': hot_type, 'offset': offset, 'limit': limit}).encode()
    for i in range(retries):
        try:
            req = urllib.request.Request(API, data=body, headers=HDRS)
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode('utf-8', errors='replace'))
        except Exception as e:
            if i == retries - 1:
                print(f'fetch_top hot_type={hot_type} 失败: {e}', file=sys.stderr)
                return None
            time.sleep(2)
    return None

def main():
    items = []
    for ht in (1, 2, 3):
        d = fetch_top(ht, 0, 50)
        if not d or d.get('result') != 1:
            continue
        lst = (d.get('data') or {}).get('list') or []
        for it in lst:
            it['hot_type'] = ht
            items.append(it)
    # 按 id 去重
    seen, uniq = set(), []
    for it in items:
        if it.get('id') and it['id'] not in seen:
            seen.add(it['id'])
            uniq.append(it)
    out = {
        'generatedAt': time.strftime('%Y-%m-%d %H:%M:%S'),
        'total': len(uniq),
        'source': 'offershow.cn',
        'list': uniq,
    }
    with open(os.path.join(OUT_DIR, 'offershow_data.js'), 'w', encoding='utf-8') as f:
        f.write('window.OFFERSHOW_DATA = ' + json.dumps(out, ensure_ascii=False) + ';\n')
    print(f'OK offershow items: {len(uniq)} generatedAt={out["generatedAt"]}')

if __name__ == '__main__':
    main()
