import React from 'react';

function StatBar({ label, val1, val2, fmt }) {
  const f = fmt || (v => v);
  const max = Math.max(val1 || 0, val2 || 0, 1);
  const p1 = ((val1 || 0) / max) * 100;
  const p2 = ((val2 || 0) / max) * 100;
  const w1 = (val1 || 0) > (val2 || 0);
  const w2 = (val2 || 0) > (val1 || 0);

  return (
    <div className="stat-bar-row">
      <span className={`stat-bar-val left ${w1 ? 'winner' : ''}`}>{f(val1)}</span>
      <div className="stat-bar-center">
        <div className="stat-bar-track">
          <div className="stat-bar-fill left" style={{ width: `${p1}%` }} />
        </div>
        <span className="stat-bar-label">{label}</span>
        <div className="stat-bar-track">
          <div className="stat-bar-fill right" style={{ width: `${p2}%` }} />
        </div>
      </div>
      <span className={`stat-bar-val right ${w2 ? 'winner' : ''}`}>{f(val2)}</span>
    </div>
  );
}

function short(addr) {
  return addr ? addr.slice(0, 4) + '...' + addr.slice(-4) : '???';
}

export default function BattleResult({ battle, onReset }) {
  const { roast1, roast2, wallet1, wallet2, battle_summary } = battle;
  const s1 = roast1.wallet_stats || {};
  const s2 = roast2.wallet_stats || {};
  const score1 = roast1.degen_score || 0;
  const score2 = roast2.degen_score || 0;
  const winner = score1 >= score2 ? 1 : 2;

  const pct = v => `${(v * 100).toFixed(0)}%`;
  const sol = v => `${(v || 0).toFixed(2)}`;

  return (
    <div className="battle-result">
      <h2 className="battle-result-title">⚔️ BATTLE RESULTS</h2>

      <div className="battle-cards">
        <div className={`battle-card ${winner === 1 ? 'winner-card' : ''}`}>
          {winner === 1 && <div className="crown">👑</div>}
          <div className="battle-card-wallet">{short(wallet1)}</div>
          <div className="battle-card-title">{roast1.title}</div>
          <div className="battle-card-score" style={{ color: score1 >= 70 ? 'var(--orange)' : score1 >= 40 ? 'var(--yellow)' : 'var(--cyan)' }}>
            {score1}<span className="score-of">/100</span>
          </div>
          <div className="battle-card-lines">
            {(roast1.roast_lines || []).slice(0, 3).map((l, i) => (
              <p key={i} className="battle-roast-line">{l}</p>
            ))}
          </div>
        </div>

        <div className="battle-vs-center">
          <span className="vs-glow">VS</span>
        </div>

        <div className={`battle-card ${winner === 2 ? 'winner-card' : ''}`}>
          {winner === 2 && <div className="crown">👑</div>}
          <div className="battle-card-wallet">{short(wallet2)}</div>
          <div className="battle-card-title">{roast2.title}</div>
          <div className="battle-card-score" style={{ color: score2 >= 70 ? 'var(--orange)' : score2 >= 40 ? 'var(--yellow)' : 'var(--cyan)' }}>
            {score2}<span className="score-of">/100</span>
          </div>
          <div className="battle-card-lines">
            {(roast2.roast_lines || []).slice(0, 3).map((l, i) => (
              <p key={i} className="battle-roast-line">{l}</p>
            ))}
          </div>
        </div>
      </div>

      <div className="battle-stats-comparison">
        <h3 className="comparison-title">📊 STAT COMPARISON</h3>
        <StatBar label="SOL Balance" val1={s1.sol_balance} val2={s2.sol_balance} fmt={sol} />
        <StatBar label="Tokens" val1={s1.token_count} val2={s2.token_count} />
        <StatBar label="Fail Rate" val1={s1.failure_rate} val2={s2.failure_rate} fmt={v => `${v || 0}%`} />
        <StatBar label="Swaps" val1={s1.swap_count} val2={s2.swap_count} />
        <StatBar label="Degen Score" val1={score1} val2={score2} />
        <StatBar label="Win Rate" val1={s1.win_rate} val2={s2.win_rate} fmt={pct} />
      </div>

      {battle_summary && (
        <div className="battle-verdict">
          <h3>🏆 VERDICT</h3>
          <p className="verdict-text">{battle_summary.verdict}</p>
          <p className="verdict-winner">
            {battle_summary.winner === 'wallet1' ? `${short(wallet1)} wins!` : `${short(wallet2)} wins!`}
          </p>
        </div>
      )}

      <div className="actions" style={{ marginTop: 24 }}>
        <button className="btn-secondary" onClick={onReset}>🔄 New Battle</button>
        <button className="btn-twitter" onClick={() => {
          const text = `⚔️ Solana Roast Battle!\n\n${short(wallet1)} (${score1}/100) vs ${short(wallet2)} (${score2}/100)\n\n${battle_summary?.verdict || ''}\n\nBattle your friend 👉 solanaroast.xyz`;
          window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}`, '_blank');
        }}>Share on 𝕏</button>
      </div>
    </div>
  );
}
