# AGENTS.md — How This Was Built

This project was built **autonomously by an AI agent** (Claude, via OpenClaw) without human code contributions.

## The Process

### 1. Signal Detection
The agent's **Narrative Radar** — a system that monitors crypto Twitter, forums, and trends — detected growing interest in "Solana wallet roasting" and degen culture content.

### 2. Idea Generation
Based on the signal, the agent proposed building a tool that:
- Analyzes Solana wallets using on-chain data
- Generates AI-powered roasts that reference specific wallet stats
- Creates shareable cards for social media virality

### 3. Implementation
The agent built the entire stack:
- **FastAPI backend** with async Solana RPC calls
- **Wallet analyzer** with behavioral pattern detection (late night trading, burst patterns, failure rates)
- **Token resolver** using Solana Token List (unknown tokens = "SHITCOIN")
- **AI roast engine** with detailed prompting for data-specific humor
- **Card generator** using Pillow with gradient backgrounds and score visualization
- **Frontend** with progress animations, fire particles, and social sharing
- **Security** — input validation, XSS prevention, rate limiting, CORS, timeouts
- **Tests** — unit tests for all core modules

### 4. Testing & Polish
The agent ran tests, fixed issues, tested with real wallets, and polished the UX.

### 5. Deployment
Deployed to DigitalOcean App Platform via Docker.

## Architecture Decisions

- **No Helius dependency** — Works with free Solana RPC + CoinGecko for pricing
- **Token resolution via CDN-hosted Solana Token List** — No API keys needed
- **Claude 3.5 Haiku** — Fast and cheap for roast generation
- **In-memory caching** — Simple, no external cache needed for this scale
- **Behavioral analysis** — Time-of-day patterns, burst detection, failure rates give the AI specific data points to roast

## Narrative Radar

The idea originated from the agent's [Narrative Radar](https://github.com/0xksure/narrative-radar), which monitors crypto narratives and identifies buildable opportunities.
