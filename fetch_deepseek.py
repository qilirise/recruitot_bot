#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek API 余额监控
调用 https://api.deepseek.com/user/balance 获取余额，
生成 deepseek_usage.js 供网页进度条展示。

用法: python fetch_deepseek.py
"""
import json, os, sys, datetime, urllib.request, urllib.error

OUT_DIR = r'C:\Users\24345\Desktop\27秋招'
CONFIG_PATH = os.path.join(OUT_DIR, 'deepseek_config.json')
BALANCE_API = 'https://api.deepseek.com/user/balance'

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_config(cfg):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def fetch_balance(api_key):
    req = urllib.request.Request(BALANCE_API, headers={
        'Authorization': 'Bearer ' + api_key,
        'Accept': 'application/json',
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')[:300]
        return {'error': f'HTTP {e.code}: {body}'}
    except Exception as e:
        return {'error': str(e)}

def main():
    cfg = load_config()
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if not cfg.get('enabled') or not cfg.get('api_key'):
        payload = {
            'generatedAt': now,
            'configured': False,
            'error': '未配置 API Key（deepseek_config.json）',
            'total': None, 'remaining': None, 'used': None, 'percent': 0,
            'currency': 'CNY', 'is_available': False,
            'total_set': False,
        }
        write_output(payload)
        print('[warn] DeepSeek 未配置，生成空状态')
        return

    data = fetch_balance(cfg['api_key'])
    if 'error' in data:
        payload = {
            'generatedAt': now,
            'configured': True,
            'error': data['error'],
            'total': None, 'remaining': None, 'used': None, 'percent': 0,
            'currency': 'CNY', 'is_available': False,
            'total_set': bool(cfg.get('total_amount')),
        }
        write_output(payload)
        print(f'[error] 获取余额失败: {data["error"]}')
        return

    # 解析余额
    is_available = data.get('is_available', False)
    infos = data.get('balance_infos', [])
    remaining = None
    currency = 'CNY'
    if infos:
        first = infos[0]
        remaining = float(first.get('total_balance', 0))
        currency = first.get('currency', 'CNY')
        granted = float(first.get('granted_balance', 0))
        topped = float(first.get('topped_up_balance', 0))
        total_raw = granted + topped
    else:
        granted = topped = total_raw = 0

    # 总金额：优先手动配置，否则首次自动记录
    total_set = bool(cfg.get('total_amount'))
    if total_set:
        total = float(cfg['total_amount'])
    else:
        if cfg.get('_baseline_total') is None:
            cfg['_baseline_total'] = total_raw if total_raw > 0 else remaining
            save_config(cfg)
            total_set = True
        total = float(cfg.get('_baseline_total') or remaining)

    used = max(0.0, round(total - remaining, 4))
    percent = round(used / total * 100, 1) if total > 0 else 0

    payload = {
        'generatedAt': now,
        'configured': True,
        'error': '',
        'total': round(total, 2),
        'remaining': round(remaining, 2),
        'used': used,
        'percent': percent,
        'currency': currency,
        'is_available': is_available,
        'total_set': total_set,
        'granted': round(granted, 2),
        'topped_up': round(topped, 2),
    }
    write_output(payload)
    print(f'[ok] 总金额 ¥{total} | 剩余 ¥{remaining} | 已用 ¥{used} ({percent}%)')

def write_output(payload):
    js = 'window.DEEPSEEK_USAGE = ' + json.dumps(payload, ensure_ascii=False) + ';\n'
    with open(os.path.join(OUT_DIR, 'deepseek_usage.js'), 'w', encoding='utf-8') as f:
        f.write(js)
    print('[ok] deepseek_usage.js 已更新')

if __name__ == '__main__':
    main()
