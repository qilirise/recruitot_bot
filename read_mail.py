#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
秋招邮件自动识别器
通过 IMAP 读取 Outlook 邮箱中的秋招邮件，
识别测评/面试邀请，匹配公司，生成 mail_events.js 供网页展示。

用法:
  python read_mail.py          # 正常读取（需 mail_config.json 已配置）
  python read_mail.py --demo   # 用内置示例邮件测试识别逻辑（无需邮箱）
"""
import json, os, re, sys, imaplib, email, datetime
from email.header import decode_header
from email.utils import parsedate_to_datetime

OUT_DIR = r'C:\Users\24345\Desktop\27秋招'
CONFIG_PATH = os.path.join(OUT_DIR, 'mail_config.json')

# ============ 配置 ============
def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, encoding='utf-8') as f:
            return json.load(f)
    return {}

# ============ 邮件解析 ============
def decode_mime(s):
    """decode =?utf-8?b?...?= 及类似编码"""
    if not s:
        return ''
    try:
        parts = decode_header(s)
        out = []
        for data, charset in parts:
            if isinstance(data, bytes):
                out.append(data.decode(charset or 'utf-8', errors='replace'))
            else:
                out.append(data)
        return ''.join(out)
    except Exception:
        return str(s)

def get_body(msg):
    """提取邮件正文纯文本"""
    parts = []
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == 'text/plain':
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        cs = part.get_content_charset() or 'utf-8'
                        parts.append(payload.decode(cs, errors='replace'))
                except Exception:
                    pass
        if not parts:  # 只有 html
            for part in msg.walk():
                if part.get_content_type() == 'text/html':
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            cs = part.get_content_charset() or 'utf-8'
                            html = payload.decode(cs, errors='replace')
                            text = re.sub(r'<[^>]+>', ' ', html)
                            text = re.sub(r'\s+', ' ', text)
                            parts.append(text)
                    except Exception:
                        pass
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                cs = msg.get_content_charset() or 'utf-8'
                parts.append(payload.decode(cs, errors='replace'))
        except Exception:
            parts.append(str(msg.get_payload()))
    return '\n'.join(parts)

def parse_mail(msg):
    """返回 {subject, from, from_domain, received_at, body}"""
    subj = decode_mime(msg.get('Subject', ''))
    frm = decode_mime(msg.get('From', ''))
    m = re.search(r'[\w.\-]+@[\w.\-]+', frm)
    from_addr = m.group(0) if m else frm
    domain = from_addr.split('@')[-1].lower() if '@' in from_addr else ''
    date_str = msg.get('Date', '')
    received = None
    try:
        received = parsedate_to_datetime(date_str).strftime('%Y-%m-%d %H:%M')
    except Exception:
        received = ''
    return {'subject': subj, 'from': frm, 'from_addr': from_addr, 'from_domain': domain,
            'received_at': received, 'body': get_body(msg)}

# ============ 公司匹配 ============
def clean_name(s):
    s = re.sub(r'[（(].*?[)）]', '', str(s))
    s = re.sub(r'[^\u4e00-\u9fa5A-Za-z0-9]', '', s)
    return s.lower()

def load_records():
    snap = os.path.join(OUT_DIR, '.tmp', 'latest_data.json')
    if not os.path.exists(snap):
        return []
    data = json.load(open(snap, encoding='utf-8'))
    records = []
    for t in data['tabs']:
        for r in t['records']:
            records.append({'id': r['id'], 'tab': t['title'], 'name': r['v'].get('公司名称', ''), 'v': r['v']})
    return records

def match_company(text, records):
    """在 text 中查找最匹配的公司。返回 (record, confidence) 或 (None, 0)"""
    if not records:
        return None, 0
    t_clean = clean_name(text)
    best, best_conf = None, 0
    for rec in records:
        cname = rec['name']
        cc = clean_name(cname)
        if not cc or len(cc) < 2:
            continue
        if cc in t_clean:
            conf = 0.95 if len(cc) >= 4 else 0.8
            if conf > best_conf:
                best, best_conf = rec, conf
        elif len(cc) >= 4 and cc[:4] in t_clean:
            if 0.7 > best_conf:
                best, best_conf = rec, 0.7
    # 用发件人域名辅助：域名包含公司拼音/缩写
    return best, best_conf

def domain_company_match(domain, records):
    """发件人域名匹配公司（如 mokahr.com 需靠主题；jobs.bytedance.com 直接匹配）"""
    d = domain.replace('www.', '').lower()
    for rec in records:
        name = clean_name(rec['name'])
        # bytedance -> 字节跳动
        if name and (name in d or d in name):
            return rec, 0.75
    return None, 0

# ============ 信息提取 ============
def extract_links(text):
    return re.findall(r'https?://[^\s<>"\'，。；）)]+', text)

def extract_date(text):
    """提取日期：2026-08-27 / 2026年8月27日 / 8月27日 / 8/27"""
    now = datetime.date.today()
    pats = [
        (r'(20\d{2})[-/年.](\d{1,2})[-/月.](\d{1,2})', lambda y, m, d: f'{y}-{int(m):02d}-{int(d):02d}'),
        (r'(\d{1,2})[-/月.](\d{1,2})日?', lambda m, d: f'{now.year}-{int(m):02d}-{int(d):02d}'),
    ]
    for pat, fmt in pats:
        m = re.search(pat, text)
        if m:
            groups = m.groups()
            try:
                return fmt(*groups)
            except Exception:
                pass
    return ''

def extract_time(text):
    m = re.search(r'(\d{1,2})[:：](\d{2})', text)
    if m:
        return f'{int(m.group(1)):02d}:{m.group(2)}'
    return ''

def extract_deadline_days(text):
    """提取 '3日内完成' '5天内' 等测评时效"""
    m = re.search(r'(\d{1,3})\s*[天日内]', text)
    if m:
        return int(m.group(1))
    return None

# ============ 分类识别 ============
def classify_and_extract(mail, cfg):
    """返回 event dict 或 None"""
    subj = mail['subject']
    body = mail['body']
    text = subj + '\n' + body
    text_low = text.lower()
    kw_assess = cfg.get('keywords_assess', [])
    kw_itv = cfg.get('keywords_interview', [])

    is_assess = any(k.lower() in text_low for k in kw_assess)
    is_itv = any(k.lower() in text_low for k in kw_itv)

    if not is_assess and not is_itv:
        return None

    links = extract_links(text)
    date = extract_date(text)
    time = extract_time(text)
    days = extract_deadline_days(text)

    if is_assess:
        etype = 'assess'
        deadline = date
        if not deadline and days:
            dl = datetime.date.today() + datetime.timedelta(days=days)
            deadline = dl.isoformat()
        link = links[0] if links else ''
    else:
        etype = 'interview'
        deadline = date  # 面试日期
        link = links[0] if links else ''
        # 面试阶段判断
        stage = 0
        for i, k in enumerate(['一面', '二面', '三面', '群面', '终面']):
            if k in text:
                stage = i + 1 if i < 3 else (4 if k == '群面' else 5)
                break

    return {
        'subject': subj[:120],
        'from': mail['from'][:80],
        'from_domain': mail['from_domain'],
        'received_at': mail['received_at'],
        'type': etype,
        'link': link,
        'date': deadline,       # 测评截止日期 / 面试日期
        'time': time,           # 面试时间
        'deadline_days': days,
        'body_excerpt': re.sub(r'\s+', ' ', body)[:300],
    }

# ============ 主流程 ============
def fetch_mails(cfg):
    """连接 IMAP 读取邮件，返回 mail dict 列表"""
    host = cfg.get('imap_host', 'imap-mail.outlook.com')
    port = int(cfg.get('imap_port', 993))
    user = cfg.get('email', '')
    pwd = cfg.get('app_password', '')
    folder = cfg.get('folder', 'INBOX')
    max_mails = int(cfg.get('max_emails', 100))
    unread_only = cfg.get('check_unread_only', True)

    M = imaplib.IMAP4_SSL(host, port)
    try:
        M.login(user, pwd)
    except Exception as e:
        print(f'[error] IMAP 登录失败: {e}')
        M.logout()
        return None
    # 发送 ID 命令（RFC2971）：网易 163/126/QQ 等要求客户端标识，否则判定不安全登录
    try:
        imaplib.Commands['ID'] = ('AUTH', 'SELECTED')
        M._simple_command('ID', '("name" "qiuzhao-mail-reader" "version" "1.0" "vendor" "hermes")')
        M._untagged_response('ID', 'ID', 'OK')
    except Exception as e:
        print(f'[warn] ID 命令发送失败（不影响多数邮箱）: {e}')
    try:
        status, _ = M.select(folder)
        if status != 'OK':
            print('[error] 无法打开收件箱')
            return None
        if unread_only:
            status, data = M.search(None, 'UNSEEN')
        else:
            status, data = M.search(None, 'ALL')
        if status != 'OK':
            return []
        ids = data[0].split()
        # 兼容已读转发邮件：如果未读为 0 但收件箱有邮件，退回最近 N 封全部扫描
        if unread_only and not ids:
            status, data = M.search(None, 'ALL')
            if status == 'OK':
                ids = data[0].split()
        ids = ids[-max_mails:]  # 最近 N 封
        mails = []
        for num in ids:
            try:
                status, msg_data = M.fetch(num, '(RFC822)')
                if status != 'OK' or not msg_data or not msg_data[0]:
                    continue
                msg = email.message_from_bytes(msg_data[0][1])
                mails.append(parse_mail(msg))
            except Exception:
                continue
        return mails
    finally:
        M.logout()

def process_mails(mails, records, cfg):
    events = []
    for mail in mails:
        try:
            ev = classify_and_extract(mail, cfg)
        except Exception:
            continue
        if not ev:
            continue
        # 公司匹配：正文+主题
        rec, conf = match_company(mail['subject'] + ' ' + mail['body'], records)
        if not rec and mail['from_domain']:
            rec, dconf = domain_company_match(mail['from_domain'], records)
            if dconf > conf:
                conf = dconf
        ev['companyGuess'] = rec['name'] if rec else ''
        ev['companyId'] = rec['id'] if rec else ''
        ev['confidence'] = round(conf, 2)
        # stable event id
        import hashlib
        ev['_id'] = hashlib.md5((ev['subject'] + ev['from'] + ev['received_at']).encode('utf-8')).hexdigest()[:12]
        events.append(ev)
    return events

def write_output(events, cfg, last_check):
    payload = {
        'generatedAt': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'configured': bool(cfg.get('enabled') and cfg.get('email')),
        'lastCheck': last_check,
        'eventCount': len(events),
        'events': events,
    }
    js = 'window.MAIL_EVENTS = ' + json.dumps(payload, ensure_ascii=False) + ';\n'
    with open(os.path.join(OUT_DIR, 'mail_events.js'), 'w', encoding='utf-8') as f:
        f.write(js)
    print(f'[ok] mail_events.js: {len(events)} events')

# ============ 演示模式 ============
DEMO_MAILS = [
    {
        'subject': '【字节跳动】2027校园招聘 在线测评通知',
        'from': 'Bytedance Campus <no-reply@bytedance.com>',
        'from_addr': 'no-reply@bytedance.com', 'from_domain': 'bytedance.com',
        'received_at': '2026-08-26 10:00',
        'body': '亲爱的同学：感谢投递字节跳动校园招聘。请于3日内完成在线测评。\n测评链接：https://exam.bytedance.com/assessment/abc123\n请在2026-08-28前完成。',
    },
    {
        'subject': '小米集团2027届校招 一面面试邀请',
        'from': 'Xiaomi Recruit <recruit@xiaomi.com>',
        'from_addr': 'recruit@xiaomi.com', 'from_domain': 'xiaomi.com',
        'received_at': '2026-08-26 09:30',
        'body': '恭喜通过简历筛选！请参加一面面试：\n时间：2026年8月29日 14:30\n形式：视频面试\n会议链接：https://meeting.xiaomi.com/join/xyz789',
    },
    {
        'subject': '腾讯 2027 校招笔试邀请',
        'from': 'Tencent HR <hr@tencent.com>',
        'from_addr': 'hr@tencent.com', 'from_domain': 'tencent.com',
        'received_at': '2026-08-26 08:00',
        'body': '腾讯校招笔试：请在 5 天内完成笔试，链接 https://exam.tencent.com/test/ttt111',
    },
    {
        'subject': 'XD Inc. 2027 秋招 在线测评邀请',
        'from': 'XD Inc. HR <hr@xd.cn>',
        'from_addr': 'hr@xd.cn', 'from_domain': 'xd.cn',
        'received_at': '2026-08-26 07:30',
        'body': '感谢你投递 XD Inc.（心动网络）。请完成在线测评：\n测评链接：https://exam.xd.cn/assessment/xyz888\n请在 7 天内完成。',
    },
]

def run_demo(cfg, records):
    mails = DEMO_MAILS
    events = process_mails(mails, records, cfg)
    for ev in events:
        print(f"  [{ev['type']}] {ev['companyGuess'] or '?'} conf={ev['confidence']} | {ev['subject'][:40]} | link={ev['link'][:40]} | date={ev['date']} time={ev['time']}")
    write_output(events, cfg, 'demo')

def main():
    cfg = load_config()
    records = load_records()
    if '--demo' in sys.argv:
        print('=== DEMO 模式（内置示例邮件） ===')
        run_demo(cfg, records)
        return
    if not cfg.get('enabled') or not cfg.get('email'):
        print('[warn] 邮箱未配置（mail_config.json enabled=false），生成空事件文件。')
        write_output([], cfg, 'not-configured')
        print('配置方法：在 mail_config.json 填入 email / app_password 并将 enabled 设为 true')
        return
    mails = fetch_mails(cfg)
    if mails is None:
        write_output([], cfg, 'login-failed')
        return
    events = process_mails(mails, records, cfg)
    print(f'[info] 读取 {len(mails)} 封邮件，识别 {len(events)} 条事件')
    for ev in events:
        print(f"  [{ev['type']}] {ev['companyGuess'] or '?'} conf={ev['confidence']} | {ev['subject'][:40]}")
    write_output(events, cfg, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

if __name__ == '__main__':
    main()
