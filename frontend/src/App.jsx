import React, { useEffect, useState, useRef } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import Navbar from './components/Navbar';
import Hero from './components/Hero';
import Loading from './components/Loading';
import RoastResult from './components/RoastResult';
import WalletAutopsy from './components/WalletAutopsy';
import StatsCards from './components/StatsCards';
import ShareActions from './components/ShareActions';
import RecentRoasts from './components/RecentRoasts';
import Footer from './components/Footer';
import { useRoast } from './hooks/useRoast';

export default function App() {
  const { roast, loading, error, wallet, doRoast, reset } = useRoast();
  const { publicKey } = useWallet();
  const prevKey = useRef(null);

  // Auto-roast when wallet connects
  useEffect(() => {
    if (publicKey) {
      const addr = publicKey.toBase58();
      if (addr !== prevKey.current) {
        prevKey.current = addr;
        doRoast(addr);
      }
    }
  }, [publicKey, doRoast]);

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

  return (
    <>
      <Navbar onReset={reset} />
      <div className="container">
        {!loading && !roast && (
          <Hero onRoast={doRoast} error={error} />
        )}

        {error && !loading && !roast && (
          <div className="error active">💀 {error}</div>
        )}

        {loading && <Loading />}

        <FireParticles active={!!roast && !loading} />

        {roast && !loading && (
          <div className="result active">
            <div className="result-card">
              <RoastResult roast={roast} wallet={wallet} />
              <StatsCards stats={roast.wallet_stats} />
              <WalletAutopsy stats={roast.wallet_stats} />
              <ShareActions roast={roast} wallet={wallet} onReset={reset} />
            </div>
          </div>
        )}

        {!loading && <RecentRoasts visible={!roast} />}
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
