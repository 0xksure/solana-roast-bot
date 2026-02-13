import React, { useState } from 'react';

export default function BattleMode({ onBattle, error }) {
  const [wallet1, setWallet1] = useState('');
  const [wallet2, setWallet2] = useState('');

  const handleSubmit = () => {
    if (wallet1.trim() && wallet2.trim()) onBattle(wallet1.trim(), wallet2.trim());
  };

  return (
    <div className="battle-mode">
      <div className="battle-header">
        <h2 className="battle-title">⚔️ ROAST BATTLE</h2>
        <p className="battle-subtitle">Pit two wallets against each other. Who's the bigger degen?</p>
      </div>
      <div className="battle-inputs">
        <div className="battle-input-card">
          <label className="battle-label">🔴 CHALLENGER 1</label>
          <input
            type="text"
            placeholder="Paste wallet address..."
            autoComplete="off"
            spellCheck="false"
            value={wallet1}
            onChange={e => setWallet1(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSubmit()}
          />
        </div>
        <div className="battle-vs-divider">
          <span className="vs-text">VS</span>
        </div>
        <div className="battle-input-card">
          <label className="battle-label">🔵 CHALLENGER 2</label>
          <input
            type="text"
            placeholder="Paste wallet address..."
            autoComplete="off"
            spellCheck="false"
            value={wallet2}
            onChange={e => setWallet2(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSubmit()}
          />
        </div>
      </div>
      <button className="btn battle-btn" onClick={handleSubmit}>
        START BATTLE ⚔️
      </button>
      {error && <div className="error active" style={{ marginTop: 16 }}>💀 {error}</div>}
    </div>
  );
}
