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

        # A1: 本平台單號唯一性
        order_counts = Counter(b['order_no'] for b in bets if b['order_no'])
        a1_errors = []
        for o, c in order_counts.items():
            if c > 1:
                a1_errors.append({'order_no': o, 'count': c})
        checks['A1'] = {
            'name': '本平台单号唯一性',
            'pass': len(a1_errors) == 0,
            'checked': len(bets),
            'errors': a1_errors,
        }

        # A2: 三方單號唯一性（按供應商/場館分組）
        venue_groups = {}
        for b in bets:
            tno = b.get('third_order_no')
            if not tno:
                continue
            venue = (b.get('venue') or b.get('game_name') or '未知').strip()
            if venue not in venue_groups:
                venue_groups[venue] = Counter()
            venue_groups[venue][tno] += 1
        a2_errors = []
        for venue, counts in venue_groups.items():
            for tno, c in counts.items():
                if c > 1:
                    a2_errors.append({
                        'venue': venue,
                        'third_order_no': tno,
                        'count': c,
                    })
        checks['A2'] = {
            'name': '三方单号唯一性(按供应商)',
            'pass': len(a2_errors) == 0,
            'checked': len(bets),
            'errors': a2_errors,
        }

        # A3: 真人視訊/彩票/體育的注單投注金額不可為0
        _target_keywords = [
            '视讯', '視訊', '真人', '彩票', '体育', '體育',
        ]
        a3_errors = []
        a3_checked = 0
        for b in bets:
            venue = (b.get('venue') or b.get('game_name') or '').strip()
            if any(k in venue for k in _target_keywords):
                a3_checked += 1
                if b['bet_amount'] is not None and b['bet_amount'] == 0:
                    a3_errors.append({
                        'order_no': b['order_no'],
                        'venue': venue,
                        'bet_amount': 0,
                    })
        checks['A3'] = {
            'name': '特定游戏投注金额非零',
            'pass': len(a3_errors) == 0,
            'checked': a3_checked,
            'errors': a3_errors,
        }

        # A4: 派彩合理性（派彩金額 ≥ 0）
        a4_errors = []
        for b in bets:
            if b['payout'] is not None and b['payout'] < 0:
                a4_errors.append({
                    'order_no': b['order_no'],
                    'bet_amount': b['bet_amount'],
                    'payout': b['payout'],
                })
        checks['A4'] = {
            'name': '派彩合理性',
            'pass': len(a4_errors) == 0,
            'checked': len(bets),
            'errors': a4_errors,
        }

        # A5: 遊戲帳變關聯（帳變中遊戲類型的關聯單號對應到注單）
        order_nos = set(b['order_no'] for b in bets if b['order_no'])
        third_order_nos = set(b['third_order_no'] for b in bets if b['third_order_no'])
        a5_errors = []
        for ac in self.account_changes:
            ct = (ac['change_type'] or '').lower()
            if any(k in ct for k in ('游戏', '注单', '派彩', '投注', '遊戲', '返水')):
                ref = ac['ref_order']
                if ref and ref not in order_nos and ref not in third_order_nos:
                    a5_errors.append({
                        'serial_no': ac['serial_no'],
                        'change_type': ac['change_type'],
                        'ref_order': ref,
                    })
        checks['A5'] = {
            'name': '游戏帐变关联',
            'pass': len(a5_errors) == 0,
            'checked': len(self.account_changes),
            'errors': a5_errors,
        }

        # A6: 時間順序（派彩時間 ≥ 投注時間）
        a6_errors = []
        for b in bets:
            if b['bet_time'] and b['payout_time']:
                if b['payout_time'] < b['bet_time']:
                    a6_errors.append({
                        'order_no': b['order_no'],
                        'bet_time': b['bet_time'],
                        'payout_time': b['payout_time'],
                    })
        checks['A6'] = {
            'name': '时间顺序',
            'pass': len(a6_errors) == 0,
            'checked': len(bets),
            'errors': a6_errors,
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


    def _build(self, cats):
        total_passed = 0
        total_failed = 0
        cat_summaries = {}

        for cat_id in ['A', 'B']:
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

        mi = self.member_summary or {}
        stats = {
            'bet_count': len(self.bets),
            'deposit_count': len(self.deposits),
            'withdraw_count': len(self.withdrawals),
            'total_bet_amount': round(sum((b['bet_amount'] or 0) for b in self.bets), 2),
            'total_payout': round(sum((b['payout'] or 0) for b in self.bets), 2),
            'total_winlose': round(sum((b['winlose'] or 0) for b in self.bets), 2),
        }

        first_deposit_date = None
        for d in self.deposits:
            t = d.get('complete_time')
            if t and (first_deposit_date is None or t < first_deposit_date):
                first_deposit_date = t

        total_rebate = 0.0
        total_bonus = 0.0
        for ac in self.account_changes:
            ct = (ac['change_type'] or '').lower()
            if '返水' in ct:
                total_rebate += (ac['amount'] or 0)
            elif any(k in ct for k in ('彩金', '活动', '活動', '奖励', '獎勵')):
                total_bonus += (ac['amount'] or 0)

        total_bet_winlose = round(
            sum(((b['payout'] or 0) - (b['bet_amount'] or 0)) for b in self.bets), 2)

        member_info = {
            'member_id': self.member_id,
            'account': mi.get('account'),
            'agent': mi.get('agent'),
            'register_date': mi.get('register_date'),
            'first_deposit_date': first_deposit_date,
            'total_bet_count': len(self.bets),
            'total_deposit_amount': mi.get('total_deposit_amount'),
            'total_withdraw_amount': mi.get('total_withdraw_amount'),
            'total_valid_bet': mi.get('total_valid_bet'),
            'total_rebate': round(total_rebate, 2),
            'total_bonus': round(total_bonus, 2),
            'total_winlose': total_bet_winlose,
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
            },
        }
