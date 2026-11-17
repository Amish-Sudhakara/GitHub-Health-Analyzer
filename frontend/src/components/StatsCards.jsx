import React from 'react';

export default function StatsCards({ metrics }) {
  if (!metrics) return null;

  const getRatingPillClass = (rating) => {
    switch (rating) {
      case 'Excellent':
        return 'rating-pill excellent';
      case 'Very Good':
        return 'rating-pill very-good';
      case 'Good':
        return 'rating-pill good';
      default:
        return 'rating-pill not-evaluated';
    }
  };

  return (
    <section>
      <div className="stats-grid">
        {/* 1. Total Contributions */}
        <div className="stat-card">
          <span className="stat-label">Contributions</span>
          <span className="stat-value">
            {metrics.contributions_available ? metrics.total_contributions.toLocaleString() : 'N/A'}
          </span>
          <span className="stat-subtext">Last 12 rolling months</span>
        </div>

        {/* 2. Active Weeks */}
        <div className="stat-card">
          <span className="stat-label">Active Weeks</span>
          <span className="stat-value">
            {metrics.contributions_available ? metrics.active_weeks : 'N/A'}
          </span>
          <span className="stat-subtext">
            {metrics.contributions_available
              ? `out of ${metrics.total_observed_weeks} observed weeks`
              : 'Contribution data restricted'}
          </span>
        </div>

        {/* 3. Public Repositories */}
        <div className="stat-card">
          <span className="stat-label">Public Repositories</span>
          <span className="stat-value">{metrics.public_repos_count}</span>
          <span className="stat-subtext">
            {metrics.eligible_repos_count} eligible original repos
            {metrics.data_limited && ' (capped at 100)'}
          </span>
        </div>

        {/* 4. Overall Activity Rating */}
        <div className="stat-card">
          <span className="stat-label">Activity Rating</span>
          <div style={{ margin: '4px 0 6px 0' }}>
            <span className={getRatingPillClass(metrics.activity_rating)}>
              {metrics.activity_rating}
            </span>
          </div>
          <span className="stat-subtext">
            {metrics.activity_rating_description}
          </span>
        </div>
      </div>

      <div className="notice-box" style={{ marginBottom: '24px' }}>
        <strong>Note on Activity Rating:</strong> This assessment evaluates visible public GitHub contributions over the previous 12 months. Private repositories, organization contributions with restricted privacy, and work outside GitHub are not reflected.
      </div>
    </section>
  );
}
