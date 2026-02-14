import React from 'react';
import { Radar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
} from 'chart.js';

ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip);

export default function TrustDegenRadar({ fairscale, walletStats }) {
  if (!fairscale) return null;

  const features = fairscale.features || {};
  const degenScore = walletStats?.degen_score || 0;

  // Normalize values to 0-100 range
  const swapFreq = Math.min((walletStats?.swap_count || 0) / 200 * 100, 100);
  const failRate = walletStats?.failure_rate || 0;
  const shitcoinRatio = Math.min((walletStats?.shitcoin_count || 0) / 30 * 100, 100);
  const fairscore = Math.min(fairscale.fairscore || 0, 100);
  const socialScore = Math.min(fairscale.social_score || 0, 100);
  const walletAge = Math.min((features.wallet_age_days || 0) / 730 * 100, 100);

  const data = {
    labels: ['Swap Freq', 'Fail Rate', 'Shitcoins', 'FairScore', 'Social', 'Wallet Age'],
    datasets: [
      {
        label: 'Degen',
        data: [swapFreq, failRate, shitcoinRatio, 0, 0, 0],
        backgroundColor: 'rgba(255, 45, 120, 0.2)',
        borderColor: '#ff2d78',
        borderWidth: 2,
        pointBackgroundColor: '#ff2d78',
      },
      {
        label: 'Trust',
        data: [0, 0, 0, fairscore, socialScore, walletAge],
        backgroundColor: 'rgba(0, 240, 255, 0.2)',
        borderColor: '#00f0ff',
        borderWidth: 2,
        pointBackgroundColor: '#00f0ff',
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (ctx) => `${ctx.dataset.label}: ${ctx.raw.toFixed(0)}`,
        },
      },
    },
    scales: {
      r: {
        min: 0,
        max: 100,
        ticks: { display: false },
        grid: { color: 'rgba(255,255,255,0.08)' },
        angleLines: { color: 'rgba(255,255,255,0.08)' },
        pointLabels: {
          color: 'rgba(255,255,255,0.6)',
          font: { size: 11 },
        },
      },
    },
  };

  return (
    <div className="trust-degen-radar">
      <div className="radar-title">
        <span style={{ color: '#ff2d78' }}>🔥 Degen</span>
        {' vs '}
        <span style={{ color: '#00f0ff' }}>🛡️ Trust</span>
      </div>
      <div className="radar-chart-wrap">
        <Radar data={data} options={options} />
      </div>
    </div>
  );
}
