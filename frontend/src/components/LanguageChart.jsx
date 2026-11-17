import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

export default function LanguageChart({ languages }) {
  if (!languages || languages.length === 0) {
    return (
      <section className="section-card">
        <div className="section-header">
          <h2 className="section-title">Programming Languages</h2>
          <span className="section-subtitle">Primary Repository Languages</span>
        </div>
        <p style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
          No primary programming language metadata was detected among original public repositories.
        </p>
      </section>
    );
  }

  // Reverse data so highest count appears at top of vertical BarChart
  const chartData = [...languages].reverse();

  return (
    <section className="section-card">
      <div className="section-header">
        <div>
          <h2 className="section-title">Programming Languages</h2>
          <span className="section-subtitle">
            Repository count by primary language (top 5 across original repositories)
          </span>
        </div>
      </div>

      <div className="language-chart-container">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
          >
            <XAxis type="number" stroke="#64716A" fontSize={11} allowDecimals={false} />
            <YAxis
              dataKey="language"
              type="category"
              stroke="#202825"
              fontSize={12}
              tickLine={false}
              axisLine={{ stroke: '#E2E7E1' }}
              width={90}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#FFFFFF',
                borderColor: '#E2E7E1',
                borderRadius: '8px',
                fontSize: '12px',
                boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
              }}
              formatter={(value, name, props) => [
                `${value} repos (${props.payload.percentage}%)`,
                'Primary Language',
              ]}
            />
            <Bar dataKey="count" fill="#47735C" radius={[0, 4, 4, 0]} barSize={18} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div style={{ marginTop: '8px', fontSize: '12px', color: 'var(--text-secondary)' }}>
        Note: Primary language reflects repository metadata configured on GitHub, not individual lines of code or total complexity.
      </div>
    </section>
  );
}
