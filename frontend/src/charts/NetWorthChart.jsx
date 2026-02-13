import React, { useRef, useEffect } from 'react';
import { Line } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip } from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip);

export default function NetWorthChart({ timeline }) {
  if (!timeline?.length) return null;

  const data = {
    labels: timeline.map(d => d.month),
    datasets: [{
      label: 'Est. USD Value',
      data: timeline.map(d => d.estimated_usd),
      borderColor: '#00f0ff',
      backgroundColor: (ctx) => {
        const chart = ctx.chart;
        const { ctx: c, chartArea } = chart;
        if (!chartArea) return 'rgba(153,69,255,0.4)';
        const g = c.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
        g.addColorStop(0, 'rgba(153,69,255,0.4)');
        g.addColorStop(1, 'rgba(153,69,255,0)');
        return g;
      },
      fill: true,
      tension: 0.4,
      pointRadius: 2,
      borderWidth: 2,
    }],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { color: 'rgba(153,69,255,0.08)' } },
      y: { grid: { color: 'rgba(153,69,255,0.08)' }, ticks: { callback: v => '$' + v.toLocaleString() } },
    },
  };

  return (
    <div className="chart-card">
      <h4>💰 Net Worth Over Time</h4>
      <div style={{ height: 300 }}>
        <Line data={data} options={options} />
      </div>
    </div>
  );
}
