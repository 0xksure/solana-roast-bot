import React, { useEffect, useState, useRef } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import Navbar from './components/Navbar';
import Hero from './components/Hero';
import Loading from './components/Loading';
import RoastResult from './components/RoastResult';
import WalletAutopsy from './components/WalletAutopsy';
import StatsCards from './components/StatsCards';
import Achievements from './components/Achievements';
import ShareActions from './components/ShareActions';
import Leaderboard from './components/Leaderboard';
import RecentRoasts from './components/RecentRoasts';
import Footer from './components/Footer';
import BattleMode from './components/BattleMode';
import BattleResult from './components/BattleResult';
import FairScoreCard from './components/FairScoreCard';
import TrustDegenRadar from './components/TrustDegenRadar';
import ReputationLeaderboard from './components/ReputationLeaderboard';
import { useRoast } from './hooks/useRoast';
import { useBattle } from './hooks/useBattle';

export default function App() {
  const { roast, loading, error, wallet, doRoast, reset } = useRoast();
  const { battle, loading: battleLoading, error: battleError, doBattle, resetBattle } = useBattle();
  const { publicKey } = useWallet();
  const prevKey = useRef(null);
  const [battleMode, setBattleMode] = useState(false);

  // Auto-roast when wallet connects
  useEffect(() => {
    if (publicKey && !battleMode) {
      const addr = publicKey.toBase58();
      if (addr !== prevKey.current) {
        prevKey.current = addr;
        doRoast(addr);
      }
    }
  }, [publicKey, doRoast, battleMode]);

  // URL param on mount
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const w = params.get('wallet');
    if (w) {
      doRoast(w);
      return;
    }
    const path = window.location.pathname.slice(1);
    if (path && /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(path)) {
      doRoast(path);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleReset = () => {
    reset();
    resetBattle();
  };

  const isLoading = loading || battleLoading;
  const hasResult = roast || battle;

  return (
    <>
      <Navbar onReset={handleReset} />
      <div className="container">
        {!isLoading && !hasResult && (
          <>
            <Hero onRoast={doRoast} error={error} battleMode={battleMode} onToggleBattle={setBattleMode} />
            {battleMode && <BattleMode onBattle={doBattle} error={battleError} />}
          </>
        )}

        {error && !isLoading && !hasResult && !battleMode && (
          <div className="error active">💀 {error}</div>
        )}

        {isLoading && <Loading />}

        <FireParticles active={!!hasResult && !isLoading} />

        {roast && !loading && !battleMode && (
          <div className="result active">
            <div className="result-card">
              <RoastResult roast={roast} wallet={wallet} />
              <Achievements achievements={roast.achievements} percentile={roast.percentile} />
              {roast.fairscale && (
                <>
                  <FairScoreCard fairscale={roast.fairscale} degenScore={roast.degen_score} />
                  <TrustDegenRadar fairscale={roast.fairscale} walletStats={{...roast.wallet_stats, degen_score: roast.degen_score}} />
                </>
              )}
              <StatsCards stats={roast.wallet_stats} />
              <WalletAutopsy stats={roast.wallet_stats} />
              <ShareActions roast={roast} wallet={wallet} onReset={handleReset} />
            </div>
          </div>
        )}

        {battle && !battleLoading && (
          <BattleResult battle={battle} onReset={() => { resetBattle(); setBattleMode(true); }} />
        )}

        {!isLoading && !hasResult && <Leaderboard visible={!hasResult} onRoast={doRoast} />}
        {!isLoading && !hasResult && <ReputationLeaderboard visible={!hasResult} onRoast={doRoast} />}
        {!isLoading && !hasResult && <RecentRoasts visible={!hasResult} onRoast={doRoast} />}
        <Footer />
      </div>
    </>
  );
}

function FireParticles({ active }) {
  const [particles, setParticles] = useState([]);

  useEffect(() => {
    if (!active) return;
    const colors = ['#ff6b2b', '#ff2d78', '#9945ff', '#00f0ff', '#ff4500'];
    const ps = Array.from({ length: 40 }, (_, i) => ({
      id: i,
      left: Math.random() * 100 + '%',
      bg: colors[Math.floor(Math.random() * colors.length)],
      duration: (1.5 + Math.random() * 2) + 's',
      delay: Math.random() * 0.8 + 's',
      size: (8 + Math.random() * 10) + 'px',
    }));
    setParticles(ps);
    const t = setTimeout(() => setParticles([]), 4000);
    return () => clearTimeout(t);
  }, [active]);

  if (!particles.length) return null;
  return (
    <div className="fire-particles active">
      {particles.map(p => (
        <div key={p.id} className="fire-particle" style={{
          left: p.left,
          background: p.bg,
          animationDuration: p.duration,
          animationDelay: p.delay,
          width: p.size,
          height: p.size,
        }} />
      ))}
    </div>
  );
}
