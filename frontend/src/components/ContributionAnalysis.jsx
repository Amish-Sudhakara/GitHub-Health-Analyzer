import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

export default function ContributionAnalysis({ contributions, metrics }) {
  if (!contributions || !contributions.available) {
    return (
      <section className="section-card">
        <div className="section-header">
          <h2 className="section-title">Contribution Analysis</h2>
          <span className="section-subtitle">Last 12 Months</span>
        </div>
        <div style={{ color: 'var(--text-secondary)', fontSize: '14px', padding: '12px 0' }}>
          Contribution data is currently unavailable for this user.
          {contributions?.error_reason && (
            <div style={{ marginTop: '8px', fontSize: '13px', color: 'var(--text-secondary)' }}>
              Reason: {contributions.error_reason}
            </div>
          )}
        </div>
      </section>
    );
  }

  const monthlyData = contributions.monthly || [];
  const dailyData = contributions.daily || [];

  // Group days into columns of 7 for GitHub-style calendar
  const weeks = [];
  let currentWeek = [];
  dailyData.forEach((day, index) => {
    currentWeek.push(day);
    if (currentWeek.length === 7 || index === dailyData.length - 1) {
      weeks.push(currentWeek);
      currentWeek = [];
    }
  });

  // Color generator for heatmap based on contribution counts
  const getDayColor = (count, rawColor) => {
    if (count === 0) return '#EBEDF0';
    if (count <= 2) return '#C6E48B';
    if (count <= 5) return '#7BC96F';
    if (count <= 9) return '#47735C';
    return '#254A37';
  };

  return (
    <section className="section-card">
      <div className="section-header">
        <div>
          <h2 className="section-title">Contribution Analysis</h2>
          <span className="section-subtitle">
            Active in {metrics.active_weeks} of {metrics.total_observed_weeks} observed weeks (
            {metrics.total_contributions.toLocaleString()} total contributions)
          </span>
        </div>
      </div>

      {/* Monthly Bar Chart */}
      <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '12px', color: 'var(--text-primary)' }}>
        Monthly Contributions
      </h3>
      <div className="chart-container">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={monthlyData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <XAxis
              dataKey="month"
              stroke="#64716A"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: '#E2E7E1' }}
            />
            <YAxis
              stroke="#64716A"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: '#E2E7E1' }}
              allowDecimals={false}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#FFFFFF',
                borderColor: '#E2E7E1',
                borderRadius: '8px',
                fontSize: '12px',
                boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
              }}
              formatter={(value) => [`${value} contributions`, 'Contributions']}
            />
            <Bar dataKey="contributions" fill="#47735C" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* GitHub-style Contribution Heatmap */}
      <h3 style={{ fontSize: '14px', fontWeight: 600, marginTop: '24px', marginBottom: '8px', color: 'var(--text-primary)' }}>
        Contribution Heatmap (52 Weeks)
      </h3>
      <div className="heatmap-wrapper">
        <div className="heatmap-grid">
          {dailyData.map((day, idx) => (
            <div
              key={`${day.date}-${idx}`}
              className="heatmap-day"
              style={{ backgroundColor: getDayColor(day.count, day.color) }}
              title={`${day.date}: ${day.count} contribution${day.count === 1 ? '' : 's'}`}
            />
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="heatmap-legend">
        <span>Less</span>
        <div className="legend-square" style={{ backgroundColor: '#EBEDF0' }} />
        <div className="legend-square" style={{ backgroundColor: '#C6E48B' }} />
        <div className="legend-square" style={{ backgroundColor: '#7BC96F' }} />
        <div className="legend-square" style={{ backgroundColor: '#47735C' }} />
        <div className="legend-square" style={{ backgroundColor: '#254A37' }} />
        <span>More</span>
      </div>
    </section>
  );
}
