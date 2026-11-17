import React from 'react';

export default function ProfileSummary({ profile, username }) {
  if (!profile) return null;

  return (
    <section className="section-card">
      <div className="section-header">
        <h2 className="section-title">Profile Summary</h2>
        <span className="section-subtitle">Verified GitHub Profile</span>
      </div>

      <div className="profile-card">
        {profile.avatar_url && (
          <img
            src={profile.avatar_url}
            alt={`${profile.name || username}'s avatar`}
            className="profile-avatar"
            loading="lazy"
          />
        )}

        <div className="profile-details">
          <div className="profile-name-row">
            <span className="profile-name">{profile.name || username}</span>
            <span className="profile-login">@{profile.login || username}</span>
          </div>

          {profile.bio && <p className="profile-bio">{profile.bio}</p>}

          <div className="profile-meta-tags">
            <div className="profile-meta-item">
              <strong>{profile.public_repos}</strong> public repos
            </div>
            <div className="profile-meta-item">
              <strong>{profile.followers}</strong> followers
            </div>
            <div className="profile-meta-item">
              Member since <strong>{profile.created_year}</strong>
            </div>
            <div className="profile-meta-item">
              <a
                href={profile.html_url}
                target="_blank"
                rel="noopener noreferrer"
                className="profile-link"
              >
                View on GitHub &rarr;
              </a>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
