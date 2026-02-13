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
- **Data:** Solana RPC (mainnet), CoinGecko/Jupiter (SOL price), Jupiter Token List
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
