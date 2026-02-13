import React, { useEffect, useState } from 'react';
import { fetchRecent } from '../utils/api';

export default function RecentRoasts({ visible }) {
  const [recent, setRecent] = useState([]);

  useEffect(() => {
    fetchRecent().then(setRecent).catch(() => {});
  }, [visible]);

  if (!visible) return null;

  return (
    <div className="recent">
      <h3>Recent Roasts</h3>
      <div>
        {!recent.length ? (
          <div style={{ textAlign: 'center', color: 'var(--muted)', padding: 20 }}>
            No roasts yet. Be the first! 🔥
          </div>
        ) : (
          recent.map((r, i) => (
            <div className="recent-item" key={i}>
              <span className="recent-title">"{r.title}"</span>
              <span className="recent-score">{r.degen_score}/100</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
