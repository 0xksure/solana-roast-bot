# 🔥 Solana Roast Bot

**Get your Solana wallet roasted by AI.** Paste a wallet address, get a savage (but funny) roast based on your actual on-chain activity, complete with a degen score and shareable card.

## How It Works

1. **Wallet Analysis** — Fetches SOL balance, token holdings, transaction history, and behavioral patterns from Solana RPC
2. **AI Roast** — Sends the analysis to Claude (Anthropic) which generates a personalized, data-driven roast
3. **Shareable Card** — Generates a PNG card with your roast, degen score, and stats for sharing on Twitter/X

## Features

- 🎯 **Data-driven roasts** — References your exact SOL balance, failure rate, shitcoin count, late night trading patterns
- 📊 **Degen Score** — 1-100 rating of how degen your wallet is
- 🖼️ **Shareable cards** — Auto-generated PNG cards with OG image support for social sharing
- 🔗 **Shareable links** — Each roast gets a unique URL with Twitter Card support
- 🪙 **Token resolution** — Uses Solana token list to identify tokens (unknowns get labeled "SHITCOIN")
- 🌙 **Behavioral analysis** — Detects late night trading, burst patterns, failure rates
- ⚡ **Fast** — Parallel data fetching, cached results

## Tech Stack

- **Backend:** Python, FastAPI, httpx (async)
- **AI:** Anthropic Claude 3.5 Haiku
- **Card Generation:** Pillow (PIL)
- **Data:** Solana RPC (mainnet), CoinGecko (SOL price), Solana Token List
- **Deploy:** Docker, DigitalOcean App Platform

## Run Locally

```bash
# Clone
git clone https://github.com/0xksure/solana-roast-bot.git
cd solana-roast-bot

# Install deps
pip install -r backend/requirements.txt

# Set API key
export ANTHROPIC_API_KEY="your-key-here"

# Run
uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload

# Open http://localhost:8080
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/roast` | Generate a roast (body: `{"wallet": "..."}`) |
| `GET` | `/api/roast/{wallet}/image` | Get roast card PNG |
| `GET` | `/api/roast/{wallet}` | OG-tagged HTML page for sharing |
| `GET` | `/api/stats` | Global stats |
| `GET` | `/api/recent` | Recent roasts |
| `GET` | `/{wallet}` | Shareable wallet page |

## Deploy to DigitalOcean

```bash
doctl apps create --spec .do/app.yaml
# Then set ANTHROPIC_API_KEY in the app's environment variables
```

## 🤖 Built Autonomously by an AI Agent

This project was built entirely by an AI agent as part of the [Superteam Open Innovation](https://superteam.fun) initiative. The agent:

1. Detected the "Solana wallet roasting" trend via its Narrative Radar
2. Generated the concept and architecture
3. Implemented the full stack (backend, frontend, card generator)
4. Tested and deployed it

No human wrote code for this project. The AI agent handled everything from idea to deployment.

## License

MIT
