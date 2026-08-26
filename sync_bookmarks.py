#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sync Edge bookmarks (找工作!/官网) -> applied_sites.js"""
import json, os, re, urllib.parse, datetime

OUT_DIR = r'C:\Users\24345\Desktop\27秋招'
BOOKMARK_PATHS = [
    r'C:\Users\24345\AppData\Local\Microsoft\Edge\User Data\Default\Bookmarks',
    r'C:\Users\24345\AppData\Local\Microsoft\Edge\User Data\Profile 1\Bookmarks',
]

def load_bookmarks(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)

def walk(node, folder_path, out):
    name = node.get('name', '')
    children = node.get('children', [])
    if node.get('type') == 'folder':
        new_path = (folder_path + '/' + name) if folder_path else name
        for ch in children:
            walk(ch, new_path, out)
    elif node.get('type') == 'url':
        out.append({'path': folder_path, 'name': name, 'url': node.get('url', '')})

def parse(u):
    if not u: return '', ''
    u = str(u).strip()
    u = re.sub(r'^[：:]\s*', '', u)
    try:
        p = urllib.parse.urlparse(u)
    except Exception:
        return '', ''
    host = p.netloc.lower().replace('www.', '')
    path = p.path.rstrip('/')
    return host, path

def mokahr_slug(u):
    host, path = parse(u)
    if 'mokahr.com' not in host:
        return None
    parts = path.split('/')
    for i, pt in enumerate(parts):
        if pt in ('campus_apply', 'campus-recruitment') and i + 1 < len(parts):
            return parts[i + 1].lower()
    return None

def reg_domain(host):
    parts = host.split('.')
    if len(parts) <= 2:
        return host
    if parts[-1] in ('cn', 'uk', 'jp', 'au', 'tw', 'hk') and len(parts) >= 3:
        return '.'.join(parts[-3:])
    return '.'.join(parts[-2:])

def clean_name(s):
    s = re.sub(r'[（(].*?[)）]', '', s)
    s = re.sub(r'[^\u4e00-\u9fa5A-Za-z0-9]', '', s)
    return s.lower()

def collect_official_bookmarks():
    """return bookmarks under any folder path ending with 官网"""
    bookmarks = []
    for p in BOOKMARK_PATHS:
        if not os.path.exists(p):
            continue
        try:
            data = load_bookmarks(p)
        except Exception:
            continue
        roots = data.get('roots', {})
        urls = []
        for root_name in ['bookmark_bar', 'other', 'synced']:
            root = roots.get(root_name)
            if root:
                walk(root, '', urls)
        for u in urls:
            parts = [x for x in u['path'].split('/') if x]
            if parts and parts[-1] == '官网':
                bookmarks.append(u)
    return bookmarks

def match_bookmarks(records):
    """records: list of {id, tab, v}. Return (applied_list, unmatched_list)."""
    bookmarks = collect_official_bookmarks()
    def company_urls(v):
        out = []
        for key in ['投递链接', '投递链接or推文', '官方公告']:
            val = v.get(key)
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, dict) and item.get('url'):
                        out.append(item['url'])
        return out

    matched, unmatched = [], []
    for bm in bookmarks:
        b_url = bm['url']
        b_host, b_path = parse(b_url)
        b_slug = mokahr_slug(b_url)
        b_name = clean_name(bm['name'])
        best, best_score = None, 0
        for rec in records:
            v = rec['v']
            cname = clean_name(v.get('公司名称', ''))
            score, matched_url = 0, None
            for cu in company_urls(v):
                cu_host, cu_path = parse(cu)
                cu_slug = mokahr_slug(cu)
                if cu_host == b_host and cu_path == b_path:
                    score = 100; matched_url = cu; break
                if b_slug and cu_slug and b_slug == cu_slug:
                    score = 95; matched_url = cu; break
                if cu_host == b_host and 'mokahr.com' not in b_host:
                    base = 80
                    b_first = b_path.split('/')[0].lower() if b_path else ''
                    c_first = cu_path.split('/')[0].lower() if cu_path else ''
                    if b_first and c_first and b_first == c_first:
                        base = 85
                    if base > score:
                        score = base; matched_url = cu
                elif cu_host != b_host and reg_domain(cu_host) == reg_domain(b_host):
                    if cname and (cname in b_name or b_name in cname or (len(cname) >= 2 and cname[:2] in b_name)):
                        if score < 75:
                            score = 75; matched_url = cu
            if score < 80 and cname and len(cname) >= 2:
                if cname in b_name or b_name in cname:
                    score = max(score, 70)
                    if not matched_url:
                        for cu in company_urls(v):
                            cu_host, _ = parse(cu)
                            if cu_host == b_host or (b_host.endswith(cu_host) or cu_host.endswith(b_host)):
                                matched_url = cu
                                break
            if score >= 60 and score == best_score and best is not None:
                cur_best_name = clean_name(best[0]['v'].get('公司名称', ''))
                if cname and (cname in b_name) and not (cur_best_name in b_name):
                    best = (rec, matched_url)
                elif '4399' in b_host and '4399' in cname and '4399' not in cur_best_name:
                    best = (rec, matched_url)
            if score > best_score:
                best_score = score
                best = (rec, matched_url)
        if best and best_score >= 70:
            matched.append({'bookmark': bm, 'record': best[0], 'matched_url': best[1], 'score': best_score})
        else:
            unmatched.append({'bookmark': bm})
    return matched, unmatched

def main():
    # load records from latest snapshot
    snap = os.path.join(OUT_DIR, '.tmp', 'latest_data.json')
    if not os.path.exists(snap):
        print('!! latest_data.json not found - run fetch_data.py first')
        return
    data = json.load(open(snap, encoding='utf-8'))
    records = []
    for t in data['tabs']:
        for r in t['records']:
            records.append({'id': r['id'], 'tab': t['title'], 'v': r['v']})

    matched, unmatched = match_bookmarks(records)
    applied = []
    for m in matched:
        applied.append({
            'id': m['record']['id'],
            'name': m['record']['v'].get('公司名称', ''),
            'tab': m['record']['tab'],
            'bookmark': m['bookmark']['name'],
            'url': m['bookmark']['url'],
            'score': m['score'],
        })
    # unique by company id
    by_id = {}
    for a in applied:
        cur = by_id.get(a['id'])
        if not cur or a['score'] > cur['score']:
            by_id[a['id']] = a
    applied = sorted(by_id.values(), key=lambda x: x['score'], reverse=True)

    payload = {
        'generatedAt': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'source': 'Edge书签「找工作!/官网」',
        'count': len(applied),
        'applied': applied,
        'unmatched': [{'name': u['bookmark']['name'], 'url': u['bookmark']['url']} for u in unmatched],
    }
    js = 'window.APPLIED_SITES = ' + json.dumps(payload, ensure_ascii=False) + ';\n'
    with open(os.path.join(OUT_DIR, 'applied_sites.js'), 'w', encoding='utf-8') as f:
        f.write(js)
    print(f'[ok] applied_sites.js: {len(applied)} matched, {len(unmatched)} unmatched')
    for a in applied:
        print(f'    {a["name"]} (s{a["score"]})')
    if unmatched:
        print('  unmatched:')
        for u in payload['unmatched']:
            print(f'    {u["name"]}  {u["url"][:60]}')

if __name__ == '__main__':
    main()
