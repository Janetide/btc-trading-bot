"""Exact-fill backtester for btc-race: replicates harness sim/bars/engine.ts integer math.

Bars: o/c are ints at price_scale 5; depths are raw USDC units (1e6 per USDC).
Cash/qty in quote units (1e6 per USDC) / qty units (1e8 per BTC).
Fee 4bps, slippage 2bps. Orders decided on bar k fill at bar k+1 open vs o_depth.
"""
import gzip, json, math

BPS = 10_000
FEE = 4
SLIP = 2
START = 1_000_000_000  # 1000 USDC in quote units


def load_bars(path):
    bars = []
    with gzip.open(path, 'rt') as f:
        for line in f:
            b = json.loads(line)
            bars.append({
                't': b['t'], 'o': int(b['o']), 'c': int(b['c']),
                'h': int(b['h']), 'l': int(b['l']),
                'o_depth': [int(d) for d in b['o_depth']],
                'c_depth': [int(d) for d in b['c_depth']],
            })
    return bars


def buy_fill(notional, open_px, depth_raw):
    """Returns (price, qty, fee). Single-hop pool: factor = 1 + spend/depth_raw."""
    spend = notional * (BPS - FEE) // BPS
    # factor num/den = (d + spend*1e6)/d with d = depth_raw*1e6 -> 1 + spend/depth_raw
    num = depth_raw + spend
    den = depth_raw
    price = open_px * (BPS + SLIP) * num // (BPS * den)
    qty = spend * 10 ** 13 // (price * 10 ** 6)
    return price, qty, notional - spend


def sell_fill(qty, open_px, depth_raw):
    value = qty * open_px * 10 ** 6 // 10 ** 13
    # slipped = open*(BPS-SLIP)*d // (BPS*(d + value*1e6)) with d=depth_raw*1e6
    # = open*9998*depth_raw // (10000*(depth_raw+value))
    slipped = open_px * (BPS - SLIP) * depth_raw // (BPS * (depth_raw + value))
    price = max(slipped, 1)
    gross = qty * price * 10 ** 6 // 10 ** 13
    proceeds = gross * (BPS - FEE) // BPS
    return price, gross, gross - proceeds, proceeds


def value(qty, px):
    return qty * px * 10 ** 6 // 10 ** 13


def run(bars, decide, max_slip_bps=10_000):
    """decide(state) -> list of orders decided after bar k (dicts side/amount).
    state: dict with closes list, cash, qty, entry_px, equity history etc.
    Returns summary dict."""
    cash = START
    qty = 0
    entry_px = None
    closes = []
    pending = []  # orders decided at bar k, fill at bar k+1
    trades = 0
    fees = 0
    peak = START
    max_dd = 0.0
    equity_curve = []
    fills_log = []
    n = len(bars)
    for k, bar in enumerate(bars):
        # 1) resolve pending orders at this bar's open
        if pending:
            pool_touched = False
            for o in pending:
                if o['side'] == 'buy':
                    if o['notional'] > cash:
                        continue
                    price, q, fee = buy_fill(o['notional'], bar['o'], bar['o_depth'][0])
                    if price * BPS > o['ref_close'] * (BPS + max_slip_bps):
                        continue
                    if q == 0:
                        continue
                    cash -= o['notional']
                    qty += q
                    fees += fee
                    trades += 1
                    entry_px = price
                    fills_log.append((k, 'buy', price, q, o['notional']))
                else:
                    if qty == 0:
                        continue
                    q = min(o['qty'], qty)
                    price, gross, fee, proceeds = sell_fill(q, bar['o'], bar['o_depth'][0])
                    if price * BPS < o['ref_close'] * (BPS - max_slip_bps):
                        continue
                    cash += proceeds
                    qty -= q
                    fees += fee
                    trades += 1
                    if qty == 0:
                        entry_px = None
                    fills_log.append((k, 'sell', price, q, proceeds))
            pending = []
        closes.append(bar['c'])
        equity = cash + value(qty, bar['c'])
        equity_curve.append(equity)
        peak = max(peak, equity)
        dd = (peak - equity) / peak
        max_dd = max(max_dd, dd)
        # 2) decide orders for next bar (not on last bar)
        if k == n - 1:
            break
        st = {'k': k, 'closes': closes, 'cash': cash, 'qty': qty,
              'entry_px': entry_px, 'equity': equity, 'bar': bar}
        orders = decide(st) or []
        for o in orders:
            o = dict(o)
            o['ref_close'] = bar['c']
            pending.append(o)
    # flatten at last close vs c_depth
    if qty > 0:
        price, gross, fee, proceeds = sell_fill(qty, bars[-1]['c'], bars[-1]['c_depth'][0])
        cash += proceeds
        fees += fee
        qty = 0
    pnl = (cash - START) / 1e6
    return {'pnl_usdc': pnl, 'trades': trades, 'fees_usdc': fees / 1e6,
            'max_dd': max_dd, 'final_cash': cash / 1e6, 'fills': fills_log,
            'equity_curve': equity_curve}
