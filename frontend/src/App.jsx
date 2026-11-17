import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import ProfileSummary from './components/ProfileSummary';
import StatsCards from './components/StatsCards';
import ContributionAnalysis from './components/ContributionAnalysis';
import LanguageChart from './components/LanguageChart';
import RepositoryList from './components/RepositoryList';
import Suggestions from './components/Suggestions';
import PdfDownloadCard from './components/PdfDownloadCard';

const CACHE_TTL_MS = 15 * 60 * 1000; // 15 minutes cache

export default function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingText, setLoadingText] = useState('');
  const [error, setError] = useState(null);
  const [cachedTime, setCachedTime] = useState(null);
  const [currentUsername, setCurrentUsername] = useState('');

  // Determine API base URL
  const getApiUrl = () => {
    let url = import.meta.env.VITE_API_URL;
    if (!url || url.startsWith('PASTE_')) {
      // Default fallback to local server during local development
      return 'http://localhost:8000';
    }
    return url.replace(/\/+$/, '');
  };

  const getCachedAnalysis = (username) => {
    try {
      const raw = sessionStorage.getItem(`gh_health_${username.toLowerCase()}`);
      if (!raw) return null;
      const parsed = jsonParseSafe(raw);
      if (!parsed || !parsed.timestamp || !parsed.payload) return null;

      const age = Date.now() - parsed.timestamp;
      if (age < CACHE_TTL_MS) {
        const minsAgo = Math.floor(age / 60000);
        return {
          payload: parsed.payload,
          ageText: minsAgo === 0 ? 'just now' : `${minsAgo}m ago`,
        };
      } else {
        sessionStorage.removeItem(`gh_health_${username.toLowerCase()}`);
      }
    } catch (e) {
      console.warn('SessionStorage read error:', e);
    }
    return null;
  };

  const setCachedAnalysis = (username, payload) => {
    try {
      const item = { timestamp: Date.now(), payload };
      sessionStorage.setItem(`gh_health_${username.toLowerCase()}`, JSON.stringify(item));
    } catch (e) {
      console.warn('SessionStorage write error:', e);
    }
  };

  const jsonParseSafe = (str) => {
    try {
      return JSON.parse(str);
    } catch {
      return null;
    }
  };

  const analyzeUser = async (username, bypassCache = false) => {
    setError(null);
    setCurrentUsername(username);

    // Check cache first
    if (!bypassCache) {
      const cached = getCachedAnalysis(username);
      if (cached) {
        setData(cached.payload);
        setCachedTime(cached.ageText);
        setLoading(false);
        return;
      }
    }

    setLoading(true);
    setCachedTime(null);
    setLoadingText('Connecting to GitHub API...');

    const timer1 = setTimeout(() => {
      setLoadingText('Retrieving public repository metadata & READMEs...');
    }, 1500);

    const timer2 = setTimeout(() => {
      setLoadingText('Analyzing 12-month contribution calendar...');
    }, 3500);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 18000); // 18s request timeout

    try {
      const baseUrl = getApiUrl();
      // Ensure path accommodates either root URL or /analyze endpoint
      const separator = baseUrl.includes('/analyze') ? '&' : '?';
      const endpoint = baseUrl.includes('/analyze')
        ? `${baseUrl}${separator}username=${encodeURIComponent(username)}`
        : `${baseUrl}/analyze?username=${encodeURIComponent(username)}`;

      const response = await fetch(endpoint, {
        method: 'GET',
        headers: {
          Accept: 'application/json',
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);
      clearTimeout(timer1);
      clearTimeout(timer2);

      const respData = await response.json().catch(() => null);

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error(`GitHub user "${username}" was not found. Please verify the username.`);
        } else if (response.status === 400) {
          throw new Error(respData?.error || 'Invalid GitHub username format.');
        } else if (response.status === 429) {
          throw new Error(
            'GitHub API rate limit exceeded. If running locally or on Lambda, configure a personal access token (GITHUB_TOKEN) to increase the limit.'
          );
        } else if (response.status === 504) {
          throw new Error('The GitHub API request timed out. Please try again.');
        } else {
          throw new Error(respData?.error || `Server returned error (${response.status}).`);
        }
      }

      if (!respData || !respData.success) {
        throw new Error(respData?.error || 'Failed to retrieve analysis from backend.');
      }

      // Success
      setData(respData);
      setCachedAnalysis(username, respData);
      setCachedTime('just now');
    } catch (err) {
      clearTimeout(timeoutId);
      clearTimeout(timer1);
      clearTimeout(timer2);

      if (err.name === 'AbortError') {
        setError('Request timed out. The backend or GitHub API took too long to respond.');
      } else if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
        setError(
          `Unable to connect to the backend API at ${getApiUrl()}. Please check that the local server is running (python backend/local_server.py) or that the AWS Lambda Function URL is active.`
        );
      } else {
        setError(err.message || 'An unexpected error occurred.');
      }
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = (username) => {
    if (!username) return;
    sessionStorage.removeItem(`gh_health_${username.toLowerCase()}`);
    analyzeUser(username, true);
  };

  return (
    <div className="app-container">
      {/* Header & Search */}
      <Header
        onAnalyze={(u) => analyzeUser(u, false)}
        loading={loading}
        cachedTime={cachedTime}
        onRefresh={handleRefresh}
        currentUsername={currentUsername}
      />

      {/* Error Alert Box */}
      {error && (
        <div className="alert-box">
          <div className="alert-title">Analysis Error</div>
          <div>{error}</div>
        </div>
      )}

      {/* Loading Progress State */}
      {loading && (
        <div className="loading-card">
          <div className="spinner" />
          <div className="loading-text">Analyzing GitHub Profile</div>
          <div className="loading-subtext">{loadingText}</div>
        </div>
      )}

      {/* Empty State before search */}
      {!loading && !data && !error && (
        <div className="empty-state">
          <h2 className="empty-title">Ready to evaluate your GitHub health?</h2>
          <p className="empty-description">
            Enter any public GitHub username above to generate an instant report covering contributions, documentation signals, language distribution, and activity ratings.
          </p>
          <div className="sample-tags">
            <span style={{ fontSize: '13px', color: 'var(--text-secondary)', alignSelf: 'center' }}>
              Try a sample:
            </span>
            <button
              type="button"
              className="sample-tag"
              onClick={() => analyzeUser('octocat')}
            >
              octocat
            </button>
            <button
              type="button"
              className="sample-tag"
              onClick={() => analyzeUser('torvalds')}
            >
              torvalds
            </button>
          </div>
        </div>
      )}

      {/* Complete Dashboard in Required Section Order */}
      {!loading && data && (
        <main>
          {/* Section A: Profile Summary */}
          <ProfileSummary profile={data.profile} username={data.username} />

          {/* Section B: Statistics Cards */}
          <StatsCards metrics={data.metrics} />

          {/* Section C: Contribution Analysis */}
          <ContributionAnalysis
            contributions={data.contributions}
            metrics={data.metrics}
          />

          {/* Section D: Programming Languages */}
          <LanguageChart languages={data.languages} />

          {/* Section E: Repository Analysis */}
          <RepositoryList repositories={data.repositories} />

          {/* Section F: Improvement Suggestions */}
          <Suggestions suggestions={data.suggestions} />

          {/* Section G: PDF Download */}
          <PdfDownloadCard data={data} />
        </main>
      )}

      {/* Footer */}
      <footer className="app-footer">
        <p>
          GitHub Student Health Analyzer &bull; Built with React, Vite, and Python AWS Lambda &bull; Slate &amp; Sage Minimalist Design
        </p>
        <p style={{ marginTop: '4px', opacity: 0.8 }}>
          Public data only. Not affiliated with or endorsed by GitHub, Inc.
        </p>
      </footer>
    </div>
  );
}
