"""
GitHub Student Health Analyzer - AWS Lambda Backend Handler
Analyzes public GitHub profiles, contributions, repositories, and languages.
Built using Python 3 standard library only (no external dependencies).
"""

import json
import os
import re
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone, timedelta

# Constants & Limits
MAX_REPOS_TO_ANALYZE = 10
MAX_REPOS_METADATA = 100
HTTP_TIMEOUT_SECONDS = 7
GITHUB_API_BASE = "https://api.github.com"
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$")


def get_allowed_origin():
    """Retrieve allowed CORS origin from environment or default to wildcard for dev."""
    return os.environ.get("ALLOWED_ORIGIN", "*")


def build_response(status_code, body_dict):
    """Format an AWS Lambda HTTP response with standard CORS headers."""
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": get_allowed_origin(),
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
    }
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(body_dict),
    }


def validate_username(username):
    """
    Validate GitHub username format.
    Alphanumeric and single internal hyphens, max 39 characters, no leading/trailing hyphen.
    """
    if not username or not isinstance(username, str):
        return False
    username = username.strip()
    return bool(USERNAME_REGEX.match(username))


def github_request(url, token=None, method="GET", payload=None):
    """
    Execute an HTTP request against the GitHub REST or GraphQL API using urllib.
    Returns (status_code, response_data, headers) or raises appropriate errors.
    """
    headers = {
        "User-Agent": "GitHub-Student-Health-Analyzer",
        "Accept": "application/vnd.github.v3+json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token.strip()}"

    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as response:
            status_code = response.getcode()
            response_body = response.read().decode("utf-8")
            response_headers = dict(response.info())
            parsed_json = json.loads(response_body) if response_body else {}
            return status_code, parsed_json, response_headers
    except urllib.error.HTTPError as e:
        status_code = e.code
        error_body = ""
        try:
            error_body = e.read().decode("utf-8")
            parsed_err = json.loads(error_body) if error_body else {}
        except Exception:
            parsed_err = {"message": error_body}
        return status_code, parsed_err, dict(e.headers)
    except urllib.error.URLError as e:
        raise ConnectionError(f"Network error contacting GitHub API: {e.reason}")
    except TimeoutError:
        raise TimeoutError("GitHub API request timed out.")


def fetch_user_profile(username, token=None):
    """Fetch GitHub user public profile information."""
    url = f"{GITHUB_API_BASE}/users/{urllib.parse.quote(username)}"
    status, data, headers = github_request(url, token=token)

    if status == 200:
        return data
    elif status == 404:
        raise LookupError(f"GitHub user '{username}' was not found.")
    elif status in (403, 429):
        msg = data.get("message", "")
        if "rate limit" in msg.lower():
            raise PermissionError("GitHub API rate limit exceeded. Please configure a GitHub token or try again later.")
        raise PermissionError(f"Access forbidden by GitHub: {msg}")
    elif status == 401:
        raise PermissionError("Configured GITHUB_TOKEN is invalid or expired.")
    else:
        raise RuntimeError(f"GitHub API returned error status {status}: {data.get('message', 'Unknown error')}")


def fetch_user_repos(username, token=None):
    """
    Fetch public repositories for the user.
    Capped at 100 repositories metadata.
    """
    url = f"{GITHUB_API_BASE}/users/{urllib.parse.quote(username)}/repos?per_page={MAX_REPOS_METADATA}&type=owner&sort=updated"
    status, data, headers = github_request(url, token=token)

    if status == 200:
        return data
    elif status in (403, 429):
        msg = data.get("message", "")
        if "rate limit" in msg.lower():
            raise PermissionError("GitHub API rate limit exceeded while retrieving repositories.")
        raise PermissionError(f"Access forbidden: {msg}")
    else:
        raise RuntimeError(f"Error fetching repositories (status {status}): {data.get('message', 'Unknown error')}")


def check_repo_readme(owner, repo_name, token=None):
    """
    Check if a repository contains a README file.
    Status 200: Found (True, True)
    Status 404: Missing (False, True)
    Other error (rate limit, etc): Not evaluated (False, False)
    """
    url = f"{GITHUB_API_BASE}/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo_name)}/readme"
    try:
        status, data, headers = github_request(url, token=token)
        if status == 200:
            return True, True
        elif status == 404:
            return False, True
        else:
            return False, False
    except Exception:
        return False, False


def fetch_graphql_contributions(username, token=None):
    """
    Query GitHub GraphQL API for the rolling 12-month contribution calendar.
    Requires a valid GitHub token.
    """
    if not token or not token.strip():
        return None, "No GITHUB_TOKEN configured on backend; GraphQL contribution calendar requires authentication."

    now = datetime.now(timezone.utc)
    one_year_ago = now - timedelta(days=365)
    from_iso = one_year_ago.strftime("%Y-%m-%dT00:00:00Z")
    to_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
                color
              }
            }
          }
        }
      }
    }
    """
    variables = {
        "login": username,
        "from": from_iso,
        "to": to_iso,
    }

    url = f"{GITHUB_API_BASE}/graphql"
    try:
        status, data, headers = github_request(url, token=token, method="POST", payload={"query": query, "variables": variables})
        if status == 200:
            if "errors" in data and not data.get("data", {}).get("user"):
                error_msgs = [e.get("message", "") for e in data.get("errors", [])]
                return None, f"GraphQL error: {'; '.join(error_msgs)}"
            user_data = data.get("data", {}).get("user")
            if not user_data:
                return None, "User contribution calendar was null or restricted."
            calendar = user_data.get("contributionsCollection", {}).get("contributionCalendar")
            return calendar, None
        elif status in (403, 429):
            return None, "GitHub GraphQL rate limit exceeded."
        elif status == 401:
            return None, "GitHub token is unauthorized for GraphQL API."
        else:
            return None, f"GraphQL returned status {status}: {data.get('message', 'Unknown error')}"
    except Exception as e:
        return None, f"Failed to retrieve contributions: {str(e)}"


def parse_iso_datetime(date_str):
    """Safely parse ISO datetime string to UTC datetime."""
    if not date_str:
        return None
    try:
        # Standard format YYYY-MM-DDTHH:MM:SSZ
        clean_str = date_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean_str)
    except Exception:
        try:
            return datetime.strptime(date_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except Exception:
            return None


def calculate_activity_rating(active_weeks):
    """
    Activity Rating based on active weeks in last 12 months (0-53):
    0-17: Good
    18-34: Very Good
    35-53: Excellent
    """
    if active_weeks is None:
        return "Insufficient data"
    if active_weeks >= 35:
        return "Excellent"
    elif active_weeks >= 18:
        return "Very Good"
    else:
        return "Good"


def rate_repository(has_desc, has_readme, recent_push, readme_evaluated):
    """
    Repository Rating:
    3 checks:
      1. Nonempty description: +1
      2. README file exists: +1
      3. Pushed to within last 180 days: +1
    Score 0-1: Good
    Score 2: Very Good
    Score 3: Excellent
    If README was not evaluated due to API error: 'Not evaluated'
    """
    if not readme_evaluated:
        return "Not evaluated", 0

    points = (1 if has_desc else 0) + (1 if has_readme else 0) + (1 if recent_push else 0)
    if points == 3:
        return "Excellent", 3
    elif points == 2:
        return "Very Good", 2
    else:
        return "Good", points


def generate_suggestions(active_weeks, analyzed_repos, eligible_repo_count):
    """
    Generate 2-3 deterministic suggestions based on analyzed repository and activity signals.
    """
    suggestions = []

    # Rule 1: Activity consistency
    if active_weeks is not None and active_weeks < 26:
        suggestions.append("Try contributing more regularly to build a consistent coding habit throughout the year.")

    # Rule 2: Missing READMEs
    missing_readme_count = sum(1 for r in analyzed_repos if r.get("checks", {}).get("readme_evaluated") and not r.get("checks", {}).get("has_readme"))
    if missing_readme_count > 0:
        suggestions.append(f"Add README files to explain the purpose, installation, and usage of your projects ({missing_readme_count} repo{'s' if missing_readme_count > 1 else ''} currently missing a README).")

    # Rule 3: Missing Descriptions
    missing_desc_count = sum(1 for r in analyzed_repos if not r.get("checks", {}).get("has_description"))
    if missing_desc_count > 0:
        suggestions.append("Write short descriptions for all your repositories so visitors immediately understand what each project does.")

    # Rule 4: Maintenance freshness
    inactive_repos = sum(1 for r in analyzed_repos if not r.get("checks", {}).get("recent_push"))
    if analyzed_repos and (inactive_repos / len(analyzed_repos)) >= 0.5:
        suggestions.append("Keep your key projects up to date by refreshing dependencies, fixing bugs, and documenting progress.")

    # Rule 5: Low original repository count
    if eligible_repo_count < 3 and len(suggestions) < 3:
        suggestions.append("Create and publish more original projects to demonstrate your hands-on problem solving skills.")

    # Fallback suggestions if all rules pass
    if len(suggestions) < 2:
        suggestions.append("Pin your top showcase repositories to your GitHub profile so visitors see your best work first.")
    if len(suggestions) < 2:
        suggestions.append("Include visual screenshots and architecture overviews in your project documentation.")

    return suggestions[:3]


def process_contributions(calendar, now_utc):
    """
    Process GraphQL calendar weeks into monthly buckets and daily heatmap items.
    Strictly filters to the 12-month rolling interval.
    """
    if not calendar:
        return {
            "available": False,
            "total_contributions": 0,
            "active_weeks": 0,
            "total_observed_weeks": 0,
            "monthly": [],
            "daily": [],
            "error_reason": "Contribution history unavailable.",
        }

    one_year_ago = now_utc - timedelta(days=365)
    one_year_ago_date = one_year_ago.date()
    now_date = now_utc.date()

    weeks = calendar.get("weeks", [])
    active_weeks_count = 0
    observed_weeks_count = 0

    daily_filtered = []
    monthly_map = {}

    # Initialize monthly map for last 12-13 calendar months in order
    curr_cursor = datetime(one_year_ago.year, one_year_ago.month, 1, tzinfo=timezone.utc)
    end_cursor = datetime(now_utc.year, now_utc.month, 1, tzinfo=timezone.utc)
    while curr_cursor <= end_cursor:
        m_key = curr_cursor.strftime("%Y-%m")
        m_label = curr_cursor.strftime("%b %y")
        monthly_map[m_key] = {"month": m_label, "month_key": m_key, "contributions": 0}
        # Advance 1 month
        year = curr_cursor.year + (1 if curr_cursor.month == 12 else 0)
        month = 1 if curr_cursor.month == 12 else curr_cursor.month + 1
        curr_cursor = datetime(year, month, 1, tzinfo=timezone.utc)

    for week in weeks:
        week_days = week.get("contributionDays", [])
        # Check if week has any days inside interval
        days_in_window = []
        for day in week_days:
            try:
                d_date = datetime.strptime(day["date"], "%Y-%m-%d").date()
            except Exception:
                continue

            if one_year_ago_date <= d_date <= now_date:
                days_in_window.append(day)
                count = day.get("contributionCount", 0)
                daily_filtered.append({
                    "date": day["date"],
                    "count": count,
                    "color": day.get("color", "#ebedf0"),
                })
                # Add to month
                m_key = day["date"][:7]
                if m_key in monthly_map:
                    monthly_map[m_key]["contributions"] += count

        if days_in_window:
            observed_weeks_count += 1
            if any(d.get("contributionCount", 0) > 0 for d in days_in_window):
                active_weeks_count += 1

    monthly_list = list(monthly_map.values())

    total_contributions = sum(d["count"] for d in daily_filtered)

    return {
        "available": True,
        "total_contributions": total_contributions,
        "active_weeks": active_weeks_count,
        "total_observed_weeks": observed_weeks_count,
        "monthly": monthly_list,
        "daily": daily_filtered,
    }


def analyze_user(username):
    """
    Core business logic: fetch profile, repositories, README checks, and contributions.
    """
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        token = token.strip()
        # Clean potential placeholder
        if token.startswith("PASTE_") or not token:
            token = None

    now_utc = datetime.now(timezone.utc)
    cutoff_180_days = now_utc - timedelta(days=180)

    # 1. Fetch user profile
    profile = fetch_user_profile(username, token=token)

    # 2. Fetch user repositories (capped at 100 metadata)
    raw_repos = fetch_user_repos(username, token=token)
    public_repos_count = profile.get("public_repos", 0)
    data_limited = bool(public_repos_count > MAX_REPOS_METADATA or len(raw_repos) >= MAX_REPOS_METADATA)

    # Filter eligible repos: public, original (not fork), nonempty (size > 0)
    eligible_repos = []
    language_counts = {}

    for repo in raw_repos:
        # Check original & nonempty
        is_fork = repo.get("fork", False)
        size = repo.get("size", 0) or 0
        if not is_fork and size > 0:
            eligible_repos.append(repo)

            # Language distribution across all eligible public original repos
            lang = repo.get("language")
            if lang and isinstance(lang, str) and lang.strip():
                clean_lang = lang.strip()
                language_counts[clean_lang] = language_counts.get(clean_lang, 0) + 1

    # Sort eligible repos by most recent push activity descending
    def get_push_time(r):
        dt = parse_iso_datetime(r.get("pushed_at"))
        return dt.timestamp() if dt else 0

    eligible_repos.sort(key=get_push_time, reverse=True)

    # Select at most 10 repositories for detailed evaluation
    selected_repos_raw = eligible_repos[:MAX_REPOS_TO_ANALYZE]
    analyzed_repos = []

    for repo in selected_repos_raw:
        repo_name = repo.get("name", "untitled")
        owner_login = repo.get("owner", {}).get("login", username)
        desc = (repo.get("description") or "").strip()
        has_description = bool(desc)

        # Check README
        has_readme, readme_evaluated = check_repo_readme(owner_login, repo_name, token=token)

        # Check recent push (within 180 days)
        pushed_at_dt = parse_iso_datetime(repo.get("pushed_at"))
        recent_push = bool(pushed_at_dt and pushed_at_dt >= cutoff_180_days)

        rating, score = rate_repository(has_description, has_readme, recent_push, readme_evaluated)

        pushed_at_str = pushed_at_dt.strftime("%Y-%m-%d") if pushed_at_dt else "Unknown"

        analyzed_repos.append({
            "name": repo_name,
            "html_url": repo.get("html_url", f"https://github.com/{owner_login}/{repo_name}"),
            "description": desc if has_description else "No description provided.",
            "language": repo.get("language") or "Not specified",
            "stargazers_count": repo.get("stargazers_count", 0),
            "pushed_at": repo.get("pushed_at"),
            "pushed_at_formatted": pushed_at_str,
            "score": score,
            "rating": rating,
            "checks": {
                "has_description": has_description,
                "has_readme": has_readme,
                "recent_push": recent_push,
                "readme_evaluated": readme_evaluated,
            },
        })

    # Top 5 primary languages
    sorted_languages = sorted(language_counts.items(), key=lambda item: item[1], reverse=True)[:5]
    total_lang_repos = sum(count for _, count in sorted_languages)
    language_distribution = [
        {
            "language": lang,
            "count": count,
            "percentage": round((count / total_lang_repos) * 100, 1) if total_lang_repos > 0 else 0,
        }
        for lang, count in sorted_languages
    ]

    # 3. Contributions via GraphQL
    calendar, calendar_error = fetch_graphql_contributions(username, token=token)
    contributions_data = process_contributions(calendar, now_utc)

    if not calendar and calendar_error:
        contributions_data["error_reason"] = calendar_error

    # Overall Activity Rating
    if contributions_data["available"]:
        active_weeks = contributions_data["active_weeks"]
        total_observed_weeks = contributions_data["total_observed_weeks"]
        activity_rating = calculate_activity_rating(active_weeks)
        activity_rating_desc = f"Active in {active_weeks} of {total_observed_weeks} observed weeks."
    else:
        active_weeks = None
        total_observed_weeks = 0
        activity_rating = "Insufficient data"
        activity_rating_desc = "Contribution history is unavailable or requires a GitHub token."

    # Parse account creation year
    created_at_dt = parse_iso_datetime(profile.get("created_at"))
    created_year = created_at_dt.year if created_at_dt else "Unknown"

    # Deterministic suggestions
    suggestions = generate_suggestions(active_weeks, analyzed_repos, len(eligible_repos))

    result = {
        "success": True,
        "username": username,
        "profile": {
            "name": profile.get("name") or username,
            "login": profile.get("login") or username,
            "avatar_url": profile.get("avatar_url", ""),
            "html_url": profile.get("html_url", f"https://github.com/{username}"),
            "bio": profile.get("bio") or "",
            "public_repos": public_repos_count,
            "followers": profile.get("followers", 0),
            "created_year": created_year,
            "created_at": profile.get("created_at"),
        },
        "metrics": {
            "total_contributions": contributions_data["total_contributions"],
            "active_weeks": active_weeks if active_weeks is not None else 0,
            "total_observed_weeks": total_observed_weeks,
            "public_repos_count": public_repos_count,
            "eligible_repos_count": len(eligible_repos),
            "analyzed_repos_count": len(analyzed_repos),
            "activity_rating": activity_rating,
            "activity_rating_description": activity_rating_desc,
            "contributions_available": contributions_data["available"],
            "data_limited": data_limited,
        },
        "contributions": {
            "available": contributions_data["available"],
            "monthly": contributions_data["monthly"],
            "daily": contributions_data["daily"],
            "error_reason": contributions_data.get("error_reason"),
        },
        "languages": language_distribution,
        "repositories": analyzed_repos,
        "suggestions": suggestions,
        "meta": {
            "analyzed_at": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "analyzed_at_formatted": now_utc.strftime("%b %d, %Y"),
            "window_start": (now_utc - timedelta(days=365)).strftime("%Y-%m-%d"),
            "window_end": now_utc.strftime("%Y-%m-%d"),
        },
    }

    return result


def lambda_handler(event, context):
    """
    AWS Lambda entry point for Lambda Function URLs and API Gateway HTTP API v2.
    Supports GET /analyze?username=USERNAME or GET /?username=USERNAME.
    """
    if not isinstance(event, dict):
        event = {}

    # 1. Determine HTTP method
    method = "GET"
    if "requestContext" in event and "http" in event["requestContext"]:
        method = event["requestContext"]["http"].get("method", "GET").upper()
    elif "httpMethod" in event:
        method = event.get("httpMethod", "GET").upper()

    # 2. Handle CORS preflight (OPTIONS)
    if method == "OPTIONS":
        return build_response(204, {})

    # 3. Allow only GET
    if method != "GET":
        return build_response(405, {"error": "Method Not Allowed. Use GET.", "code": "METHOD_NOT_ALLOWED"})

    # 4. Extract query parameters
    query_params = event.get("queryStringParameters") or {}
    if not query_params and "rawQueryString" in event and event["rawQueryString"]:
        parsed_qs = urllib.parse.parse_qs(event["rawQueryString"])
        query_params = {k: v[0] for k, v in parsed_qs.items() if v}

    username = query_params.get("username")

    # If no username provided, return health status check
    if not username:
        return build_response(200, {
            "status": "ok",
            "service": "GitHub Student Health Analyzer API",
            "version": "1.0.0",
            "usage": "GET /analyze?username=<github_username>",
        })

    username = username.strip()

    # 5. Validate username
    if not validate_username(username):
        return build_response(400, {
            "error": "Invalid GitHub username format. Usernames must be 1 to 39 characters, containing only letters, numbers, and single internal hyphens.",
            "code": "INVALID_USERNAME",
        })

    # 6. Execute analysis
    try:
        data = analyze_user(username)
        return build_response(200, data)
    except LookupError as e:
        return build_response(404, {"error": str(e), "code": "USER_NOT_FOUND"})
    except PermissionError as e:
        return build_response(429, {"error": str(e), "code": "RATE_LIMIT_OR_PERMISSION_ERROR"})
    except (ConnectionError, TimeoutError) as e:
        return build_response(504, {"error": str(e), "code": "UPSTREAM_TIMEOUT"})
    except Exception as e:
        # Never leak secret or stack trace in response
        return build_response(500, {
            "error": "An unexpected error occurred while analyzing the GitHub profile.",
            "code": "INTERNAL_SERVER_ERROR",
        })
