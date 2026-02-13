import React, { useEffect, useRef } from 'react';

export default function RoastResult({ roast }) {
  const scoreRef = useRef(null);
  const fillRef = useRef(null);
  const score = roast.degen_score || 0;
  const circumference = 2 * Math.PI * 65;
  const offset = circumference - (score / 100) * circumference;

  let strokeColor = '#00f0ff';
  if (score >= 66) strokeColor = '#ff2d78';
  else if (score >= 33) strokeColor = '#ff6b2b';

  useEffect(() => {
    // Animate score number
    const el = scoreRef.current;
    if (!el) return;
    const start = performance.now();
    const duration = 1500;
    function update(now) {
      const p = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(score * eased);
      if (p < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);

    // Animate circle
    if (fillRef.current) {
      fillRef.current.style.strokeDasharray = circumference;
      fillRef.current.style.strokeDashoffset = circumference;
      setTimeout(() => {
        fillRef.current.style.strokeDashoffset = offset;
      }, 100);
    }
  }, [score, circumference, offset]);

  return (
    <>
      <div className="result-title">"{roast.title}"</div>
      <div className="result-summary">{roast.summary}</div>
      <div className="score-wrap">
        <div className="score-circle">
          <div className="score-glow-ring"></div>
          <svg viewBox="0 0 140 140">
            <circle className="score-bg" cx="70" cy="70" r="65" />
            <circle
              className="score-fill"
              ref={fillRef}
              cx="70" cy="70" r="65"
              style={{ stroke: strokeColor, strokeDasharray: circumference, strokeDashoffset: circumference }}
            />
          </svg>
          <div className="score-num" ref={scoreRef}>0</div>
        </div>
        <div className="score-label">DEGEN SCORE</div>
        {roast.score_explanation && (
          <div className="score-expl">{roast.score_explanation}</div>
        )}
      </div>
      <div className="roast-lines">
        {(roast.roast_lines || []).map((line, i) => (
          <div key={i} className="roast-line" style={{ animationDelay: `${0.3 + i * 0.3}s` }}>
            {line}
          </div>
        ))}
      </div>
    </>
  );
}
