import React from 'react';

export default function Achievements({ achievements, percentile }) {
  if (!achievements?.length && percentile == null) return null;

  return (
    <div className="achievements-section">
      {percentile != null && (
        <div className="percentile-banner">
          <span className="percentile-text">
            More degen than <span className="percentile-num">{Math.round(percentile)}%</span> of wallets roasted
          </span>
        </div>
      )}
      {achievements?.length > 0 && (
        <div className="achievements-grid">
          {achievements.map((a, i) => (
            <div className="achievement-badge" key={i} style={{ animationDelay: `${i * 0.1}s` }}>
              <span className="achievement-icon">{a.icon}</span>
              <span className="achievement-name">{a.name}</span>
              <span className="achievement-desc">{a.desc}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
