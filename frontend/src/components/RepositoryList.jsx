import React from 'react';

export default function RepositoryList({ repositories }) {
  if (!repositories || repositories.length === 0) {
    return (
      <section className="section-card">
        <div className="section-header">
          <h2 className="section-title">Repository Analysis</h2>
          <span className="section-subtitle">Documentation & Maintenance Signals</span>
        </div>
        <p style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
          No eligible original public repositories found. (Forks and empty repositories are excluded from analysis).
        </p>
      </section>
    );
  }

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
    <section className="section-card">
      <div className="section-header">
        <div>
          <h2 className="section-title">Repository Analysis</h2>
          <span className="section-subtitle">
            Evaluating up to 10 most recently updated original public repositories
          </span>
        </div>
      </div>

      <div className="repo-table-container">
        <table className="repo-table">
          <thead>
            <tr>
              <th>Repository</th>
              <th>Primary Language</th>
              <th>Stars</th>
              <th>Commits</th>
              <th>Last Push</th>
              <th>Signals</th>
              <th>Rating</th>
            </tr>
          </thead>
          <tbody>
            {repositories.map((repo) => (
              <tr key={repo.name}>
                <td>
                  <a
                    href={repo.html_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="repo-name-link"
                  >
                    {repo.name}
                  </a>
                  <div className="repo-desc">{repo.description}</div>
                </td>
                <td>{repo.language}</td>
                <td>{repo.stargazers_count}</td>
                <td>{repo.commit_count_display || (repo.commit_count != null ? repo.commit_count : 'N/A')}</td>
                <td>{repo.pushed_at_formatted}</td>
                <td>
                  <div className="repo-checks-detail">
                    <span
                      className={`check-tag ${
                        !repo.checks.readme_evaluated
                          ? 'fail'
                          : repo.checks.has_readme
                          ? 'pass'
                          : 'fail'
                      }`}
                      title={
                        !repo.checks.readme_evaluated
                          ? 'README check unevaluated'
                          : repo.checks.has_readme
                          ? 'README present'
                          : 'No README'
                      }
                    >
                      README
                    </span>
                    <span
                      className={`check-tag ${repo.checks.recent_push ? 'pass' : 'fail'}`}
                      title={repo.checks.recent_push ? 'Pushed within 180 days' : 'No push in 180 days'}
                    >
                      &lt;180d
                    </span>
                    <span
                      className={`check-tag ${
                        !repo.checks.commits_evaluated
                          ? 'fail'
                          : repo.checks.commits_ge_10
                          ? 'pass'
                          : 'fail'
                      }`}
                      title={
                        !repo.checks.commits_evaluated
                          ? 'Commit count unevaluated'
                          : repo.checks.commits_ge_10
                          ? '≥10 commits on default branch'
                          : '<10 commits on default branch'
                      }
                    >
                      &ge;10 commits
                    </span>
                  </div>
                </td>
                <td>
                  <span className={getRatingPillClass(repo.rating)}>
                    {repo.rating}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={{ marginTop: '16px', fontSize: '12px', color: 'var(--text-secondary)' }}>
        Note: This rating assesses basic project maintenance (presence of README documentation, push activity within the last 180 days, and at least 10 commits on the default branch). It does not grade internal code complexity, style, or algorithm performance.
      </div>
    </section>
  );
}
