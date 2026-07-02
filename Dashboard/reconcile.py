import csv
import io
from collections import Counter


def _classify(name):
    n = name.lower()
    if '会员帐变纪录' in n or '账变记录' in n:
        return 'account_change'
    if '充值提现' in n or '充提款' in n or '充提现明细' in n:
        return 'deposit_withdraw'
    if ('注单' in n and '明细' in n) or n.startswith('注单明细'):
        return 'betting'
    if '会员讯息汇总' in n or '会员信息汇总' in n:
        return 'member_summary'
    return None


BETTING_FIELDS = {
    'member_id': ['会员ID'],
    'order_no': ['本平台单号'],
    'third_order_no': ['三方单号'],
    'bet_amount': ['投注金额'],
    'payout': ['派彩金额'],
    'winlose': ['会员输赢金额'],
    'valid_bet': ['有效打码'],
    'rebate': ['返水'],
    'bet_time': ['投注日期时间'],
    'payout_time': ['派彩日期时间'],
    'game_name': ['游戏名称'],
    'venue': ['游戏场馆'],
}

DEPOSIT_FIELDS = {
    'member_id': ['会员ID'],
    'order_no': ['订单号'],
    'type': ['类型'],
    'amount': ['金额'],
    'status': ['状态'],
    'complete_time': ['完成时间'],
}

ACCOUNT_FIELDS = {
    'member_id': ['会员ID'],
    'serial_no': ['流水号'],
    'change_type': ['帐变类型'],
    'amount': ['帐变金额'],
    'balance_before': ['帐变前余额'],
    'balance_after': ['帐变后余额'],
    'ref_order': ['关联单号'],
    'change_time': ['帐变时间'],
}

SUMMARY_FIELDS = {
    'member_id': ['会员ID', '会员 ID'],
    'account': ['会员登入帐号'],
    'agent': ['上级代理'],
    'register_date': ['注册日期时间'],
    'first_deposit': ['第一次充值成功的日期时间'],
    'last_deposit': ['最新一次充值成功的日期时间'],
    'first_bet': ['第一笔游戏注单的日期时间'],
    'last_bet': ['最新一笔游戏注单的日期时间'],
    'total_deposit_count': ['充值累积总次数'],
    'total_deposit_amount': ['累积充值总额'],
    'total_withdraw_count': ['累积提现次数'],
    'total_withdraw_amount': ['累积提现总额'],
    'total_valid_bet': ['有效打码累积总额'],
    'total_winlose': ['输赢累积总额'],
    'total_bet_count': ['注单累积总数'],
}


def _map_columns(headers, field_defs):
    m = {}
    for field, patterns in field_defs.items():
        for p in patterns:
            if p in headers:
                m[field] = headers.index(p)
                break
    return m


def _val(row, idx):
    if idx is None:
        return None
    v = row[idx].strip()
    return v if v else None


def _num(row, idx):
    v = _val(row, idx)
    if v is None:
        return None
    try:
        return float(v.replace(',', ''))
    except (ValueError, AttributeError):
        return None


class Reconciliator:

    def __init__(self, source, member_id):
        self.source = source
        self.member_id = str(member_id)
        self.bets = []
        self.deposits = []
        self.withdrawals = []
        self.account_changes = []
        self.member_summary = None
        self._seen_orders = set()

    def run(self):
        self._collect_data()
        cats = {}
        cats['A'] = self._check_betting()
        cats['B'] = self._check_deposit_withdraw()
        cats['C'] = self._check_account_change()
        cats['D'] = self._check_rebate()
        cats['E'] = self._check_member_summary()
        return self._build(cats)

    def _collect_data(self):
        self._summary_mtime = 0
        for name, mtime, fh in self.source.iter_csv():
            ftype = _classify(name)
            if ftype is None:
                continue
            try:
                reader = csv.reader(fh)
                headers = next(reader)
                if ftype == 'betting':
                    self._parse_betting(headers, reader)
                elif ftype == 'deposit_withdraw':
                    self._parse_deposit(headers, reader)
                elif ftype == 'account_change':
                    self._parse_account(headers, reader)
                elif ftype == 'member_summary':
                    self._parse_summary(headers, reader, mtime)
            except Exception:
                continue

    def _row_matches(self, row, col):
        return self.member_id == _val(row, col)

    def _parse_betting(self, headers, reader):
        m = _map_columns(headers, BETTING_FIELDS)
        mid_col = m.get('member_id')
        if mid_col is None:
            return
        for row in reader:
            if not row or len(row) <= mid_col:
                continue
            if not self._row_matches(row, mid_col):
                continue
            order_no = _val(row, m.get('order_no'))
            if order_no and order_no in self._seen_orders:
                continue
            if order_no:
                self._seen_orders.add(order_no)
            self.bets.append({
                'order_no': _val(row, m.get('order_no')),
                'third_order_no': _val(row, m.get('third_order_no')),
                'bet_amount': _num(row, m.get('bet_amount')),
                'payout': _num(row, m.get('payout')),
                'winlose': _num(row, m.get('winlose')),
                'valid_bet': _num(row, m.get('valid_bet')),
                'rebate': _num(row, m.get('rebate')),
                'bet_time': _val(row, m.get('bet_time')),
                'payout_time': _val(row, m.get('payout_time')),
            })

    def _parse_deposit(self, headers, reader):
        m = _map_columns(headers, DEPOSIT_FIELDS)
        mid_col = m.get('member_id')
        if mid_col is None:
            return
        for row in reader:
            if not row or len(row) <= mid_col:
                continue
            if not self._row_matches(row, mid_col):
                continue
            t = (_val(row, m.get('type')) or '').lower()
            rec = {
                'order_no': _val(row, m.get('order_no')),
                'type': _val(row, m.get('type')),
                'amount': _num(row, m.get('amount')),
                'status': _val(row, m.get('status')),
                'complete_time': _val(row, m.get('complete_time')),
            }
            if any(k in t for k in ('充值', '存款', 'deposit')):
                self.deposits.append(rec)
            elif any(k in t for k in ('提现', '取款', 'withdraw')):
                self.withdrawals.append(rec)

    def _parse_account(self, headers, reader):
        m = _map_columns(headers, ACCOUNT_FIELDS)
        mid_col = m.get('member_id')
        if mid_col is None:
            return
        for row in reader:
            if not row or len(row) <= mid_col:
                continue
            if not self._row_matches(row, mid_col):
                continue
            self.account_changes.append({
                'serial_no': _val(row, m.get('serial_no')),
                'change_type': _val(row, m.get('change_type')),
                'amount': _num(row, m.get('amount')),
                'balance_before': _num(row, m.get('balance_before')),
                'balance_after': _num(row, m.get('balance_after')),
                'ref_order': _val(row, m.get('ref_order')),
                'change_time': _val(row, m.get('change_time')),
            })

    def _parse_summary(self, headers, reader, mtime=0):
        m = _map_columns(headers, SUMMARY_FIELDS)
        mid_col = m.get('member_id')
        if mid_col is None:
            return
        for row in reader:
            if not row or len(row) <= mid_col:
                continue
            if not self._row_matches(row, mid_col):
                continue
            if mtime < self._summary_mtime:
                continue
            self._summary_mtime = mtime
            self.member_summary = {
                'account': _val(row, m.get('account')),
                'agent': _val(row, m.get('agent')),
                'register_date': _val(row, m.get('register_date')),
                'total_deposit_count': _num(row, m.get('total_deposit_count')),
                'total_deposit_amount': _num(row, m.get('total_deposit_amount')),
                'total_withdraw_count': _num(row, m.get('total_withdraw_count')),
                'total_withdraw_amount': _num(row, m.get('total_withdraw_amount')),
                'total_valid_bet': _num(row, m.get('total_valid_bet')),
                'total_winlose': _num(row, m.get('total_winlose')),
                'total_bet_count': _num(row, m.get('total_bet_count')),
            }

    def _check_betting(self):
        bets = self.bets
        checks = {}

        a1_errors = []
        for b in bets:
            if b['payout'] is not None and b['bet_amount'] is not None and b['winlose'] is not None:
                expected = b['payout'] - b['bet_amount']
                if abs(expected - b['winlose']) > 0.01:
                    a1_errors.append({
                        'order_no': b['order_no'],
                        'bet_amount': b['bet_amount'],
                        'payout': b['payout'],
                        'expected_winlose': round(expected, 2),
                        'actual_winlose': b['winlose'],
                    })
        checks['A1'] = {
            'name': '会员输赢公式',
            'pass': len(a1_errors) == 0,
            'checked': len(bets),
            'errors': a1_errors,
        }

        a2_errors = []
        for b in bets:
            if b['payout'] is not None and b['payout'] < 0:
                a2_errors.append({
                    'order_no': b['order_no'],
                    'bet_amount': b['bet_amount'],
                    'payout': b['payout'],
                })
        checks['A2'] = {
            'name': '派彩合理性',
            'pass': len(a2_errors) == 0,
            'checked': len(bets),
            'errors': a2_errors,
        }

        a3_errors = []
        for b in bets:
            if b['valid_bet'] is not None and b['bet_amount'] is not None:
                if b['bet_amount'] > 0 and b['valid_bet'] > b['bet_amount'] + 0.01:
                    a3_errors.append({
                        'order_no': b['order_no'],
                        'bet_amount': b['bet_amount'],
                        'valid_bet': b['valid_bet'],
                    })
        checks['A3'] = {
            'name': '有效打码',
            'pass': len(a3_errors) == 0,
            'checked': len(bets),
            'errors': a3_errors,
        }

        a4_errors = []
        for b in bets:
            if b['bet_time'] and b['payout_time']:
                if b['payout_time'] < b['bet_time']:
                    a4_errors.append({
                        'order_no': b['order_no'],
                        'bet_time': b['bet_time'],
                        'payout_time': b['payout_time'],
                    })
        checks['A4'] = {
            'name': '时间顺序',
            'pass': len(a4_errors) == 0,
            'checked': len(bets),
            'errors': a4_errors,
        }

        order_counts = Counter(b['order_no'] for b in bets if b['order_no'])
        third_counts = Counter(b['third_order_no'] for b in bets if b['third_order_no'])
        a5_errors = []
        for o, c in order_counts.items():
            if c > 1:
                a5_errors.append({'order_no': o, 'count': c, 'type': '本平台单号'})
        for o, c in third_counts.items():
            if c > 1:
                a5_errors.append({'order_no': o, 'count': c, 'type': '三方单号'})
        checks['A5'] = {
            'name': '单号唯一性',
            'pass': len(a5_errors) == 0,
            'checked': len(bets),
            'errors': a5_errors,
        }

        return checks

    def _check_deposit_withdraw(self):
        checks = {}
        bw_orders = set()
        for d in self.deposits:
            if d['order_no']:
                bw_orders.add(d['order_no'])
        for w in self.withdrawals:
            if w['order_no']:
                bw_orders.add(w['order_no'])

        b1_errors = []
        for ac in self.account_changes:
            ct = (ac['change_type'] or '').lower()
            if any(k in ct for k in ('充值', '提现', '存款', '取款')):
                ref = ac['ref_order']
                if ref and ref not in bw_orders:
                    b1_errors.append({
                        'serial_no': ac['serial_no'],
                        'change_type': ac['change_type'],
                        'ref_order': ref,
                    })
        checks['B1'] = {
            'name': '关联单号',
            'pass': len(b1_errors) == 0,
            'checked': len(self.deposits) + len(self.withdrawals),
            'errors': b1_errors,
        }
        return checks

    def _check_account_change(self):
        checks = {}
        order_nos = set()
        for b in self.bets:
            if b['order_no']:
                order_nos.add(b['order_no'])

        c1_errors = []
        for ac in self.account_changes:
            ct = (ac['change_type'] or '').lower()
            if any(k in ct for k in ('游戏', '注单', '派彩', '投注')):
                ref = ac['ref_order']
                if ref and ref not in order_nos:
                    c1_errors.append({
                        'serial_no': ac['serial_no'],
                        'change_type': ac['change_type'],
                        'ref_order': ref,
                    })
        checks['C1'] = {
            'name': '游戏关联',
            'pass': len(c1_errors) == 0,
            'checked': len(self.account_changes),
            'errors': c1_errors,
        }

        sorted_ac = sorted(self.account_changes, key=lambda x: x['change_time'] or '')
        c2_errors = []
        for i in range(len(sorted_ac) - 1):
            cur = sorted_ac[i]
            nxt = sorted_ac[i + 1]
            if cur['balance_after'] is not None and nxt['balance_before'] is not None:
                if abs(cur['balance_after'] - nxt['balance_before']) > 0.01:
                    c2_errors.append({
                        'serial_no_cur': cur['serial_no'],
                        'serial_no_nxt': nxt['serial_no'],
                        'balance_after_cur': cur['balance_after'],
                        'balance_before_nxt': nxt['balance_before'],
                    })
        checks['C2'] = {
            'name': '余额连续性',
            'pass': len(c2_errors) == 0,
            'checked': max(0, len(sorted_ac) - 1),
            'errors': c2_errors,
        }

        c3_errors = []
        if len(sorted_ac) >= 2:
            first = sorted_ac[0]
            last = sorted_ac[-1]
            if first['balance_before'] is not None and last['balance_after'] is not None:
                total_change = sum((ac['amount'] or 0) for ac in sorted_ac)
                expected_diff = last['balance_after'] - first['balance_before']
                if abs(total_change - expected_diff) > 0.01:
                    c3_errors.append({
                        'first_balance': first['balance_before'],
                        'last_balance': last['balance_after'],
                        'expected_diff': round(expected_diff, 2),
                        'actual_sum': round(total_change, 2),
                        'diff': round(total_change - expected_diff, 2),
                    })
        checks['C3'] = {
            'name': '帐变总和',
            'pass': len(c3_errors) == 0,
            'checked': len(sorted_ac),
            'errors': c3_errors,
        }
        return checks

    def _check_rebate(self):
        checks = {}
        d1_errors = []
        for b in self.bets:
            if b['rebate'] is not None and b['valid_bet'] is not None and b['valid_bet'] > 0:
                ratio = b['rebate'] / b['valid_bet']
                if ratio < 0 or ratio > 0.02:
                    d1_errors.append({
                        'order_no': b['order_no'],
                        'valid_bet': b['valid_bet'],
                        'rebate': b['rebate'],
                        'ratio': round(ratio * 100, 4),
                    })
        checks['D1'] = {
            'name': '返水比例',
            'pass': len(d1_errors) == 0,
            'checked': len(self.bets),
            'errors': d1_errors,
        }
        return checks

    def _check_member_summary(self):
        checks = {}
        s = self.member_summary
        if s is None:
            for k in ['E1', 'E2', 'E3', 'E4', 'E5']:
                checks[k] = {'name': '', 'pass': False, 'checked': 0,
                             'errors': [{'msg': '未找到该会员的汇总数据'}]}
            checks['E1']['name'] = '充值总额'
            checks['E2']['name'] = '提现总额'
            checks['E3']['name'] = '输赢总额'
            checks['E4']['name'] = '注单总数'
            checks['E5']['name'] = '有效打码'
            return checks

        total_deposit = sum((d['amount'] or 0) for d in self.deposits)
        total_withdraw = sum((w['amount'] or 0) for w in self.withdrawals)
        total_winlose = sum((b['winlose'] or 0) for b in self.bets)
        total_bet_count = len(self.bets)
        total_valid_bet = sum((b['valid_bet'] or 0) for b in self.bets)

        pairs = [
            ('E1', '充值总额', total_deposit, s['total_deposit_amount']),
            ('E2', '提现总额', total_withdraw, s['total_withdraw_amount']),
            ('E3', '输赢总额', total_winlose, s['total_winlose']),
            ('E4', '注单总数', total_bet_count, s['total_bet_count']),
            ('E5', '有效打码', total_valid_bet, s['total_valid_bet']),
        ]
        for code, cname, detail_total, summary_val in pairs:
            errs = []
            if summary_val is not None and abs(detail_total - summary_val) > 0.01:
                errs.append({
                    'detail_total': round(detail_total, 2) if isinstance(detail_total, float) else detail_total,
                    'summary_value': round(summary_val, 2) if isinstance(summary_val, float) else summary_val,
                    'diff': round(detail_total - summary_val, 2) if isinstance(detail_total, float) else int(detail_total - summary_val),
                })
            checks[code] = {
                'name': cname,
                'pass': len(errs) == 0,
                'checked': 1,
                'errors': errs,
            }
        return checks

    def _build(self, cats):
        all_checks = []
        total_passed = 0
        total_failed = 0
        cat_summaries = {}

        for cat_id in ['A', 'B', 'C', 'D', 'E']:
            checks = cats.get(cat_id, {})
            cat_passed = sum(1 for c in checks.values() if c['pass'])
            cat_failed = sum(1 for c in checks.values() if not c['pass'])
            cat_total = len(checks)
            cat_summaries[cat_id] = {
                'total': cat_total,
                'passed': cat_passed,
                'failed': cat_failed,
            }
            total_passed += cat_passed
            total_failed += cat_failed
            all_checks.extend(checks.values())

        mi = self.member_summary or {}
        stats = {
            'bet_count': len(self.bets),
            'deposit_count': len(self.deposits),
            'withdraw_count': len(self.withdrawals),
            'account_change_count': len(self.account_changes),
            'total_bet_amount': round(sum((b['bet_amount'] or 0) for b in self.bets), 2),
            'total_payout': round(sum((b['payout'] or 0) for b in self.bets), 2),
            'total_winlose': round(sum((b['winlose'] or 0) for b in self.bets), 2),
        }

        member_info = None
        if mi:
            member_info = {
                'member_id': self.member_id,
                'account': mi.get('account'),
                'agent': mi.get('agent'),
                'register_date': mi.get('register_date'),
                'total_deposit_amount': mi.get('total_deposit_amount'),
                'total_withdraw_amount': mi.get('total_withdraw_amount'),
                'total_valid_bet': mi.get('total_valid_bet'),
                'total_winlose': mi.get('total_winlose'),
            }

        return {
            'member_id': self.member_id,
            'member_info': member_info,
            'stats': stats,
            'summary': {
                'total': total_passed + total_failed,
                'passed': total_passed,
                'failed': total_failed,
            },
            'categories': {
                'A': {'name': '注单核对', 'checks': cats.get('A', {}), **cat_summaries['A']},
                'B': {'name': '充值提现核对', 'checks': cats.get('B', {}), **cat_summaries['B']},
                'C': {'name': '帐变核对', 'checks': cats.get('C', {}), **cat_summaries['C']},
                'D': {'name': '返水核对', 'checks': cats.get('D', {}), **cat_summaries['D']},
                'E': {'name': '会员汇总核对', 'checks': cats.get('E', {}), **cat_summaries['E']},
            },
        }
