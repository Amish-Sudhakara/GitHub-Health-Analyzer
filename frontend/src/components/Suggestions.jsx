import React from 'react';

export default function Suggestions({ suggestions }) {
  if (!suggestions || suggestions.length === 0) return null;

  return (
    <section className="section-card">
      <div className="section-header">
        <div>
          <h2 className="section-title">Improvement Suggestions</h2>
          <span className="section-subtitle">
            Deterministic recommendations based on your public project data
          </span>
        </div>
      </div>

      <div className="suggestions-list">
        {suggestions.map((suggestion, index) => (
          <div key={index} className="suggestion-item">
            <span className="suggestion-bullet">&bull;</span>
            <span>{suggestion}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
