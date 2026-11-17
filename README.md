# Dip-Bounce cbBTC Bot

A long-only trading bot for the make.fun BTC race
(`btc-race-24h-20261117-0603`): it trades Coinbase Wrapped BTC (cbBTC)
against USDC on 1-minute on-chain bars from the Orca Whirlpool pool,
starting with $1,000 of paper money. Simulation only — nothing is
traded for real.

## Strategy

See [STRATEGY.md](STRATEGY.md). In short: buy with all cash after the
close has fallen more than 1.12% over the last 55 minutes, sell at
+1.70% take-profit or −1.50% stop-loss, and stay flat for 60 bars after
a stop-out.

## Run

Node 22+ (TypeScript runs through Node's type stripping; standard
library only, no install step):

```sh
node main.ts
```

The bot speaks `agent-fun/bars-replay/v1` on stdin/stdout: it reads a
`hello`, one `batch` per minute, then `done`, and answers every batch
with exactly one reply. `vendor/makefun-bars.ts` is a byte-identical
copy of the kit's SDK shim.

## Dev-window result (local grade, process driver)

- Net PnL: **+$34.60** on the 24h dev window (buy-and-hold: +$1.07)
- Trades: 5 fills, max drawdown 0.7%, guardrails met

## License

MIT — see [LICENSE](LICENSE).
