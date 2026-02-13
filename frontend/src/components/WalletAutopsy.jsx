import React from 'react';
import NetWorthChart from '../charts/NetWorthChart';
import ProtocolChart from '../charts/ProtocolChart';
import ActivityChart from '../charts/ActivityChart';
import LossChart from '../charts/LossChart';

export default function WalletAutopsy({ stats }) {
  if (!stats) return null;

  const hasTimeline = stats.net_worth_timeline?.length > 0;
  const hasProtocol = stats.protocol_stats?.length > 0;
  const hasLoss = stats.loss_by_token?.length > 0;

  if (!hasTimeline && !hasProtocol && !hasLoss) return null;

  const autopsyStats = [
    [stats.total_sol_volume ? stats.total_sol_volume.toFixed(1) + ' SOL' : '—', 'Volume Traded'],
    [stats.win_rate != null ? Math.round(stats.win_rate * 100) + '%' : '—', 'Win Rate'],
    [stats.biggest_loss ? stats.biggest_loss.sol_spent + ' SOL' : '—', 'Biggest Loss'],
    [hasProtocol ? stats.protocol_stats[0].name : '—', 'Top Protocol'],
    [stats.graveyard_tokens ?? '—', 'Graveyard Tokens'],
    [stats.peak_activity_period ? stats.peak_activity_period.period : '—', 'Peak Month'],
  ];

  return (
    <div className="autopsy-section">
      <div className="autopsy-title">📊 Your Wallet Autopsy</div>
      <div className="autopsy-stats-row">
        {autopsyStats.map(([val, label], i) => (
          <div className="autopsy-stat" key={i}>
            <div className="val">{val}</div>
            <div className="label">{label}</div>
          </div>
        ))}
      </div>
      {hasTimeline && <NetWorthChart timeline={stats.net_worth_timeline} />}
      {hasProtocol && <ProtocolChart protocols={stats.protocol_stats} />}
      {hasTimeline && <ActivityChart timeline={stats.net_worth_timeline} />}
      {hasLoss && <LossChart losses={stats.loss_by_token} />}
    </div>
  );
}
