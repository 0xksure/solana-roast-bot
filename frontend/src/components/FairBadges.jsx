import React from 'react';

const TIER_ICONS = {
  platinum: '💎',
  gold: '🥇',
  silver: '🥈',
  bronze: '🥉',
};

export default function FairBadges({ badges }) {
  if (!badges || badges.length === 0) return null;

  return (
    <div className="fair-badges">
      <div className="fair-badges-title">🏆 Reputation Badges</div>
      <div className="fair-badges-list">
        {badges.map((badge, i) => (
          <div
            key={badge.id || i}
            className={`fair-badge fair-badge-${badge.tier || 'bronze'}`}
          >
            <span className="fair-badge-icon">
              {TIER_ICONS[badge.tier] || '🏅'}
            </span>
            <div className="fair-badge-info">
              <span className="fair-badge-name">{badge.label || badge.id}</span>
              {badge.description && (
                <span className="fair-badge-desc">{badge.description}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
