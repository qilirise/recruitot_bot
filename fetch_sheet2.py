#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据源2抓取：2027届校招信息汇总表（腾讯文档普通表格 /sheet/）
接口（匿名）: https://docs.qq.com/dop-api/get/sheet?padId=300000000$ACqttWrwdxqJ&subId=986nx3
数据 = base64(zlib(protobuf))，文本 cell = 0x0a <len> 0x0a <len> <utf8>（外层 len = l1 + varint字节 + 1）
输出: data_source2.js (window.SOURCE2_DATA = {generatedAt, count, records:[...]})
"""
import os, re, sys, json, time, zlib, base64
import urllib.request

PAD = '300000000%24ACqttWrwdxqJ'
SUBID = '986nx3'
DOC_URL = 'https://docs.qq.com/sheet/DQUNxdHRXcndkeHFK?tab=986nx3'
BASE = 'https://docs.qq.com/dop-api/get/sheet?padId=%s&subId=%s&startrow=0&endrow=4443&outformat=1&normal=1&nowb=1' % (PAD, SUBID)

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------- 分类词典（与 .tmp/sheet_rows.py 同源精简） ----------
DATE_RE = re.compile(r'^\d{4}[./]\d{1,2}[./]\d{1,2}')
STATUS_W = ['招聘中', '已截止', '暂停', '暂缓', '停止', '结束', '进行中', '未开始', '网申']
NATURE_W = ['民营企业', '国有企业', '中央企业', '央国企', '央企', '国企', '外企', '合资企业',
            '上市公司', '事业单位', '民营', '国有', '合资', '私营', '民企', '集体', '股份制']
OBJ_W = ['本科', '硕士', '博士', '大专', '留学生', '全日制']
CITY_W = ['北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '南京', '苏州', '天津', '西安', '合肥',
          '长沙', '重庆', '青岛', '大连', '厦门', '福州', '郑州', '济南', '无锡', '宁波', '东莞', '佛山',
          '珠海', '嘉兴', '洛阳', '烟台', '莱阳', '格尔木', '永康', '武义', '蓬溪', '黄石', '常州', '淮安',
          '横琴', '金华', '沈阳', '长春', '潍坊', '临沂', '徐州', '温州', '绍兴', '南通', '泉州', '南昌',
          '贵阳', '昆明', '兰州', '太原', '石家庄', '南宁', '呼和浩特', '哈尔滨', '海外', '全国',
          '凯里', '萍乡', '新加坡', '防城港', '漳州', '威海', '湘潭', '泰州', '江门', '绵阳', '横峰', '弋阳',
          '赣州', '莱芜', '枣庄', '济宁', '菏泽', '义乌', '余姚', '慈溪', '昆山', '常熟', '张家港', '江阴',
          '宜兴', '太仓', '海宁', '桐乡', '德清', '安吉', '临海', '温岭', '乐清', '瑞安', '湛江', '惠州',
          '中山', '肇庆', '汕头', '揭阳', '柳州', '桂林', '北海', '三亚', '海口', '西宁', '银川',
          '乌鲁木齐', '拉萨', '吉林', '南阳', '新乡', '安阳', '襄阳', '宜昌', '荆州', '株洲',
          '芜湖', '马鞍山', '安庆', '阜阳', '滁州', '连云港', '盐城', '扬州', '镇江', '泰兴',
          '莆田', '龙岩', '三明', '南平', '宁德', '台州', '湖州', '丽水', '衢州',
          '舟山', '诸暨', '上虞', '嵊州', '永嘉', '平阳', '苍南', '云南', '贵州', '陕西', '山西',
          '甘肃', '青海', '内蒙古', '黑龙江', '福建', '广西', '新疆', '宁夏', '海南', '四川', '重庆']
POST_TAIL = ['工程师', '管培生', '培训生', '专员', '助理', '顾问', '技师', '设计师', '造价师',
             '会计师', '经理', '主管', '督导', '店长', '教员', '讲师', '研究员', '技术员', '分析师',
             '采购员', '销售员', '操作员', '作业员', '储备干部', '管理培训生']
ORG_TAIL = ['科技', '公司', '集团', '电子', '通信', '软件', '网络', '技术', '信息', '股份', '大学',
            '学院', '研究院', '研究所', '设计院', '有限', '控股', '银行', '证券', '保险', '基金',
            '汽车', '电力', '能源', '光电', '材料', '生物', '医药', '环境', '航空', '工业', '建筑',
            '机器人', '半导体', '数据', '数字', '智能', '激光', '矿业', '铁路', '工程局',
            '规划院', '广电', '传媒', '实业', '发展', '中心', '总行', '分行', '事务所', '联盟']


def fetch():
    req = urllib.request.Request(BASE, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                                                'Referer': DOC_URL})
    d = json.loads(urllib.request.urlopen(req, timeout=60).read().decode('utf-8', errors='replace'))
    return d


def extract_text_cells(raw, start):
    cells = []
    i, end = start, len(raw)
    while i < end:
        if raw[i] == 0x0a:
            l2, adv = 0, 0
            for j in range(5):
                if i + 1 + j >= end:
                    break
                v = raw[i + 1 + j]
                l2 |= (v & 0x7f) << (7 * j)
                adv = j + 1
                if not (v & 0x80):
                    break
            inner = i + 1 + adv
            if inner + l2 <= end and l2 > 0 and raw[inner] == 0x0a:
                l1, adv2 = 0, 0
                for j in range(5):
                    if inner + 1 + j >= end:
                        break
                    v = raw[inner + 1 + j]
                    l1 |= (v & 0x7f) << (7 * j)
                    adv2 = j + 1
                    if not (v & 0x80):
                        break
                ts = inner + 1 + adv2
                if ts + l1 <= end and l2 == l1 + adv2 + 1:
                    try:
                        t = raw[ts:ts + l1].decode('utf-8')
                        if t:
                            cells.append(t)
                    except Exception:
                        pass
                    i = ts + l1
                    continue
            i = inner + l2 if inner + l2 <= end else i + 1
        else:
            i += 1
    return cells


def is_org_name(t):
    if len(t) > 20:
        return False
    return any(t.endswith(o) for o in ORG_TAIL) or '有限公司' in t


def classify(cell):
    t = cell.strip()
    if not t:
        return 'empty'
    if t == '\\' or t.startswith('http'):
        return 'url'
    if DATE_RE.match(t):
        return 'date'
    if re.match(r'^\d+$', t):
        return 'num'
    if t in STATUS_W or (any(s in t for s in STATUS_W) and len(t) <= 8):
        return 'status'
    if '招满即止' in t or t == '尽快' or '长期' in t or t == '随时':
        return 'deadline'
    if len(t) <= 8 and any(t.startswith(b) for b in ['秋招', '春招', '暑期', '日常', '提前批', '补录', '校招']):
        return 'batch'
    if re.match(r'^[（(]?\d{4}[）)]?$', t):
        return 'batch'
    if any(n in t for n in NATURE_W) and len(t) <= 16:
        return 'nature'
    if any(o in t for o in OBJ_W) or re.match(r'^20\d{2}/\d{4}届', t) or re.match(r'^\d{2,4}届', t):
        if len(t) <= 24 and not any(p in t for p in POST_TAIL):
            return 'obj'
    if len(t) <= 50 and re.match(r'^[\u4e00-\u9fff ]+$', t):
        hits = [c for c in CITY_W if c in t]
        if len(hits) >= 2 or (t in CITY_W) or (' ' in t and len(hits) >= 1 and not any(p in t for p in POST_TAIL)):
            return 'loc'
    if any(p in t for p in POST_TAIL) and 4 <= len(t) <= 60 and not is_org_name(t):
        return 'post'
    if '/' in t and len(t) > 6:
        return 'industry'
    if len(t) >= 14:
        return 'post'
    return 'name'


def norm_date(s):
    """2026.09.08 / 2026/09/08 -> 2026-09-08；招满即止 等原样"""
    m = re.match(r'^(\d{4})[./](\d{1,2})[./](\d{1,2})', s.strip())
    if m:
        return '%s-%02d-%02d' % (m.group(1), int(m.group(2)), int(m.group(3)))
    return s.strip()


def build_records(data_cells):
    """行切分 + 类型归列 -> 标准记录列表"""
    # 行切分
    rows = []
    cur = []
    prev_ty = None
    END_TYPES = {'status', 'deadline', 'url', 'date'}
    for c in data_cells:
        ty = classify(c)
        if ty == 'name' and (len(cur) >= 2 or prev_ty in END_TYPES):
            rows.append(cur)
            cur = [c]
        else:
            cur.append(c)
        prev_ty = ty
    if cur:
        rows.append(cur)
    # 归列
    records = []
    for cells in rows:
        if not cells or len(cells) == 0:
            continue
        name = cells[0].strip()
        if not name or len(name) > 30:
            continue
        rec = {'公司名称': name}
        posts, locs, dates, urls, extras = [], [], [], [], []
        for c in cells[1:]:
            ty = classify(c)
            if ty == 'industry':
                if not rec.get('行业'):
                    rec['行业'] = c
                else:
                    posts.append(c)
            elif ty == 'nature':
                if not rec.get('企业性质'):
                    rec['企业性质'] = c
            elif ty == 'batch':
                if not rec.get('批次'):
                    rec['批次'] = c
            elif ty == 'post':
                posts.append(c)
            elif ty == 'loc':
                locs.append(c)
            elif ty == 'obj':
                if not rec.get('招聘对象'):
                    rec['招聘对象'] = c
            elif ty == 'date':
                dates.append(c)
            elif ty == 'deadline':
                if not rec.get('截止时间'):
                    rec['截止时间'] = c
            elif ty == 'status':
                if not rec.get('网申状态'):
                    rec['网申状态'] = c
            elif ty == 'url':
                urls.append(c)
            elif ty == 'num':
                if not rec.get('序号'):
                    rec['序号'] = c
            else:
                extras.append(c)
        if posts:
            rec['招聘岗位'] = ' '.join(posts)
        if locs:
            rec['工作地点'] = ' '.join(locs)
        if dates:
            rec['更新时间'] = dates[0]
            if len(dates) > 1:
                rec['截止时间'] = dates[1]
        if urls:
            rec['官方公告'] = urls[0]
            if len(urls) > 1:
                rec['投递方式'] = urls[1]
        if extras:
            rec['内推码/备注'] = ' '.join(str(e) for e in extras if str(e).strip())
        # 日期归一
        if rec.get('更新时间'):
            rec['更新时间'] = norm_date(rec['更新时间'])
        if rec.get('截止时间'):
            rec['截止时间'] = norm_date(rec['截止时间'])
        # 转标准字段（与 QIUZHAO_DATA 对齐）
        std = {
            '公司名称': rec.get('公司名称', ''),
            '招聘岗位': rec.get('招聘岗位', ''),
            '工作地点': rec.get('工作地点', ''),
            '行业': rec.get('行业', ''),
            '企业性质': rec.get('企业性质', ''),
            '批次': rec.get('批次', ''),
            '招聘对象': rec.get('招聘对象', ''),
            '更新日期': rec.get('更新时间', ''),
            '截止日期': rec.get('截止时间', ''),
            '网申状态': rec.get('网申状态', ''),
            '官方公告': rec.get('官方公告', ''),
            '投递方式': rec.get('投递方式', ''),
            '内推码': rec.get('内推码/备注', ''),
        }
        # 过滤：无公司名跳过；更新时间格式非日期则清（说明行）
        if not std['公司名称']:
            continue
        records.append(std)
    return records


def main():
    print('[fetch_sheet2] 抓取 2027届校招信息汇总表 ...')
    d = fetch()
    rs = d['data']['initialAttributedText']['text'][0]['related_sheet']
    raw = zlib.decompress(base64.b64decode(rs))
    idx = raw.find('序号'.encode('utf-8'))
    cells = extract_text_cells(raw, max(0, idx - 20))
    print('[fetch_sheet2] 总 cell:', len(cells))
    # 定位表头
    try:
        hi = cells.index('内推码/备注')
        data_cells = cells[hi + 1:]
    except ValueError:
        data_cells = cells
    records = build_records(data_cells)
    print('[fetch_sheet2] 记录数:', len(records))
    js = 'window.SOURCE2_DATA = ' + json.dumps({
        'generatedAt': time.strftime('%Y-%m-%d %H:%M:%S'),
        'count': len(records),
        'records': records,
    }, ensure_ascii=False) + ';'
    out = os.path.join(OUT_DIR, 'data_source2.js')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(js)
    print('[fetch_sheet2] 已写', out, len(js), 'bytes')


if __name__ == '__main__':
    main()
