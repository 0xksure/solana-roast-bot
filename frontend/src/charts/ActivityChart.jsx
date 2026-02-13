import React from 'react';
import { Bar } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Tooltip } from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip);

export default function ActivityChart({ timeline }) {
  if (!timeline?.length) return null;
  const maxTx = Math.max(...timeline.map(d => d.tx_count));

  const data = {
    labels: timeline.map(d => d.month),
    datasets: [{
      label: 'Transactions',
      data: timeline.map(d => d.tx_count),
      backgroundColor: timeline.map(d => {
        const r = d.tx_count / (maxTx || 1);
        return r > 0.66 ? '#ff2d78' : r > 0.33 ? '#ff6b2b' : '#00f0ff';
      }),
      borderRadius: 4,
    }],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { display: false } },
      y: { grid: { color: 'rgba(153,69,255,0.08)' } },
    },
  };

  return (
    <div className="chart-card">
      <h4>📈 Monthly Activity</h4>
      <div style={{ height: 300 }}>
        <Bar data={data} options={options} />
      </div>
    </div>
  );
}
