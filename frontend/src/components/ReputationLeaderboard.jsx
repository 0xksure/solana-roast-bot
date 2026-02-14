import React, { useEffect, useState } from 'react';

const TIER_EMOJI = {
  platinum: '💎',
  gold: '🥇',
  silver: '🥈',
  bronze: '🥉',
};

export default function ReputationLeaderboard({ visible, onRoast }) {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!visible) return;
    fetch('/api/reputation-leaderboard')
      .then(r => r.json())
      .then(data => {
        setEntries(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [visible]);

  if (!visible) return null;
  if (loading) return null;
  if (entries.length === 0) return null;

  return (
    <div className="leaderboard reputation-leaderboard">
      <h3 className="leaderboard-title">🏆 Most Trusted Degens</h3>
      <p className="leaderboard-subtitle">Highest combined degen × reputation score</p>
      <div className="leaderboard-list">
        {entries.map((entry, i) => {
          const short = entry.wallet.slice(0, 4) + '...' + entry.wallet.slice(-4);
          const tierEmoji = TIER_EMOJI[entry.tier] || '🏅';
          return (
            <div
              key={entry.wallet}
              className="leaderboard-row clickable"
              onClick={() => onRoast?.(entry.wallet)}
            >
              <span className="lb-rank">#{i + 1}</span>
              <span className="lb-wallet">{short}</span>
              <span className="lb-tier">{tierEmoji} {(entry.tier || '').toUpperCase()}</span>
              <span className="lb-degen">🔥 {Math.round(entry.degen_score || 0)}</span>
              <span className="lb-fair">🛡️ {(entry.fairscore || 0).toFixed(1)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
