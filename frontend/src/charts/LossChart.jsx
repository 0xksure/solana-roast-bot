import React from 'react';
import { Bar } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Tooltip } from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip);

export default function LossChart({ losses }) {
  if (!losses?.length) return null;
  const top5 = losses.slice(0, 5);

  const data = {
    labels: top5.map(d => d.token),
    datasets: [{
      label: 'SOL Lost',
      data: top5.map(d => d.sol_lost),
      backgroundColor: 'rgba(239,68,68,0.7)',
      borderColor: '#ef4444',
      borderWidth: 1,
      borderRadius: 4,
    }],
  };

  const options = {
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { color: 'rgba(153,69,255,0.08)' }, ticks: { callback: v => v + ' SOL' } },
      y: { grid: { display: false } },
    },
  };

  return (
    <div className="chart-card">
      <h4>💸 Where You Lost Money</h4>
      <div style={{ height: 300 }}>
        <Bar data={data} options={options} />
      </div>
    </div>
  );
}
