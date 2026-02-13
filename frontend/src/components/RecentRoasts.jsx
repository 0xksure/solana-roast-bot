import React, { useEffect, useState } from 'react';
import { fetchRecent } from '../utils/api';

export default function RecentRoasts({ visible, onRoast }) {
  const [recent, setRecent] = useState([]);

  useEffect(() => {
    if (!visible) return;
    fetchRecent().then(setRecent).catch(() => {});
  }, [visible]);

  if (!visible) return null;

  return (
    <div className="recent">
      <h3>🔥 Recent Roasts</h3>
      <div>
        {!recent.length ? (
          <div style={{ textAlign: 'center', color: 'var(--muted)', padding: 20 }}>
            No roasts yet. Be the first! 🔥
          </div>
        ) : (
          recent.map((r, i) => (
            <div
              className="recent-item"
              key={i}
              onClick={() => onRoast && onRoast(r.wallet)}
              style={{ cursor: onRoast ? 'pointer' : 'default' }}
            >
              <span className="recent-title">"{r.title}"</span>
              <span className="recent-wallet">{r.wallet.slice(0, 4)}...{r.wallet.slice(-4)}</span>
              <span className="recent-score">{r.degen_score}/100</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
