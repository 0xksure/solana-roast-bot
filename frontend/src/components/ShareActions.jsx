import React, { useState } from 'react';
import { mp } from '../utils/api';

export default function ShareActions({ roast, wallet, onReset }) {
  const [copied, setCopied] = useState(false);

  const shareTwitter = () => {
    mp('share_twitter', { degen_score: roast?.degen_score });
    if (!roast) return;
    const text = `My Solana wallet got roasted 🔥\n\nI'm "${roast.title}" with a ${roast.degen_score}/100 degen score.\n\nThink you can handle it?`;
    const url = window.location.origin + '/' + wallet;
    window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`, '_blank');
  };

  const copyLink = () => {
    if (!wallet) return;
    const url = window.location.origin + '/' + wallet;
    navigator.clipboard.writeText(url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const downloadCard = () => {
    mp('download_card', { degen_score: roast?.degen_score });
    if (wallet) window.open(`/api/roast/${wallet}/image`, '_blank');
  };

  return (
    <div className="actions">
      <button className="btn-twitter" onClick={shareTwitter}>Share on 𝕏</button>
      <button className="btn-secondary btn-copy" onClick={copyLink}>
        🔗 Copy Link
        <span className={`copied ${copied ? 'show' : ''}`}>Copied!</span>
      </button>
      <button className="btn-secondary" onClick={downloadCard}>📥 Download Card</button>
      <button className="btn-secondary" onClick={onReset}>🔥 Roast Another</button>
    </div>
  );
}
