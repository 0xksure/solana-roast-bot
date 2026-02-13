import React from 'react';

export default function Navbar({ onReset }) {
  return (
    <nav className="navbar">
      <div className="navbar-left" onClick={onReset} style={{ cursor: 'pointer' }}>
        <img src="/img/logo.jpg" alt="Logo" className="navbar-logo" />
        <span className="navbar-title">SOLANA ROAST BOT</span>
      </div>
      <div className="navbar-right">
        <span className="live-indicator"><span className="live-dot"></span> LIVE</span>
        <a href="https://github.com/0xksure/solana-roast-bot" target="_blank" rel="noreferrer" className="nav-link">GitHub</a>
      </div>
    </nav>
  );
}
