import React, { useState, useEffect, useRef } from 'react';

const MSGS = [
  "Scanning your bad decisions...",
  "Counting your failed txns...",
  "Calculating your paper hands score...",
  "Reading your portfolio... yikes...",
  "Consulting the blockchain oracle...",
  "Measuring your copium levels...",
  "Analyzing your rug pull history...",
  "Computing your L/W ratio...",
  "Checking if you've touched grass recently...",
  "Rating your shitcoin collection..."
];

export default function Loading() {
  const [msg, setMsg] = useState(MSGS[0]);
  const [progress, setProgress] = useState(0);
  const idx = useRef(0);

  useEffect(() => {
    const msgTimer = setInterval(() => {
      idx.current = (idx.current + 1) % MSGS.length;
      setMsg(MSGS[idx.current]);
    }, 2200);

    const progTimer = setInterval(() => {
      setProgress(prev => {
        if (prev < 30) return prev + 3;
        if (prev < 70) return prev + 1.5;
        if (prev < 95) return prev + 0.3;
        return prev;
      });
    }, 200);

    return () => { clearInterval(msgTimer); clearInterval(progTimer); };
  }, []);

  const pct = Math.round(Math.min(progress, 95));

  return (
    <div className="loading active">
      <div className="loading-terminal">
        <div style={{ color: 'var(--cyan)', marginBottom: 8 }}>root@solana-roast:~$</div>
        <div className="loading-msg">{msg}</div>
      </div>
      <div style={{ marginTop: 20 }}>
        <div className="progress-wrap">
          <div className="progress-bar" style={{ width: pct + '%' }} />
        </div>
        <div className="loading-pct">{pct}%</div>
      </div>
    </div>
  );
}
