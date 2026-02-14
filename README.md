# 🔥 Solana Roast Bot

**Get your Solana wallet roasted by AI.** Connect your wallet or paste an address — get a savage, data-driven roast based on your actual on-chain activity, complete with a degen score, wallet autopsy charts, and shareable card.

**🌐 Live:** [solana-roast-bot-km9nj.ondigitalocean.app](https://solana-roast-bot-km9nj.ondigitalocean.app)

## What It Does

Solana Roast Bot analyzes any Solana wallet's on-chain history and generates a personalized AI roast. Think "Spotify Wrapped" but for your degen activity — and way meaner.

### Features

- 🎯 **Data-driven roasts** — References your exact SOL balance, swap history, failure rate, dead token count, late-night trading patterns
- 📊 **Degen Score** (1-100) — Quantified measure of how degen your wallet is
- 📈 **Wallet Autopsy** — Interactive Chart.js visualizations: net worth timeline, protocol usage breakdown, monthly activity, biggest losses
- 🔗 **Wallet Connect** — Native Phantom, Solflare, Backpack, Coinbase Wallet support via `@solana/wallet-adapter`
- 🖼️ **Shareable cards** — Auto-generated PNG cards with Twitter/OG card metadata
- 🪙 **Token resolution** — Jupiter token list (13.6k tokens cached), unknowns labeled "SHITCOIN"
- 🕰️ **Deep history** — Swap parsing (Jupiter, Raydium, Orca program IDs), PnL estimation, win rate, market timeline, inactive gap detection, token graveyard
- 🌙 **Behavioral analysis** — Detects late-night trading, burst patterns, failure rates
- 🛡️ **Security hardened** — XSS prevention, IP+wallet rate limiting, async timeouts, CORS
- 🏆 **FairScale Reputation** — On-chain reputation scoring via FairScale API: trust vs degen radar chart, tier badges (Platinum/Gold/Silver/Bronze), reputation-aware roasts, "Most Trusted Degens" leaderboard
- ⚔️ **Roast Battles** — Head-to-head wallet comparison with AI verdict, stat bars, and winner crown
- 🎖️ **Achievement Badges** — Token Graveyard, Swap Addict, OG, Exit Liquidity, Whale Alert, and more
- 📊 **Percentile Ranking** — "More degen than X% of wallets roasted"
- 🏅 **Leaderboard** — Top 20 degens + Most Trusted Degens (combined degen × reputation)

## How Solana Is Used

This project reads extensively from the Solana blockchain:

1. **`getBalance`** — Current SOL holdings
2. **`getTokenAccountsByOwner`** — All SPL token positions (via Token Program)
3. **`getSignaturesForAddress`** — Full transaction signature history (paginated, up to 1000 across wallet lifetime)
4. **`getTransaction`** — Individual transaction details for swap detection and behavioral analysis
5. **Program ID detection** — Identifies interactions with Jupiter (`JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4`), Raydium CLMM, Orca Whirlpool, and other Solana DeFi protocols
6. **Token resolution** — Cross-references on-chain mint addresses against Jupiter's token registry

All data comes directly from Solana mainnet RPC — no third-party indexers required (optional Helius enrichment supported).

## Tech Stack

- **Frontend:** React 18 + Vite, @solana/wallet-adapter-react, Chart.js/react-chartjs-2
- **Backend:** Python, FastAPI, httpx (async)
- **AI:** Anthropic Claude 3.5 Haiku (cost-optimized)
- **Card Generation:** Pillow (PIL)
- **Reputation:** FairScale API (on-chain reputation scoring, badges, tiers)
- **Data:** Solana RPC (mainnet), Helius Enhanced API (parsed tx history), CoinGecko/Jupiter (SOL price), Jupiter Token List
- **Database:** PostgreSQL (DigitalOcean managed) with SQLite fallback for local dev
- **Monitoring:** Sentry (error tracking), built-in analytics
- **Deploy:** Docker multi-stage build, DigitalOcean App Platform

## Run Locally

```bash
# Clone
git clone https://github.com/0xksure/solana-roast-bot.git
cd solana-roast-bot

# Backend
pip install -r backend/requirements.txt
export ANTHROPIC_API_KEY="your-key-here"
export FAIRSCALE_API_KEY="your-fairscale-key"  # optional, enables reputation features
export HELIUS_API_KEY="your-helius-key"  # optional, enables enhanced tx history
uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173 (proxies API to :8080)
```

### Docker (production)

```bash
docker build -t solana-roast-bot .
docker run -p 8080:8080 -e ANTHROPIC_API_KEY="..." solana-roast-bot
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/roast` | Generate a roast (`{"wallet": "..."}`) |
| `GET` | `/api/roast/{wallet}/image` | Roast card PNG |
| `GET` | `/api/roast/{wallet}` | OG-tagged HTML page for sharing |
| `GET` | `/api/stats` | Global stats |
| `GET` | `/api/recent` | Recent roasts |
| `GET` | `/api/history` | Cached roast history |
| `GET` | `/api/fairscore/{wallet}` | FairScale reputation score |
| `GET` | `/api/reputation-leaderboard` | Top wallets by degen × reputation |
| `POST` | `/api/battle` | Head-to-head wallet battle |

## FairScale Integration

Solana Roast Bot integrates [FairScale](https://fairscale.xyz) reputation infrastructure to add an on-chain trust dimension to wallet roasts. This was built for the **FairScale Fairathon** bounty.

### What FairScale Adds

- **FairScore Card** (`FairScoreCard.jsx`) — Animated reputation score display with tier badge (Platinum/Gold/Silver/Bronze), base score, social score, wallet age, and active days breakdown. Includes a "persona" label based on trust×degen quadrant.
- **Trust vs Degen Radar** (`TrustDegenRadar.jsx`) — 6-axis Chart.js radar chart with dual datasets: degen axes (swap frequency, fail rate, shitcoin ratio) in red vs trust axes (FairScore, social score, wallet age) in cyan.
- **Reputation-Aware Roasts** — The AI roast prompt (`roast_engine.py`) receives FairScale data via `fairscale.format_for_roast()`, producing contextual humor:
  - High trust + high degen → "Trusted degen — respected by the chain, feared by your portfolio"
  - Low trust + high degen → "Anonymous ape — no reputation, all risk"
  - High trust + low degen → "Respectable builder — boring but your mom would be proud"
  - Low trust + low degen → "Ghost — the chain barely knows you exist"
- **FairScale Badges** (`FairBadges.jsx`) — Renders reputation badges (Diamond Hands, DAO Voter, Long-term Holder, etc.) with tier-colored styling alongside roast achievement badges.
- **Reputation Leaderboard** (`ReputationLeaderboard.jsx`) — "Most Trusted Degens" tab ranked by `degen_score × fairscore` combined score. Clickable rows trigger a roast.
- **Battle Comparisons** — Roast battles include reputation tier in the AI verdict context.

### Architecture

```
User → POST /api/roast → [Wallet Analysis + FairScale API (parallel fetch)]
                         → AI Roast (with reputation context injected)
                         → Response includes: roast + degen_score + fairscale{}

FairScale flow:
  fairscale.get_fairscore(wallet)
    → Check in-memory hot cache (1h TTL)
    → GET https://api.fairscale.xyz/score?wallet=X  (header: fairkey)
    → Cache in memory + persist to PostgreSQL fairscale_scores table
    → Return {fairscore, fairscore_base, social_score, tier, badges[], features{}}
```

### API Endpoints

| Endpoint | Description | Auth Required |
|----------|-------------|---------------|
| `GET /api/fairscore/{wallet}` | Full FairScale reputation profile for a wallet. Returns cached data (1h TTL) or fetches fresh from FairScale API. Returns 503 if API unavailable. | No (public) |
| `GET /api/reputation-leaderboard` | Top 20 wallets ranked by `degen_score × fairscore`. Requires both a roast and FairScale score to exist. | No (public) |

### FairScale API Response (from `/score`)

```json
{
  "wallet": "7xKXtg...",
  "fairscore_base": 58.1,
  "social_score": 36.0,
  "fairscore": 65.3,
  "tier": "gold",
  "badges": [
    { "id": "diamond_hands", "label": "Diamond Hands", "description": "Long-term holder", "tier": "platinum" }
  ],
  "features": {
    "lst_percentile_score": 0.75,
    "major_percentile_score": 0.82,
    "native_sol_percentile": 0.68,
    "tx_count": 1250,
    "active_days": 180,
    "wallet_age_days": 365
  }
}
```

### Database Schema

```sql
CREATE TABLE fairscale_scores (
    wallet TEXT PRIMARY KEY,
    fairscore DOUBLE PRECISION,
    fairscore_base DOUBLE PRECISION,
    social_score DOUBLE PRECISION,
    tier TEXT,
    badges TEXT,          -- JSON array
    features TEXT,        -- JSON object
    fetched_at DOUBLE PRECISION NOT NULL
);
```

### Graceful Degradation

The app works fully without FairScale — reputation features are additive, never blocking:

1. **No `FAIRSCALE_API_KEY` env var** → All FairScale UI sections hidden. `fairscale.py` returns `None` immediately. No API calls made.
2. **FairScale API returns 429/500** → Returns stale cache if available, `None` otherwise. Roast generation continues without reputation context.
3. **FairScale API timeout (10s)** → Same as above. The roast endpoint has a 30s overall timeout; FairScale is fetched in parallel and doesn't block wallet analysis.
4. **Frontend** → `{roast.fairscale && <FairScoreCard />}` — components only render when data exists.

### Frontend Components

| Component | File | Props | Description |
|-----------|------|-------|-------------|
| `FairScoreCard` | `FairScoreCard.jsx` | `fairscale, degenScore` | Animated score counter, tier badge, stat breakdown, persona label |
| `TrustDegenRadar` | `TrustDegenRadar.jsx` | `fairscale, walletStats` | 6-axis radar chart (Chart.js) |
| `FairBadges` | `FairBadges.jsx` | `badges` | Reputation badge list with tier coloring |
| `ReputationLeaderboard` | `ReputationLeaderboard.jsx` | `visible, onRoast` | Leaderboard tab, fetches from `/api/reputation-leaderboard` |

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude Haiku for roast generation |
| `SOLANA_RPC_URL` | Yes | Solana mainnet RPC |
| `FAIRSCALE_API_KEY` | No | FairScale reputation API key (get from [sales.fairscale.xyz](https://sales.fairscale.xyz)). Enables all trust/reputation features when set. |
| `HELIUS_API_KEY` | No | Helius Enhanced API (richer tx history, better chart accuracy) |
| `DATABASE_URL` | No | PostgreSQL connection string (falls back to SQLite for local dev) |

## 🤖 Built Autonomously by an AI Agent

This project was conceived, designed, built, and deployed entirely by **Max** (`max-ai-cofounder-pink-72`), an AI agent running on [OpenClaw](https://github.com/openclaw/openclaw).

### Agent Autonomy Timeline

1. **Concept Generation** — The agent evaluated 10+ project ideas using a scoring matrix (virality, technical feasibility, Solana integration depth, originality). Selected "Solana Roast Bot" scoring 10/10 on virality.
2. **Architecture Design** — Chose FastAPI + React stack, designed the wallet analysis pipeline, planned the roast generation prompt engineering.
3. **Backend Implementation** — Built the full wallet analyzer (RPC calls, swap parsing, behavioral analysis), roast engine (Anthropic integration with structured output), card generator (Pillow), and API endpoints.
4. **Frontend Implementation** — Built React SPA with wallet adapter integration, Chart.js visualizations, cyberpunk UI theme (Orbitron font, glass morphism, scanlines, fire particles).
5. **Asset Generation** — Used Leonardo.ai API to generate custom cyberpunk skull logo and city background.
6. **Security Hardening** — Added XSS prevention, rate limiting, async timeouts, CORS, error handling with funny messages.
7. **Testing** — 32 passing tests covering wallet analysis, roast generation, card creation, API endpoints.
8. **Deployment** — Configured Docker multi-stage build, deployed to DigitalOcean App Platform, debugged production issues (API key whitespace, token resolution, price fetching).
9. **Iteration** — Deep history analysis (swap parsing, PnL, market timeline), added wallet connect, improved chart accuracy, cyberpunk UI overhaul.

**Human involvement:** Kristoffer (operator) provided API keys, confirmed design direction, and deployed infrastructure. All code, architecture, prompts, and creative decisions were made by the agent.

## License

MIT
