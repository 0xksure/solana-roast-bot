# FairRoast — Tech Spec & Product Description

> **Solana Roast Bot × FairScale**: Reputation-aware wallet roasting. See how degen you really are — and whether anyone should trust you.

## Product Overview

FairRoast integrates FairScale's reputation infrastructure into the Solana Roast Bot. Instead of just roasting a wallet's degen behavior, we overlay **on-chain reputation scoring** to create a "Trust vs Degen" profile — the full picture of any Solana wallet.

**One-liner:** *"Get your wallet roasted AND rated. Degen score meets reputation score."*

### Why This Exists

Roast Bot already analyzes wallets for entertainment. FairScale provides real reputation data. Combined, you get:
- **Entertainment + Utility** — fun roasts backed by real on-chain reputation signals
- **Viral sharing** — "I'm a Gold-tier degen" is inherently shareable
- **Real use case** — DeFi protocols could use this to gamify reputation

### Target Users
- Solana degens who want to flex (or get roasted)
- CT personalities comparing wallets
- DeFi protocols exploring reputation gating
- Anyone curious about their on-chain standing

---

## Tech Stack

### Frontend
- **React 18** + **Vite** (fast builds, modern DX)
- **@solana/wallet-adapter-react** — wallet connection (Phantom, Solflare, etc.)
- **Chart.js** via **react-chartjs-2** — radar charts, bar charts
- **Tailwind CSS** — utility-first styling
- **TypeScript** (new components)

### Backend
- **Python 3.11** + **FastAPI**
- **Anthropic Claude Haiku** — AI roast generation
- **Helius Enhanced API** — parsed transaction history
- **FairScale API** — reputation scores, badges, tiers
- **PostgreSQL** (DigitalOcean managed) — persistence
- **SQLite fallback** for local dev

### Infrastructure
- **DigitalOcean App Platform** — deployment
- **Docker multi-stage build** — optimized images
- **GitHub Actions** — CI/CD
- **Sentry** — error monitoring

---

## FairScale Integration

### API Endpoints Used

| Endpoint | Purpose | Response |
|----------|---------|----------|
| `GET /score?wallet=X` | Full reputation profile | fairscore, tier, badges, features, social_score |
| `GET /fairScore?wallet=X` | Quick score only | fair_score integer |

**Auth:** `fairkey` header with API key.
**Rate limit:** Free tier = 10 req/min. Cache aggressively (scores don't change fast).

### API Response Shape (from `/score`)
```json
{
  "wallet": "7xKXtg...",
  "fairscore_base": 58.1,
  "social_score": 36.0,
  "fairscore": 65.3,
  "tier": "gold",
  "badges": [
    { "id": "diamond_hands", "label": "Diamond Hands", "description": "Long-term holder with conviction", "tier": "platinum" }
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

---

## New Features

### 1. FairScore Display Card
After roasting, show the wallet's FairScale reputation alongside the degen score.

**UI Layout:**
```
┌──────────────────────────────────┐
│  🔥 DEGEN SCORE: 87/100         │
│  🛡️ FAIRSCORE: 65.3 (Gold)      │
│                                  │
│  [Trust vs Degen Radar Chart]    │
│                                  │
│  Badges: 💎 Diamond Hands        │
│          🏛️ DAO Voter            │
│          🔒 Long-term Holder     │
│                                  │
│  "You're a trusted degen.        │
│   Gold-tier reputation but       │
│   still aping into everything."  │
└──────────────────────────────────┘
```

### 2. Trust vs Degen Radar Chart
6-axis radar chart comparing:
- **Degen axes:** Swap frequency, Meme coin %, Loss ratio
- **Trust axes:** FairScore, Social score, Wallet age

Built with react-chartjs-2, dual-colored (red for degen, green for trust).

### 3. Reputation-Aware Roasts
The AI roast prompt includes FairScale data:
- **High trust + high degen** → "Respected community member who still apes into everything"
- **Low trust + high degen** → "Anonymous degen with nothing to lose"
- **High trust + low degen** → "Boring but trustworthy"
- **Low trust + low degen** → "Ghost wallet, nobody knows you, you've done nothing"

### 4. FairScale Badges in Results
Display FairScale badges alongside our existing achievement badges (Token Graveyard, Swap Addict, OG, etc.). Different visual style to distinguish reputation badges from roast badges.

### 5. Reputation Leaderboard Tab
New leaderboard view: "Most Trusted Degens" — sorted by combined degen_score × fairscore. Shows wallets that are both degenerate AND reputable.

### 6. Battle Mode Enhancement
Roast battles now include reputation comparison:
- "Wallet A is a Gold-tier degen, Wallet B is a Bronze nobody"
- Trust score difference shown in stat bars

---

## Backend Changes

### New Endpoint: `GET /api/fairscore/{wallet}`
Returns cached FairScale data for a wallet.

```python
@app.get("/api/fairscore/{wallet}")
async def get_fairscore(wallet: str):
    # Check cache (1h TTL)
    # Call FairScale API
    # Store in PostgreSQL
    # Return combined data
```

### Modified Endpoint: `POST /api/roast`
Now includes FairScale data in the roast context:
- Fetches FairScale score in parallel with wallet analysis
- Passes fairscore, tier, badges to AI prompt
- Stores FairScale data alongside roast in DB

### New DB Table: `fairscale_scores`
```sql
CREATE TABLE IF NOT EXISTS fairscale_scores (
    wallet TEXT PRIMARY KEY,
    fairscore REAL,
    fairscore_base REAL,
    social_score REAL,
    tier TEXT,
    badges JSONB,
    features JSONB,
    fetched_at TIMESTAMP DEFAULT NOW()
);
```

### Caching Strategy
- Cache FairScale responses for 1 hour (scores don't change frequently)
- PostgreSQL for persistence across deploys
- In-memory dict for hot cache within a single process

---

## Frontend Changes

### New Components
| Component | Purpose |
|-----------|---------|
| `FairScoreCard.tsx` | Displays FairScore, tier badge, and reputation summary |
| `TrustDegenRadar.tsx` | 6-axis radar chart (react-chartjs-2) |
| `FairBadges.tsx` | Renders FairScale badges with tier colors |
| `ReputationLeaderboard.tsx` | "Most Trusted Degens" leaderboard tab |

### Modified Components
| Component | Change |
|-----------|--------|
| `RoastResult.jsx` | Add FairScore section below degen score |
| `BattleResult.jsx` | Add reputation comparison bars |
| `ShareActions.jsx` | Include tier in share text ("Gold-tier degen") |
| `App.jsx` | Add reputation leaderboard tab |

---

## Implementation Plan

### Phase 1: Backend Integration (Day 1)
- [ ] Add FairScale API client (`backend/roaster/fairscale.py`)
- [ ] Create `fairscale_scores` DB table
- [ ] Add `/api/fairscore/{wallet}` endpoint
- [ ] Modify roast endpoint to fetch FairScale data in parallel
- [ ] Update AI prompt to include reputation context

### Phase 2: Frontend — Score Display (Day 2)
- [ ] `FairScoreCard` component with tier styling
- [ ] `TrustDegenRadar` radar chart
- [ ] `FairBadges` component
- [ ] Integrate into `RoastResult`

### Phase 3: Leaderboard & Battle (Day 3)
- [ ] `ReputationLeaderboard` component
- [ ] Battle mode reputation comparison
- [ ] Share text updates

### Phase 4: Polish & Deploy (Day 4)
- [ ] Responsive design / mobile polish
- [ ] Error handling for FairScale API failures (graceful degradation)
- [ ] Deploy to DigitalOcean
- [ ] Create demo video

### Phase 5: Submission (Day 5)
- [ ] Kristoffer creates Legends.fun page (invite code: FAIRAT)
- [ ] Kristoffer submits on Superteam Earn
- [ ] Tweet about the integration

---

## Graceful Degradation

FairScale API might be unavailable or rate-limited. The app must still work:
1. If FairScale returns 429/500 → show "Reputation score unavailable" with retry button
2. If no API key configured → hide FairScore section entirely
3. Roast generation continues regardless — FairScale data is additive, not blocking

---

## Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `FAIRSCALE_API_KEY` | FairScale API key | Yes (for reputation features) |
| `DATABASE_URL` | PostgreSQL connection | Yes (production) |
| `HELIUS_API_KEY` | Helius Enhanced API | Yes |
| `ANTHROPIC_API_KEY` | Claude Haiku for roasts | Yes |
| `SOLANA_RPC_URL` | Solana RPC endpoint | Yes |

---

## Success Metrics

- **Integration depth:** FairScale data visible in roasts, battles, leaderboards, and share cards
- **User engagement:** Track FairScore lookups vs regular roasts
- **Virality:** Share text includes tier ("I'm a Gold-tier degen on Solana")
- **Uptime:** Graceful degradation when FairScale API is down

---

## Repo Structure (additions)
```
solana-roast-bot/
├── backend/
│   └── roaster/
│       ├── fairscale.py          # NEW — FairScale API client
│       ├── roast_engine.py       # MODIFIED — reputation-aware prompts
│       ├── wallet_analyzer.py    # unchanged
│       └── db.py                 # MODIFIED — fairscale_scores table
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── FairScoreCard.tsx      # NEW
│       │   ├── TrustDegenRadar.tsx    # NEW
│       │   ├── FairBadges.tsx         # NEW
│       │   ├── ReputationLeaderboard.tsx  # NEW
│       │   ├── RoastResult.jsx        # MODIFIED
│       │   ├── BattleResult.jsx       # MODIFIED
│       │   └── ShareActions.jsx       # MODIFIED
│       └── App.jsx                    # MODIFIED
```
