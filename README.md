# GitHub Student Health Analyzer

A clean, lightweight, single-page web application designed for college students to evaluate and showcase their GitHub development activity and repository hygiene.

Built with a **React + Vite** frontend and a **serverless Python 3.12 AWS Lambda** backend, with zero heavy frameworks, no external database, and zero client-side credentials.

---

## Features

- **Public Profile Overview**: Instant snapshot of student profile, avatar, bio, follower count, and account creation year.
- **12-Month Contribution Metrics**: Total contributions, active weeks, and rolling monthly activity buckets.
- **Interactive Visualizations**:
  - Monthly contributions bar chart (Recharts).
  - 52-week GitHub-style contribution heatmap.
  - Top 5 primary programming languages distribution across original public repositories.
- **Repository Maintenance & Activity Rating**:
  - Evaluates up to 10 most recently updated original public repositories (forks and empty repositories excluded).
  - Analyzes 3 objective signals: verified README file (+1), push within last 180 days (+1), and at least 10 commits on default branch (+1).
  - Categorizes into **Good** (0–1 pts), **Very Good** (2 pts), or **Excellent** (3 pts).
- **Deterministic Improvement Suggestions**: 2–3 actionable, rule-based recommendations tailored to the student's metrics.
- **Downloadable PDF Report**: Instant client-side report generation formatted in Slate & Sage with summary tables, ratings, and methodology notes.
- **Local Caching & Resilience**: 15-minute `sessionStorage` caching with cache freshness indicators and one-click refresh.
- **Slate & Sage Theme**: Professional minimalist aesthetic with Inter typography, accessible contrast, and full mobile responsiveness.

---

## Technology Stack

### Frontend
- **Framework**: React 18 with Vite
- **Language**: JavaScript (ES Modules)
- **Styling**: Plain CSS with custom CSS variables (Slate & Sage theme)
- **Charts**: Recharts
- **PDF Generation**: jsPDF & jspdf-autotable (100% in-browser)
- **HTTP Client**: Native browser Fetch API with `AbortController` timeouts

### Backend
- **Runtime**: AWS Lambda with Python 3.12
- **Dependencies**: None (100% Python Standard Library: `urllib.request`, `json`, `datetime`)
- **API Protocol**: REST & GitHub GraphQL API v4
- **Local Testing**: Standard Library `http.server` (running identical Lambda handler logic)

### Cloud Infrastructure
- **Frontend Hosting**: AWS Amplify Hosting (continuous deployment from GitHub)
- **Backend Compute**: AWS Lambda Function URL (Auth type `NONE` with CORS protection)

---

## Project Structure

```text
github-student-health/
├── .gitignore               # Git ignore rules for node_modules, build artifacts, and secrets
├── amplify.yml              # AWS Amplify continuous deployment configuration
├── DEPLOYMENT.md            # Detailed AWS deployment and configuration guide
├── README.md                # Project documentation and architecture overview
│
├── backend/
│   ├── lambda_function.py   # Core AWS Lambda handler (Python standard library only)
│   ├── local_server.py      # Local development server using http.server
│   ├── requirements.txt     # Backend dependencies (pure standard library)
│   └── test_analyzer.py     # Comprehensive automated unit test suite
│
└── frontend/
    ├── .env.example         # Template for frontend environment variables
    ├── index.html           # HTML entry point with Inter font preload
    ├── package.json         # Frontend dependencies and npm scripts
    ├── vite.config.js       # Vite configuration with chunk optimization
    └── src/
        ├── App.jsx          # Main application container & state management
        ├── main.jsx         # React application bootstrap
        ├── styles.css       # Slate & Sage design system and responsive styles
        ├── components/
        │   ├── Header.jsx               # Logo, subtitle, input form, and cache refresh
        │   ├── ProfileSummary.jsx       # Section A: Student profile card
        │   ├── StatsCards.jsx           # Section B: 4 primary metrics & rating pill
        │   ├── ContributionAnalysis.jsx # Section C: Monthly bar chart & 52-week heatmap
        │   ├── LanguageChart.jsx        # Section D: Horizontal top-5 languages chart
        │   ├── RepositoryList.jsx       # Section E: Repository rating & signals table
        │   ├── Suggestions.jsx          # Section F: Deterministic recommendations
        │   └── PdfDownloadCard.jsx      # Section G: PDF report export trigger
        └── utils/
            └── pdfGenerator.js          # jsPDF document layout engine
```

---

## Local Development Quickstart

### Prerequisites
- **Node.js**: v18 or newer (v20+ recommended)
- **Python**: 3.11 or 3.12

### 1. Backend Setup & Run

The backend uses Python's standard library. No `pip install` is necessary.

```bash
# Navigate to the backend directory
cd backend

# (Optional) Create a .env file for local development with your personal access token:
# GITHUB_TOKEN=PASTE_GITHUB_TOKEN_HERE

# Run the local server (starts on http://localhost:8000)
python local_server.py
```

You can test the backend directly in your browser or curl:
```bash
curl "http://localhost:8000/analyze?username=octocat"
```

### 2. Run Backend Unit Tests

A comprehensive unit test suite with 18 automated tests covers username validation, scoring thresholds, boundary date calculations, repository filters, suggestions, and simulated GitHub API errors:

```bash
# Run unit tests
python backend/test_analyzer.py
```

### 3. Frontend Setup & Run

In a separate terminal:

```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Start the Vite local development server
npm run dev
```

Open `http://localhost:5173` in your browser. By default, the frontend automatically connects to `http://localhost:8000` when running locally.

To build the production bundle:
```bash
npm run build
```

---

## Backend API Specification

### Endpoint: `GET /analyze`

Analyzes a public GitHub profile and returns calculated health metrics.

#### Query Parameters:
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `username` | string | Yes | Valid GitHub username (1–39 alphanumeric characters, internal hyphens). |

#### Sample Request:
```http
GET /analyze?username=octocat HTTP/1.1
Host: localhost:8000
Accept: application/json
```

#### Sample Response:
```json
{
  "success": true,
  "username": "octocat",
  "profile": {
    "name": "The Octocat",
    "login": "octocat",
    "avatar_url": "https://avatars.githubusercontent.com/u/583231?v=4",
    "html_url": "https://github.com/octocat",
    "bio": "GitHub mascot",
    "public_repos": 8,
    "followers": 15000,
    "created_year": 2011
  },
  "metrics": {
    "total_contributions": 142,
    "active_weeks": 28,
    "total_observed_weeks": 53,
    "public_repos_count": 8,
    "eligible_repos_count": 6,
    "analyzed_repos_count": 6,
    "activity_rating": "Very Good",
    "activity_rating_description": "Active in 28 of 53 observed weeks.",
    "contributions_available": true,
    "data_limited": false
  },
  "contributions": {
    "available": true,
    "monthly": [
      { "month": "Dec 25", "month_key": "2025-12", "contributions": 14 }
    ],
    "daily": [
      { "date": "2025-11-18", "count": 2, "color": "#40c463" }
    ]
  },
  "languages": [
    { "language": "Ruby", "count": 4, "percentage": 66.7 },
    { "language": "JavaScript", "count": 2, "percentage": 33.3 }
  ],
  "repositories": [
    {
      "name": "Hello-World",
      "html_url": "https://github.com/octocat/Hello-World",
      "description": "My first repository",
      "language": "Ruby",
      "stargazers_count": 2500,
      "commit_count": 42,
      "commit_count_display": "42",
      "pushed_at_formatted": "2026-10-15",
      "score": 3,
      "rating": "Excellent",
      "checks": {
        "has_readme": true,
        "recent_push": true,
        "commits_ge_10": true,
        "readme_evaluated": true,
        "commits_evaluated": true
      }
    }
  ],
  "suggestions": [
    "Write short descriptions for all your repositories so visitors immediately understand what each project does.",
    "Pin your top showcase repositories to your GitHub profile for better visibility."
  ],
  "meta": {
    "analyzed_at": "2026-11-17T14:45:00Z",
    "analyzed_at_formatted": "Nov 17, 2026",
    "window_start": "2025-11-17",
    "window_end": "2026-11-17"
  }
}
```

#### Error Codes:
- `400 INVALID_USERNAME`: Invalid username format (regex validation failed).
- `404 USER_NOT_FOUND`: GitHub user was not found on GitHub.
- `405 METHOD_NOT_ALLOWED`: Request method was not GET or OPTIONS.
- `429 RATE_LIMIT_OR_PERMISSION_ERROR`: GitHub rate limit reached or unauthorized.
- `504 UPSTREAM_TIMEOUT`: GitHub API request timed out.

---

## Rating Methodology

### 1. Overall Activity Rating
Categorizes consistent public GitHub presence over the rolling 12 months (0–53 observed weeks):
- **0–17 active weeks**: Good
- **18–34 active weeks**: Very Good
- **35–53 active weeks**: Excellent

*An active week is defined as a calendar week with at least 1 visible public contribution.*

### 2. Repository Maintenance & Activity Rating
Evaluates up to 10 most recently updated original public repositories on 3 objective signals:
1. **README**: Repository contains a readable README file (+1 pt).
2. **Recent Activity (<180d)**: Pushed to within the last 180 days (+1 pt).
3. **Commits (≥10)**: Repository has at least 10 commits on its default branch (+1 pt).

- **0–1 points**: Good
- **2 points**: Very Good
- **3 points**: Excellent
- *Not evaluated*: Displayed if GitHub API encountered an error checking README or commit count.

---

## Known Limitations

- **Public Data Only**: The analyzer uses public GitHub APIs. Activity in private repositories and private organizations with restricted visibility is excluded.
- **Hygiene Signals vs Code Quality**: Ratings reflect documentation and maintenance hygiene (README presence, push frequency, commit volume), not internal algorithm design, architecture, or code complexity.
- **API Rate Limits**: GitHub enforces a rate limit of 60 requests/hour for unauthenticated REST calls. Providing a personal access token (`GITHUB_TOKEN`) raises this to 5,000 requests/hour and enables GraphQL contribution calendar retrieval.
- **Capped Repositories**: Profiles with over 100 repositories are capped at the first 100 metadata results, with the `data_limited: true` flag set.

---

## AWS Deployment Summary

Full step-by-step instructions with console screenshots and cost control settings are available in [DEPLOYMENT.md](DEPLOYMENT.md).

### Quick Deployment Steps:
1. **Push to GitHub**: Push this repository to `GITHUB_REPOSITORY_URL=PASTE_GITHUB_REPOSITORY_URL_HERE`.
2. **AWS Amplify**: Connect repository to AWS Amplify Hosting to deploy the frontend and obtain your Amplify URL (`https://main.xxx.amplifyapp.com`).
3. **AWS Lambda**: Create a Python 3.12 Lambda function, paste `backend/lambda_function.py`, create a Function URL (Auth `NONE`), and configure:
   - `GITHUB_TOKEN=PASTE_GITHUB_TOKEN_HERE`
   - `ALLOWED_ORIGIN=PASTE_AMPLIFY_URL_HERE`
4. **Link Frontend to Lambda**: In AWS Amplify, set `VITE_API_URL=PASTE_LAMBDA_FUNCTION_URL_HERE` and redeploy.

---

## License

This project is open-source and free for educational use under the MIT License.
