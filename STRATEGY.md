# Strategy note

## Idea

On the 24-hour dev window cbBTC is range-bound ($63,874–$65,467) with
sharp hourly dips that snap back. A full-size round trip costs about
26–37 bps (4 bps fee + 2 bps slippage + ~7–13 bps pool impact per
leg), so frequent trading loses money — the kit's EMA-cross baseline
lost $106 on 68 trades. This bot therefore trades rarely and only
after a deep, fast dip, then holds for a full bounce.

## Rules

- **Entry** (flat only): the latest close is more than 1.12% below
  the close 55 bars ago (55-minute return < −112 bps). Buy with all
  cash (one position, up to 100% of equity). Entry needs 56 closes
  of history.
- **Take profit**: sell the whole position when the close is at least
  1.70% above the entry price.
- **Stop loss**: sell the whole position when the close is at least
  1.50% below the entry price. After a stop-out, no new entry for
  60 bars.
- **Slippage guard**: every order names `max_slippage_bps: 300`, so a
  fill more than 3% away from the latest close is rejected rather
  than chased.
- No leverage, no shorts, no time-based exit: a position rides until
  take-profit, stop-loss, or the window's final flatten.

Entry price is read from the position's cost basis, so the thresholds
compare against what was actually paid (fees included).

## Why these numbers

Backtested on the dev window with a simulator replicating the
harness's exact integer fill model (later confirmed by the kit's own
`grade-local`): **+$34.60 net PnL, 5 fills, 0.7% max drawdown**.
Nearby parameters all score +$20–$35 (lookbacks 45–65, dip
0.9–1.12%, take-profit 1.4–1.7%), so the edge is the dip-bounce
structure, not a tuned spike. Scale-in legs, multi-gate entries,
trailing stops, and a 5-minute stabilisation filter were all tried
and rejected — each scored worse on the dev window. The stop-loss
never triggered on the dev window; it exists purely as downside
protection for the unseen race window.

## Risks

The race window is a different 24 hours. In a sustained downtrend
the bot can take repeated 1.5% stop-outs (mitigated by the 60-bar
cooldown); in a strong uptrend with no 1.12% dip it may sit in cash
and finish near $0. Max drawdown is capped by the stop-loss plus
the final flatten.
