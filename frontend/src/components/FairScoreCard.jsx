import React, { useEffect, useRef } from 'react';
import FairBadges from './FairBadges';

const TIER_COLORS = {
  platinum: { bg: '#E5E4E2', text: '#1a1a2e', glow: 'rgba(229,228,226,0.4)' },
  gold: { bg: '#FFD700', text: '#1a1a2e', glow: 'rgba(255,215,0,0.4)' },
  silver: { bg: '#C0C0C0', text: '#1a1a2e', glow: 'rgba(192,192,192,0.4)' },
  bronze: { bg: '#CD7F32', text: '#fff', glow: 'rgba(205,127,50,0.4)' },
};

export default function FairScoreCard({ fairscale, degenScore }) {
  const scoreRef = useRef(null);
  const fairscore = fairscale?.fairscore || 0;
  const tier = fairscale?.tier || 'unknown';
  const colors = TIER_COLORS[tier] || { bg: '#666', text: '#fff', glow: 'rgba(100,100,100,0.3)' };

  useEffect(() => {
    const el = scoreRef.current;
    if (!el) return;
    const start = performance.now();
    const duration = 1200;
    function update(now) {
      const p = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      el.textContent = (fairscore * eased).toFixed(1);
      if (p < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
  }, [fairscore]);

  // Determine trust-vs-degen persona
  const persona = getPersona(fairscore, degenScore);

  return (
    <div className="fairscore-card" style={{ '--tier-glow': colors.glow }}>
      <div className="fairscore-header">
        <span className="fairscore-icon">🛡️</span>
        <span className="fairscore-title">REPUTATION SCORE</span>
        <span className="fairscore-powered">powered by FairScale</span>
      </div>

      <div className="fairscore-body">
        <div className="fairscore-score-wrap">
          <div className="fairscore-number" ref={scoreRef}>0</div>
          <div
            className="fairscore-tier"
            style={{ background: colors.bg, color: colors.text }}
          >
            {tier.toUpperCase()}
          </div>
        </div>

        <div className="fairscore-breakdown">
          <div className="fairscore-stat">
            <span className="fairscore-stat-label">Base Score</span>
            <span className="fairscore-stat-value">{fairscale?.fairscore_base?.toFixed(1) || '—'}</span>
          </div>
          <div className="fairscore-stat">
            <span className="fairscore-stat-label">Social Score</span>
            <span className="fairscore-stat-value">{fairscale?.social_score?.toFixed(1) || '—'}</span>
          </div>
          {fairscale?.features?.wallet_age_days && (
            <div className="fairscore-stat">
              <span className="fairscore-stat-label">Wallet Age</span>
              <span className="fairscore-stat-value">{fairscale.features.wallet_age_days}d</span>
            </div>
          )}
          {fairscale?.features?.active_days && (
            <div className="fairscore-stat">
              <span className="fairscore-stat-label">Active Days</span>
              <span className="fairscore-stat-value">{fairscale.features.active_days}</span>
            </div>
          )}
        </div>
      </div>

      <div className="fairscore-persona">{persona}</div>

      {fairscale?.badges?.length > 0 && (
        <FairBadges badges={fairscale.badges} />
      )}
    </div>
  );
}

function getPersona(fairscore, degenScore) {
  const highTrust = fairscore >= 50;
  const highDegen = degenScore >= 60;

  if (highTrust && highDegen) return '🤝🔥 Trusted Degen — respected by the chain, feared by your portfolio';
  if (highTrust && !highDegen) return '🏛️ Respectable Builder — boring but your mom would be proud';
  if (!highTrust && highDegen) return '👻 Anonymous Ape — no reputation, all risk, zero chill';
  return '🧊 Ghost — the chain barely knows you exist';
}
