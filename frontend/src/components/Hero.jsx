import React, { useState, useEffect } from 'react';
import WalletButton from './WalletButton';

const EXAMPLES = [
  { name: 'Toly', addr: 'CKs1E69a2e9TmH4mKKLrXFF8kD3ZnwKjoEuXa6sz9WqX' },
  { name: 'Mert', addr: 'madSoL3Fz7Jm5fFBxEDFmAEJCm588bun5KEiJrb7ivH' },
  { name: 'Whale 🐋', addr: '5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9' },
];

export default function Hero({ onRoast, error, battleMode, onToggleBattle }) {
  const [input, setInput] = useState('');
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetch('/api/stats').then(r => r.json()).then(setStats).catch(() => {});
  }, []);

  const handleSubmit = () => {
    if (input.trim()) onRoast(input.trim());
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
              <span key={ex.name} onClick={() => { setInput(ex.addr); onRoast(ex.addr); }}>
                {ex.name}
              </span>
            ))}
          </div>
        </>
      )}

      {stats && stats.total_roasts > 0 && (
        <div className="hero-stats">
          <span>🔥 <strong>{stats.total_roasts.toLocaleString()}</strong> wallets roasted</span>
          <span>·</span>
          <span>📊 Avg degen score: <strong>{stats.avg_degen_score}</strong>/100</span>
        </div>
      )}
    </div>
  );
}
