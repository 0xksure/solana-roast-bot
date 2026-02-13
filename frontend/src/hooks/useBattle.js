import { useState, useCallback } from 'react';
import { fetchBattle, mp } from '../utils/api';

const WALLET_RE = /^[1-9A-HJ-NP-Za-km-z]{32,44}$/;

export function useBattle() {
  const [battle, setBattle] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const doBattle = useCallback(async (wallet1, wallet2) => {
    const w1 = wallet1.trim();
    const w2 = wallet2.trim();
    if (!w1 || !w2) { setError('Enter both wallet addresses'); return; }
    if (!WALLET_RE.test(w1)) { setError('Invalid first wallet address'); return; }
    if (!WALLET_RE.test(w2)) { setError('Invalid second wallet address'); return; }
    if (w1 === w2) { setError("Can't battle yourself... or can you? 🤔 Use different wallets."); return; }

    mp('battle_started', { wallet1: w1.slice(0, 8), wallet2: w2.slice(0, 8) });
    setLoading(true);
    setError(null);
    setBattle(null);

    try {
      const data = await fetchBattle(w1, w2);
      setBattle(data);
      mp('battle_completed', { wallet1: w1.slice(0, 8), wallet2: w2.slice(0, 8) });
    } catch (e) {
      setError(e.message);
      mp('battle_failed', { error: e.message });
    } finally {
      setLoading(false);
    }
  }, []);

  const resetBattle = useCallback(() => {
    setBattle(null);
    setError(null);
    setLoading(false);
  }, []);

  return { battle, loading, error, doBattle, resetBattle };
}
