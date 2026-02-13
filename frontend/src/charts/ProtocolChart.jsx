import React from 'react';
import { Doughnut } from 'react-chartjs-2';
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';

ChartJS.register(ArcElement, Tooltip, Legend);

const COLORS = ['#00f0ff', '#9945ff', '#ff6b2b', '#ff2d78', '#22c55e'];
const SKIP = ['System', 'Token Program', 'Associated Token'];

const centerTextPlugin = {
  id: 'centerText',
  beforeDraw(chart) {
    const { ctx, width, height } = chart;
    const total = chart.data.datasets[0].data.reduce((s, v) => s + v, 0);
    ctx.save();
    ctx.font = 'bold 24px Orbitron';
    ctx.fillStyle = '#00f0ff';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(total, width / 2, height / 2 - 8);
    ctx.font = '11px Inter';
    ctx.fillStyle = '#7c7394';
    ctx.fillText('interactions', width / 2, height / 2 + 14);
    ctx.restore();
  },
};

export default function ProtocolChart({ protocols }) {
  if (!protocols?.length) return null;
  const top5 = protocols.filter(p => !SKIP.includes(p.name)).slice(0, 5);
  if (!top5.length) return null;

  const data = {
    labels: top5.map(p => p.name),
    datasets: [{
      data: top5.map(p => p.tx_count),
      backgroundColor: COLORS.slice(0, top5.length),
      borderWidth: 0,
    }],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '65%',
    plugins: {
      legend: { position: 'bottom', labels: { padding: 16, usePointStyle: true } },
    },
  };

  return (
    <div className="chart-card">
      <h4>🔄 Protocol Usage</h4>
      <div style={{ height: 300 }}>
        <Doughnut data={data} options={options} plugins={[centerTextPlugin]} />
      </div>
    </div>
  );
}
