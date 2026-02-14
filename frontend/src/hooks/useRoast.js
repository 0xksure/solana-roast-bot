import { useState, useRef, useCallback } from 'react';
import { fetchRoast, mp } from '../utils/api';

const WALLET_RE = /^[1-9A-HJ-NP-Za-km-z]{32,44}$/;

export function useRoast() {
  const [roast, setRoast] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [wallet, setWallet] = useState('');
  const cache = useRef({});

  const doRoast = useCallback(async (input, persona = 'degen') => {
    const addr = input.trim();
    if (!addr) return;

    mp('roast_started', { wallet: addr.slice(0, 8) + '...', persona });

    if (!WALLET_RE.test(addr)) {
      setError('Invalid Solana wallet address — check and try again');
      return;
    }

    setWallet(addr);
    setLoading(true);
    setError(null);
    setRoast(null);

    const cacheKey = `${addr}:${persona}`;
    try {
      if (cache.current[cacheKey]) {
        setRoast(cache.current[cacheKey]);
        mp('roast_completed', { wallet: addr.slice(0, 8) + '...', degen_score: cache.current[cacheKey].degen_score, title: cache.current[cacheKey].title, persona });
      } else {
        const data = await fetchRoast(addr, persona);
        cache.current[cacheKey] = data;
        setRoast(data);
        mp('roast_completed', { wallet: addr.slice(0, 8) + '...', degen_score: data.degen_score, title: data.title, persona });
      }
      window.history.replaceState({}, '', `/?wallet=${addr}`);
    } catch (e) {
      setError(e.message);
      mp('roast_failed', { wallet: addr.slice(0, 8) + '...', error: e.message });
    } finally {
      setLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setRoast(null);
    setError(null);
    setWallet('');
    setLoading(false);
    window.history.replaceState({}, '', '/');
  }, []);

  return { roast, loading, error, wallet, doRoast, reset };
}
