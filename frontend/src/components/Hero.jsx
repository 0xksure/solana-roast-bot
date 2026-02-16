import React, { useState, useEffect, useRef } from 'react';
import WalletButton from './WalletButton';
import PersonaSelector from './PersonaSelector';

const EXAMPLES = [
  { name: 'Toly', addr: 'CKs1E69a2e9TmH4mKKLrXFF8kD3ZnwKjoEuXa6sz9WqX' },
  { name: 'Mert', addr: 'madSoL3Fz7Jm5fFBxEDFmAEJCm588bun5KEiJrb7ivH' },
  { name: 'Whale 🐋', addr: '5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9' },
];

function useCountUp(target, duration = 1500) {
  const [value, setValue] = useState(0);
  const started = useRef(false);
  useEffect(() => {
    if (!target || started.current) return;
    started.current = true;
    const start = performance.now();
    function tick(now) {
      const p = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      setValue(Math.round(target * eased));
      if (p < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }, [target, duration]);
  return value;
}

export default function Hero({ onRoast, error, battleMode, onToggleBattle, persona, onPersonaChange }) {
  const [input, setInput] = useState('');
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetch('/api/stats').then(r => r.json()).then(setStats).catch(() => {});
  }, []);

  const animatedRoasts = useCountUp(stats?.total_roasts);
  const animatedScore = useCountUp(stats?.avg_degen_score, 1200);

  const handleSubmit = () => {
    if (input.trim()) onRoast(input.trim(), persona);
  };

  return (
    <div className="hero" id="hero">
      <img src="/img/logo.jpg" alt="Solana Roast Bot" className="hero-logo" />
      <h1>GET ROASTED</h1>
      <p className="subtitle">How degen is your Solana wallet?</p>

      <div className="mode-toggle">
        <button className={`mode-tab ${!battleMode ? 'active' : ''}`} onClick={() => onToggleBattle(false)}>
          🔥 Solo Roast
        </button>
        <button className={`mode-tab ${battleMode ? 'active' : ''}`} onClick={() => onToggleBattle(true)}>
          ⚔️ Battle Mode
        </button>
      </div>

      {!battleMode && (
        <>
          <PersonaSelector selected={persona} onSelect={onPersonaChange} />
          <div className="input-wrap">
            <input
              type="text"
              placeholder="Paste your Solana wallet address..."
              autoComplete="off"
              spellCheck="false"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSubmit()}
            />
            <button className="btn" onClick={handleSubmit}>ROAST ME 🔥</button>
          </div>
          <div className="wallet-connect-divider">
            <span className="divider-line"></span>
            <span className="divider-text">OR</span>
            <span className="divider-line"></span>
          </div>
          <WalletButton />
          <div className="examples">
            Try a famous wallet:{' '}
            {EXAMPLES.map(ex => (
              <span key={ex.name} onClick={() => { setInput(ex.addr); onRoast(ex.addr, persona); }}>
                {ex.name}
              </span>
            ))}
          </div>
        </>
      )}

      {stats && stats.total_roasts > 0 && (
        <div className="hero-stats-banner">
          <div className="hero-stat-item">
            <span className="hero-stat-num">🔥 {animatedRoasts.toLocaleString()}</span>
            <span className="hero-stat-label">wallets roasted</span>
          </div>
          <div className="hero-stat-divider" />
          <div className="hero-stat-item">
            <span className="hero-stat-num">📊 {animatedScore}</span>
            <span className="hero-stat-label">avg degen score</span>
          </div>
        </div>
      )}
    </div>
  );
}
