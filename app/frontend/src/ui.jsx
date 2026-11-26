import { useEffect, useRef } from 'react';
import Chart from 'chart.js/auto';

export function Badge({ tone = 'info', children }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

export function Tile({ label, value, color }) {
  return <div className="tile"><div className="l">{label}</div>
    <div className="v" style={{ color, overflowWrap: 'anywhere' }}>{value ?? '—'}</div>
  </div>;
}

export function Empty({ children }) {
  return <div className="empty">{children}</div>;
}

export function Card({ title, note, action, children }) {
  return <div className="card">
    <div className="card-head"><h2>{title}</h2>{note && <span className="submuted">{note}</span>}{action}</div>
    {children}
  </div>;
}

export const scoreTone = score => score >= 80 ? 'good' : score >= 60 ? 'warn' : 'crit';
export const missingTone = value => value >= 15 ? 'crit' : value >= 5 ? 'warn' : 'good';
export const percent = (value, digits = 1) => value == null ? '—' : `${Number(value).toFixed(digits)}%`;
export const severityTone = severity => ({ CRITICAL: 'crit', HIGH: 'warn', MEDIUM: 'warn', INFO: 'info', LOW: 'good' })[severity] || 'warn';

const axis = { ticks: { color: '#8a98b0' }, grid: { color: 'rgba(38,55,88,.55)' } };

export function Plot({ title, type = 'bar', labels, series, size = 'md', suffix = '', legend = false, min, max }) {
  const canvas = useRef(null);
  useEffect(() => {
    const chart = new Chart(canvas.current, {
      type,
      data: {
        labels,
        datasets: series.map(({ color, values, ...options }) => ({
          data: values,
          backgroundColor: color,
          borderColor: type === 'line' ? color : undefined,
          borderRadius: 5,
          tension: .3,
          ...options,
        })),
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: legend, position: 'bottom', labels: { color: '#8a98b0' } } },
        scales: type === 'doughnut' ? {} : {
          x: axis,
          y: {
            ...axis, min, max, beginAtZero: min == null && type === 'bar',
            ticks: { ...axis.ticks, callback: value => `${value}${suffix}` },
          },
        },
      },
    });
    return () => chart.destroy();
  }, [type, labels, series, suffix, legend, min, max]);

  return <div className={`chart-wrap ${size}`}><canvas ref={canvas} role="img" aria-label={title} /></div>;
}
