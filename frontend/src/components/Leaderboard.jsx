import React, { useEffect, useState } from 'react';

export default function Leaderboard({ visible, onRoast }) {
  const [leaders, setLeaders] = useState([]);

  useEffect(() => {
    if (!visible) return;
    fetch('/api/leaderboard')
      .then(r => r.json())
      .then(setLeaders)
      .catch(() => {});
  }, [visible]);

  if (!visible || !leaders.length) return null;

  return (
    <div className="leaderboard">
      <h3>🏆 Degen Leaderboard</h3>
      <div className="leaderboard-list">
        {leaders.map((l, i) => (
          <div
            className={`leaderboard-item ${i < 3 ? 'top-' + (i + 1) : ''}`}
            key={i}
            onClick={() => onRoast && onRoast(l.wallet)}
            style={{ cursor: onRoast ? 'pointer' : 'default' }}
          >
            <span className="lb-rank">
              {i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `#${i + 1}`}
            </span>
            <span className="lb-title">"{l.title}"</span>
            <span className="lb-wallet">{l.wallet.slice(0, 4)}...{l.wallet.slice(-4)}</span>
            <span className="lb-score" data-score={l.degen_score}>{l.degen_score}/100</span>
          </div>
        ))}
      </div>
    </div>
  );
}
