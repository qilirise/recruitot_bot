#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
27秋招日报数据生成器
抓取腾讯文档智能表格 -> 生成 data.js（网页数据文件）
用法: python fetch_data.py
"""
import json, re, html, sys, os, datetime, urllib.request, urllib.parse

DOC_ID = 'DTkRMUVhoUWJXZEhJ'
PAD_ID = 'NDLQXhQbWdHI'
BASE = 'https://docs.qq.com/dop-api/opendoc'
# 输出目录：优先环境变量 QIUZHAO_OUT_DIR（GitHub Actions 使用），否则脚本所在目录
OUT_DIR = os.environ.get('QIUZHAO_OUT_DIR') or os.path.dirname(os.path.abspath(__file__))

HDRS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
    'Referer': f'https://docs.qq.com/smartsheet/{DOC_ID}',
}

def fetch_opendoc(tab, startrow=0, endrow=5000):
    params = {
        'tab': tab, 'id': DOC_ID, 'normal': '1', 'outformat': '1',
        'startrow': str(startrow), 'endrow': str(endrow),
        'wb': '1', 'callback': 'clientVarsCallback',
    }
    url = BASE + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HDRS)
    with urllib.request.urlopen(req, timeout=90) as r:
        raw = r.read().decode('utf-8-sig')
    m = re.match(r'^clientVarsCallback\((.*)\)\s*;?\s*$', raw, re.S)
    inner = m.group(1) if m else raw
    s1 = json.loads(inner)
    s2 = html.unescape(s1)
    return json.loads(s2)

def extract_smartsheet(data):
    cc = data['clientVars']['collab_client_vars']
    iat = cc['initialAttributedText']
    for entry in iat.get('text', []):
        ss = entry.get('smartsheet')
        if ss:
            return json.loads(ss)
    return None

def parse_fields(meta_elem):
    c = meta_elem['c']
    f3 = c.get('3', {})
    raw_fields = f3.get('3', {})
    fields = {}
    for fid, finfo in raw_fields.items():
        name = finfo.get('30', '')
        ftype = finfo.get('31', 1)
        opts = {}
        for okey in ('17', '9'):
            od = finfo.get(okey)
            if isinstance(od, dict):
                olist = od.get('3') or od.get('2')
                if isinstance(olist, list):
                    for o in olist:
                        if isinstance(o, dict) and '1' in o and '2' in o:
                            opts[o['1']] = o['2']
        fields[fid] = {'name': name, 'type': ftype, 'options': opts}
    return fields

def parse_records(rec_elem, fields):
    c = rec_elem['c']
    recs = c.get('2', {}).get('1', {})
    out = []
    for rid, rv in recs.items():
        vals = {}
        for fid, fv in rv.get('1', {}).items():
            fmeta = fields.get(fid)
            fname = fmeta['name'] if fmeta else fid
            ftype = fmeta['type'] if fmeta else 1
            opts = fmeta['options'] if fmeta else {}
            if '1' in fv:
                items = fv['1']
                text = ' '.join(it.get('2', '') for it in items if isinstance(it, dict))
                vals[fname] = text
            elif '4' in fv:
                ts = fv['4']
                try:
                    dt = datetime.datetime.fromtimestamp(int(ts)/1000)
                    vals[fname] = dt.strftime('%Y-%m-%d')
                except Exception:
                    vals[fname] = str(ts)
            elif '8' in fv:
                items = fv['8']
                links = []
                for it in items:
                    if isinstance(it, dict):
                        links.append({'text': it.get('2', '') or it.get('3', ''), 'url': it.get('3', '')})
                vals[fname] = links
            elif '9' in fv:
                oids = fv['9']
                if isinstance(oids, list):
                    vals[fname] = '、'.join(opts.get(o, o) for o in oids)
                else:
                    vals[fname] = str(oids)
            elif '17' in fv:
                oids = fv['17']
                if isinstance(oids, list):
                    vals[fname] = '、'.join(opts.get(o, o) for o in oids)
                else:
                    vals[fname] = str(oids)
            else:
                vals[fname] = json.dumps(fv, ensure_ascii=False)
        out.append({'id': rid, 'v': vals})
    return out

def process_tab(tab, title):
    print(f'[fetch] tab={tab} ({title}) ...')
    data = fetch_opendoc(tab)
    ss = extract_smartsheet(data)
    if not ss:
        print(f'  !! no data for {tab}')
        return None
    inner = ss[0]
    fields = parse_fields(inner[0])
    records = parse_records(inner[1], fields)
    print(f'  fields({len(fields)}): {[f["name"] for f in fields.values()]}')
    print(f'  records: {len(records)}')
    return {'tab': tab, 'title': title, 'fields': fields, 'records': records}

def main():
    tabs = [
        ('tvVDZj', '27秋招每日更新'),
        ('tTNjGc', '27届内推汇总'),
    ]
    result = {'generatedAt': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
              'docTitle': '27届秋招信息汇总', 'tabs': []}
    for tab, title in tabs:
        try:
            t = process_tab(tab, title)
            if t:
                result['tabs'].append(t)
        except Exception as e:
            print(f'  !! ERROR: {e}')
    if not result['tabs']:
        print('FATAL: no data fetched')
        sys.exit(1)
    # write data.js
    js = 'window.QIUZHAO_DATA = ' + json.dumps(result, ensure_ascii=False) + ';\n'
    path = os.path.join(OUT_DIR, 'data.js')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(js)
    print(f'[ok] wrote {path} ({len(js)} bytes)')
    # also write a JSON snapshot for debugging
    with open(os.path.join(OUT_DIR, '.tmp', 'latest_data.json'), 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print('[ok] snapshot saved')

    # generate human-readable daily report (markdown)
    write_daily_report(result)

    # sync DeepSeek API balance -> deepseek_usage.js
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location('fetch_deepseek', os.path.join(OUT_DIR, 'fetch_deepseek.py'))
        fd = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fd)
        fd.main()
    except Exception as e:
        print(f'[warn] deepseek sync skipped: {e}')

def write_daily_report(data):
    today = datetime.date.today().isoformat()
    d7 = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    daily = None
    for t in data['tabs']:
        if t['tab'] == 'tvVDZj':
            daily = t
            break
    if not daily:
        return
    lines = []
    lines.append(f'# 🚀 27届秋招日报 · {today}')
    lines.append('')
    lines.append(f'> 数据来源：27届秋招信息汇总（腾讯文档）· 生成时间 {data["generatedAt"]} · 共 {len(daily["records"])} 家公司')
    lines.append('')
    today_recs = [r for r in daily['records'] if r['v'].get('更新日期') == today]
    week_recs = [r for r in daily['records'] if d7 <= (r['v'].get('更新日期') or '') <= today]
    lines.append(f'## 🆕 今日新开（{len(today_recs)} 家）')
    lines.append('')
    if not today_recs:
        lines.append('今日暂无新开公司。')
        lines.append('')
    for r in sorted(today_recs, key=lambda x: x['v'].get('公司名称', '')):
        v = r['v']
        links = v.get('投递链接') or []
        url = links[0]['url'] if links else ''
        pub = v.get('官方公告') or []
        pub_url = pub[0]['url'] if pub else ''
        lines.append(f'### {v.get("公司名称", "")} · {v.get("批次", "")}')
        lines.append(f'- 🎯 岗位：{v.get("招聘岗位", "—")}')
        lines.append(f'- 📍 地点：{v.get("工作地点", "—")}　🏭 行业：{v.get("行业", "—")}')
        lines.append(f'- ⏰ 截止：{v.get("招聘截止日期", "—")}')
        if v.get('内推码'):
            lines.append(f'- 🎁 内推码：{v["内推码"]}')
        if url:
            lines.append(f'- 🔗 投递：{url}')
        if pub_url:
            lines.append(f'- 📄 公告：{pub_url}')
        lines.append('')
    lines.append(f'## 📅 近7天新开（{len(week_recs)} 家）')
    lines.append('')
    by_date = {}
    for r in week_recs:
        by_date.setdefault(r['v'].get('更新日期', ''), []).append(r)
    for d in sorted(by_date.keys(), reverse=True):
        lines.append(f'### {d}（{len(by_date[d])} 家）')
        for r in sorted(by_date[d], key=lambda x: x['v'].get('公司名称', '')):
            v = r['v']
            links = v.get('投递链接') or []
            url = links[0]['url'] if links else ''
            code = f'　🎁 {v["内推码"]}' if v.get('内推码') else ''
            lines.append(f'- **{v.get("公司名称", "")}**（{v.get("批次", "")}）：{v.get("招聘岗位", "")[:50]}{code}')
            if url:
                lines.append(f'  - 🔗 {url}')
        lines.append('')
    report_path = os.path.join(OUT_DIR, '秋招日报.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f'[ok] wrote {report_path} ({len(lines)} lines)')

if __name__ == '__main__':
    main()
