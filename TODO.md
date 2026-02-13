# Roast Bot TODO

## In Progress
- [ ] Fix chart accuracy (sampling across full tx history) — sub-agent working

## Next
- [ ] SQLite database for caching wallet analyses + roasts (save RPC calls)
  - Key: wallet address
  - Store: full analysis JSON + roast JSON + generated_at timestamp
  - TTL: 24h for analysis, 1h for roast (or configurable)
  - On repeat lookup: serve cached analysis, optionally re-generate roast
  - Also store historical roasts per wallet (fun to compare over time)
- [ ] Fix protocol usage & net worth charts with Helius deep history (if API key available)
- [ ] Submit to Open Innovation bounty
- [ ] Sentry DSN
- [ ] Mixpanel token
- [ ] Custom domain
