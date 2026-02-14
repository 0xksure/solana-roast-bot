import React from 'react';

const PERSONAS = [
  { id: 'degen', name: 'Degen Roaster', icon: '🦍', desc: 'Crypto degen slang, brutal honesty', color: '#9945ff' },
  { id: 'gordon', name: 'Gordon Ramsay', icon: '👨‍🍳', desc: '"This wallet is RAW!"', color: '#ff2d78' },
  { id: 'shakespeare', name: 'Shakespeare', icon: '🎭', desc: 'Thy portfolio doth stinketh', color: '#00f0ff' },
  { id: 'drill_sergeant', name: 'Drill Sergeant', icon: '🎖️', desc: 'DROP AND GIVE ME 20 SOL!', color: '#ff6b2b' },
];

export default function PersonaSelector({ selected, onSelect }) {
  return (
    <div className="persona-selector">
      <div className="persona-label">Choose your roaster:</div>
      <div className="persona-grid">
        {PERSONAS.map(p => (
          <button
            key={p.id}
            className={`persona-card ${selected === p.id ? 'active' : ''}`}
            onClick={() => onSelect(p.id)}
            style={{ '--persona-color': p.color }}
          >
            <span className="persona-icon">{p.icon}</span>
            <span className="persona-name">{p.name}</span>
            <span className="persona-desc">{p.desc}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

export { PERSONAS };
