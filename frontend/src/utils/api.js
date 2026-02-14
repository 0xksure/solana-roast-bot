export function mp(event, props) {
  try {
    if (window.mixpanel && typeof window.mixpanel.track === 'function') {
      window.mixpanel.track(event, props);
    }
  } catch (e) { /* ignore */ }
}

export async function fetchRoast(wallet, persona = 'degen') {
  const res = await fetch('/api/roast', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ wallet, persona }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Error ${res.status}`);
  }
  return res.json();
}

export async function fetchBattle(wallet1, wallet2) {
  const res = await fetch('/api/battle', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ wallet1, wallet2 }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Error ${res.status}`);
  }
  return res.json();
}

export async function fetchRecent() {
  const res = await fetch('/api/recent');
  return res.json();
}
