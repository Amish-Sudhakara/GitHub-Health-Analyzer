import React, { useState } from 'react';

export default function Header({ onAnalyze, loading, cachedTime, onRefresh, currentUsername }) {
  const [inputVal, setInputVal] = useState(currentUsername || '');
  const [validationError, setValidationError] = useState('');

  const GITHUB_USERNAME_REGEX = /^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$/;

  const handleSubmit = (e) => {
    e.preventDefault();
    const cleanUsername = inputVal.trim();

    if (!cleanUsername) {
      setValidationError('Please enter a GitHub username.');
      return;
    }

    if (!GITHUB_USERNAME_REGEX.test(cleanUsername)) {
      setValidationError(
        'Invalid GitHub username. Usernames can only contain letters, numbers, and single internal hyphens (max 39 characters).'
      );
      return;
    }

    setValidationError('');
    onAnalyze(cleanUsername);
  };

  return (
    <header className="header-section">
      <div className="brand-badge">
        <span>GitHub Student Health</span>
      </div>
      <h1 className="app-title">GitHub Health</h1>
      <p className="app-subtitle">
        A simple, lightweight snapshot of your GitHub activity, repositories, and project maintenance.
      </p>

      <div className="search-card">
        <form onSubmit={handleSubmit} className="search-form">
          <div className="search-input-group">
            <input
              type="text"
              className="search-input"
              placeholder="Enter GitHub username (e.g. octocat)"
              value={inputVal}
              onChange={(e) => {
                setInputVal(e.target.value);
                if (validationError) setValidationError('');
              }}
              disabled={loading}
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck="false"
            />
          </div>
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Analyzing...' : 'Analyze'}
          </button>
        </form>

        {validationError && (
          <div style={{ marginTop: '10px', color: 'var(--error-text)', fontSize: '13px', textAlign: 'left' }}>
            {validationError}
          </div>
        )}

        {cachedTime && (
          <div className="search-meta-bar">
            <span className="cached-indicator">
              Cached result ({cachedTime})
            </span>
            <button
              type="button"
              className="btn-secondary"
              style={{ padding: '4px 10px', fontSize: '12px' }}
              onClick={() => onRefresh(inputVal.trim())}
              disabled={loading}
            >
              Refresh Data
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
