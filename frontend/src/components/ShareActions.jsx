import React, { useState } from 'react';
import { mp } from '../utils/api';

export default function ShareActions({ roast, wallet, onReset }) {
  const [copied, setCopied] = useState(false);

  const bestLine = (roast?.roast_lines || [])[0] || '';
  const shortLine = bestLine.length > 100 ? bestLine.slice(0, 97) + '...' : bestLine;
  const url = window.location.origin + '/' + wallet;

  const shareTwitter = () => {
    mp('share_twitter', { degen_score: roast?.degen_score });
    const text = `My Solana wallet got roasted 🔥\n\n"${roast.title}" — ${roast.degen_score}/100 degen score\n\n"${shortLine}"\n\nGet roasted:`;
    window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`, '_blank');
  };

  const challengeFriend = () => {
    mp('challenge_friend', { degen_score: roast?.degen_score });
    const text = `I scored ${roast.degen_score}/100 on the Solana Degen Score.\n\nBet you can't beat that. Paste your wallet and find out 👇`;
    window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(window.location.origin)}`, '_blank');
  };

  const copyLink = () => {
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
      <button className="btn-challenge" onClick={challengeFriend}>⚔️ Challenge a Friend</button>
      <button className="btn-secondary btn-copy" onClick={copyLink}>
        🔗 Copy Link
        <span className={`copied ${copied ? 'show' : ''}`}>Copied!</span>
      </button>
      <button className="btn-secondary" onClick={downloadCard}>📥 Download Card</button>
      <button className="btn-secondary" onClick={onReset}>🔥 Roast Another</button>
    </div>
  );
}
