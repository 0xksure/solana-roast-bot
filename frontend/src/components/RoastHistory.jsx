import React, { useEffect, useState } from 'react';

export default function RoastHistory({ wallet }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!wallet) return;
    setLoading(true);
    fetch(`/api/roast/${wallet}/history`)
      .then(r => r.json())
      .then(data => {
        // Skip the first entry (current roast)
        setHistory(data.slice(1));
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [wallet]);

  if (loading || history.length === 0) return null;

  return (
    <div className="roast-history">
      <div className="roast-history-badge">
        🔥 Roasted {history.length + 1} times
      </div>
      <h3 className="roast-history-title">📜 Past Roasts</h3>
      <div className="roast-history-list">
        {history.map((item, i) => {
          const r = item.roast;
          const date = new Date(item.created_at * 1000).toLocaleDateString();
          return (
            <div key={i} className="roast-history-item">
              <div className="roast-history-item-header">
                <span className="roast-history-item-title">"{r.title}"</span>
                <span className="roast-history-item-score">{r.degen_score}/100</span>
              </div>
              <div className="roast-history-item-date">{date}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
