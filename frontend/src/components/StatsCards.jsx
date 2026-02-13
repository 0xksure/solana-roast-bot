import React from 'react';

export default function StatsCards({ stats }) {
  if (!stats) return null;
  const items = [
    [stats.sol_balance ? `${stats.sol_balance} SOL` : '—', 'Balance'],
    [stats.sol_usd ? `$${stats.sol_usd.toLocaleString()}` : '—', 'USD Value'],
    [stats.token_count ?? '—', 'Tokens'],
    [stats.transaction_count ?? '—', 'Transactions'],
    [stats.failed_transactions ?? '—', 'Failed TXs'],
    [stats.wallet_age_days ? `${stats.wallet_age_days}d` : '—', 'Wallet Age'],
    [stats.swap_count ?? '—', 'Swaps'],
    [stats.shitcoin_count ?? '—', 'Shitcoins'],
  ];

  return (
    <div className="stats-grid">
      {items.map(([val, label], i) => (
        <div className="stat-item" key={i}>
          <div className="stat-val">{val}</div>
          <div className="stat-label">{label}</div>
        </div>
      ))}
    </div>
  );
}
