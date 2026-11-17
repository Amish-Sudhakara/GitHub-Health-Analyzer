"""
Comprehensive Unit Tests for GitHub Student Health Analyzer Backend.
Tests all requirements including commit count signals, README checks, recency,
ratings, suggestions, and API failure modes.
"""

import json
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import lambda_function


class TestUsernameValidation(unittest.TestCase):
    def test_valid_usernames(self):
        valid_cases = ["octocat", "torvalds", "john-doe", "a-b-c", "user123", "a", "x" * 39]
        for username in valid_cases:
            with self.subTest(username=username):
                self.assertTrue(lambda_function.validate_username(username))

    def test_invalid_usernames(self):
        invalid_cases = [
            "",
            None,
            " ",
            "-octocat",          # leading hyphen
            "octocat-",          # trailing hyphen
            "user--name",        # double hyphen
            "user@domain",       # special character
            "user name",         # space
            "x" * 40,            # exceeds 39 chars
            "user.name",         # dot
        ]
        for username in invalid_cases:
            with self.subTest(username=username):
                self.assertFalse(lambda_function.validate_username(username))


class TestScoringAndRating(unittest.TestCase):
    def test_activity_rating_thresholds(self):
        # 0-17: Good
        self.assertEqual(lambda_function.calculate_activity_rating(0), "Good")
        self.assertEqual(lambda_function.calculate_activity_rating(17), "Good")
        # 18-34: Very Good
        self.assertEqual(lambda_function.calculate_activity_rating(18), "Very Good")
        self.assertEqual(lambda_function.calculate_activity_rating(34), "Very Good")
        # 35-53: Excellent
        self.assertEqual(lambda_function.calculate_activity_rating(35), "Excellent")
        self.assertEqual(lambda_function.calculate_activity_rating(53), "Excellent")
        # None: Insufficient data
        self.assertEqual(lambda_function.calculate_activity_rating(None), "Insufficient data")

    def test_repository_rating_commit_above_10(self):
        # All 3 signals pass: README, <180d, commits >= 10 (commits=25)
        rating, score = lambda_function.rate_repository(
            has_readme=True, recent_push=True, commit_count=25,
            readme_evaluated=True, commits_evaluated=True
        )
        self.assertEqual((rating, score), ("Excellent", 3))

    def test_repository_rating_commit_equal_10(self):
        # Exactly 10 commits -> meets >=10 threshold
        rating, score = lambda_function.rate_repository(
            has_readme=True, recent_push=True, commit_count=10,
            readme_evaluated=True, commits_evaluated=True
        )
        self.assertEqual((rating, score), ("Excellent", 3))

    def test_repository_rating_commit_below_10(self):
        # 9 commits -> fails commits signal, passes README & recency -> 2 points
        rating, score = lambda_function.rate_repository(
            has_readme=True, recent_push=True, commit_count=9,
            readme_evaluated=True, commits_evaluated=True
        )
        self.assertEqual((rating, score), ("Very Good", 2))

        # 5 commits, only README passes -> 1 point
        rating, score = lambda_function.rate_repository(
            has_readme=True, recent_push=False, commit_count=5,
            readme_evaluated=True, commits_evaluated=True
        )
        self.assertEqual((rating, score), ("Good", 1))

    def test_repository_rating_single_commit(self):
        # 1 commit (single commit repo)
        rating, score = lambda_function.rate_repository(
            has_readme=True, recent_push=False, commit_count=1,
            readme_evaluated=True, commits_evaluated=True
        )
        self.assertEqual((rating, score), ("Good", 1))

        # 1 commit with README + recent push -> 2 points
        rating, score = lambda_function.rate_repository(
            has_readme=True, recent_push=True, commit_count=1,
            readme_evaluated=True, commits_evaluated=True
        )
        self.assertEqual((rating, score), ("Very Good", 2))

    def test_repository_rating_description_removed_from_scoring(self):
        # Description is not a parameter and does not affect the 3 signals
        rating_with_all = lambda_function.rate_repository(
            has_readme=True, recent_push=True, commit_count=15,
            readme_evaluated=True, commits_evaluated=True
        )
        self.assertEqual(rating_with_all, ("Excellent", 3))

    def test_repository_rating_api_failures(self):
        # README check failed (e.g. rate limit / network error)
        rating, score = lambda_function.rate_repository(
            has_readme=False, recent_push=True, commit_count=20,
            readme_evaluated=False, commits_evaluated=True
        )
        self.assertEqual(rating, "Not evaluated")

        # Commit count check failed (commits_evaluated = False)
        rating, score = lambda_function.rate_repository(
            has_readme=True, recent_push=True, commit_count=None,
            readme_evaluated=True, commits_evaluated=False
        )
        self.assertEqual(rating, "Not evaluated")

        # Both failed
        rating, score = lambda_function.rate_repository(
            has_readme=False, recent_push=True, commit_count=None,
            readme_evaluated=False, commits_evaluated=False
        )
        self.assertEqual(rating, "Not evaluated")


class TestCommitCountFetcher(unittest.TestCase):
    @patch("lambda_function.github_request")
    def test_link_header_pagination(self, mock_request):
        # Link header with rel="last" page=42
        link = '<https://api.github.com/repositories/1/commits?per_page=1&sha=main&page=2>; rel="next", <https://api.github.com/repositories/1/commits?per_page=1&sha=main&page=42>; rel="last"'
        mock_request.return_value = (200, [{"sha": "abc"}], {"Link": link})

        count, evaluated = lambda_function.fetch_repo_commit_count("owner", "repo", "main")
        self.assertTrue(evaluated)
        self.assertEqual(count, 42)

    @patch("lambda_function.github_request")
    def test_single_commit_no_link_header(self, mock_request):
        # 1 commit, no link header
        mock_request.return_value = (200, [{"sha": "abc"}], {})

        count, evaluated = lambda_function.fetch_repo_commit_count("owner", "repo", "main")
        self.assertTrue(evaluated)
        self.assertEqual(count, 1)

    @patch("lambda_function.github_request")
    def test_empty_repo_409(self, mock_request):
        # Empty repo returning 409 Conflict
        mock_request.return_value = (409, {"message": "Git Repository is empty."}, {})

        count, evaluated = lambda_function.fetch_repo_commit_count("owner", "repo", "main")
        self.assertTrue(evaluated)
        self.assertEqual(count, 0)

    @patch("lambda_function.github_request")
    def test_api_failure_404_or_500(self, mock_request):
        # 404 branch not found
        mock_request.return_value = (404, {"message": "Not Found"}, {})
        count, evaluated = lambda_function.fetch_repo_commit_count("owner", "repo", "main")
        self.assertFalse(evaluated)
        self.assertIsNone(count)


class TestContributionCalendarProcessing(unittest.TestCase):
    def test_contributions_boundary_and_filtering(self):
        now_utc = datetime(2026, 11, 17, 12, 0, 0, tzinfo=timezone.utc)
        one_year_ago = now_utc - timedelta(days=365)

        sample_weeks = [
            # Week before window
            {
                "contributionDays": [
                    {"date": "2024-01-01", "contributionCount": 10, "color": "#216e39"}
                ]
            },
            # Week on window start
            {
                "contributionDays": [
                    {"date": one_year_ago.strftime("%Y-%m-%d"), "contributionCount": 5, "color": "#40c463"},
                    {"date": (one_year_ago + timedelta(days=1)).strftime("%Y-%m-%d"), "contributionCount": 0, "color": "#ebedf0"}
                ]
            },
            # Week around New Year boundary
            {
                "contributionDays": [
                    {"date": "2025-12-31", "contributionCount": 3, "color": "#40c463"},
                    {"date": "2026-01-01", "contributionCount": 4, "color": "#40c463"}
                ]
            },
            # Current day
            {
                "contributionDays": [
                    {"date": now_utc.strftime("%Y-%m-%d"), "contributionCount": 2, "color": "#40c463"}
                ]
            }
        ]

        calendar = {"weeks": sample_weeks}
        result = lambda_function.process_contributions(calendar, now_utc)

        self.assertTrue(result["available"])
        daily_dates = [d["date"] for d in result["daily"]]
        self.assertNotIn("2024-01-01", daily_dates)
        self.assertIn(one_year_ago.strftime("%Y-%m-%d"), daily_dates)
        self.assertIn("2025-12-31", daily_dates)
        self.assertIn("2026-01-01", daily_dates)
        self.assertIn(now_utc.strftime("%Y-%m-%d"), daily_dates)

        expected_total = 5 + 0 + 3 + 4 + 2
        self.assertEqual(result["total_contributions"], expected_total)
        self.assertEqual(result["active_weeks"], 3)
        self.assertEqual(result["total_observed_weeks"], 3)


class TestSuggestions(unittest.TestCase):
    def test_suggestions_generation(self):
        analyzed_repos = [
            {"checks": {"has_readme": False, "recent_push": False, "commits_ge_10": False, "readme_evaluated": True, "commits_evaluated": True}},
            {"checks": {"has_readme": False, "recent_push": False, "commits_ge_10": True, "readme_evaluated": True, "commits_evaluated": True}}
        ]
        suggestions = lambda_function.generate_suggestions(active_weeks=10, analyzed_repos=analyzed_repos, eligible_repo_count=2)
        self.assertTrue(2 <= len(suggestions) <= 3)
        joined = " ".join(suggestions)
        self.assertIn("regularly", joined)
        self.assertIn("README", joined)

    def test_suggestions_stellar_profile(self):
        analyzed_repos = [
            {"checks": {"has_readme": True, "recent_push": True, "commits_ge_10": True, "readme_evaluated": True, "commits_evaluated": True}}
            for _ in range(5)
        ]
        suggestions = lambda_function.generate_suggestions(active_weeks=45, analyzed_repos=analyzed_repos, eligible_repo_count=5)
        self.assertTrue(2 <= len(suggestions) <= 3)
        joined = " ".join(suggestions)
        self.assertIn("Pin your top", joined)


class TestLambdaHandlerRouting(unittest.TestCase):
    def test_options_cors_preflight(self):
        event = {
            "requestContext": {"http": {"method": "OPTIONS"}},
            "rawPath": "/analyze",
        }
        resp = lambda_function.lambda_handler(event, None)
        self.assertEqual(resp["statusCode"], 204)
        self.assertIn("Access-Control-Allow-Origin", resp["headers"])
        self.assertIn("Access-Control-Allow-Methods", resp["headers"])

    def test_health_check_without_username(self):
        event = {
            "requestContext": {"http": {"method": "GET"}},
            "rawPath": "/analyze",
            "queryStringParameters": {}
        }
        resp = lambda_function.lambda_handler(event, None)
        self.assertEqual(resp["statusCode"], 200)
        body = json.loads(resp["body"])
        self.assertEqual(body["status"], "ok")

    def test_invalid_username_format_returns_400(self):
        event = {
            "requestContext": {"http": {"method": "GET"}},
            "queryStringParameters": {"username": "invalid--username"}
        }
        resp = lambda_function.lambda_handler(event, None)
        self.assertEqual(resp["statusCode"], 400)
        body = json.loads(resp["body"])
        self.assertEqual(body["code"], "INVALID_USERNAME")

    def test_method_not_allowed(self):
        event = {
            "requestContext": {"http": {"method": "DELETE"}},
            "queryStringParameters": {"username": "octocat"}
        }
        resp = lambda_function.lambda_handler(event, None)
        self.assertEqual(resp["statusCode"], 405)


class TestFullAnalysisScenarios(unittest.TestCase):
    @patch("lambda_function.fetch_repo_commit_count")
    @patch("lambda_function.fetch_graphql_contributions")
    @patch("lambda_function.check_repo_readme")
    @patch("lambda_function.fetch_user_repos")
    @patch("lambda_function.fetch_user_profile")
    def test_valid_public_user_success(self, mock_profile, mock_repos, mock_readme, mock_graphql, mock_commits):
        # 1. Profile
        mock_profile.return_value = {
            "login": "studentcoder",
            "name": "Jane Coder",
            "avatar_url": "https://avatars.githubusercontent.com/u/12345?v=4",
            "html_url": "https://github.com/studentcoder",
            "bio": "CS Student @ University",
            "public_repos": 4,
            "followers": 18,
            "created_at": "2023-09-01T10:00:00Z"
        }

        # 2. Repositories
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        mock_repos.return_value = [
            {
                "name": "portfolio",
                "fork": False,
                "size": 150,
                "description": "Personal React portfolio site",
                "language": "JavaScript",
                "stargazers_count": 5,
                "pushed_at": now_iso,
                "default_branch": "main",
                "owner": {"login": "studentcoder"}
            },
            {
                "name": "algo-visualizer",
                "fork": False,
                "size": 250,
                "description": "Graph algorithms in Python",
                "language": "Python",
                "stargazers_count": 12,
                "pushed_at": now_iso,
                "default_branch": "main",
                "owner": {"login": "studentcoder"}
            },
            {
                "name": "forked-library",
                "fork": True,  # Fork -> excluded
                "size": 500,
                "description": "Forked repo",
                "language": "C++",
                "stargazers_count": 1,
                "pushed_at": now_iso,
                "owner": {"login": "studentcoder"}
            },
            {
                "name": "empty-repo",
                "fork": False,
                "size": 0,  # Empty -> excluded
                "description": "Empty project",
                "language": None,
                "stargazers_count": 0,
                "pushed_at": now_iso,
                "owner": {"login": "studentcoder"}
            }
        ]

        # 3. Readme check: both have README
        mock_readme.side_effect = lambda owner, repo, token=None: (True, True)

        # 4. Commit counts: portfolio has 15 commits, algo has 5 commits
        def commit_side_effect(owner, repo, default_branch="main", token=None):
            if repo == "portfolio":
                return 15, True
            return 5, True
        mock_commits.side_effect = commit_side_effect

        # 5. GraphQL contributions
        mock_graphql.return_value = (
            {
                "totalContributions": 240,
                "weeks": [
                    {
                        "contributionDays": [
                            {"date": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "contributionCount": 4, "color": "#40c463"}
                        ]
                    }
                ]
            },
            None
        )

        event = {
            "requestContext": {"http": {"method": "GET"}},
            "queryStringParameters": {"username": "studentcoder"}
        }

        response = lambda_function.lambda_handler(event, None)
        self.assertEqual(response["statusCode"], 200)

        data = json.loads(response["body"])
        self.assertTrue(data["success"])
        self.assertEqual(data["username"], "studentcoder")
        self.assertEqual(data["profile"]["name"], "Jane Coder")

        # Only 2 eligible repos
        self.assertEqual(data["metrics"]["eligible_repos_count"], 2)
        self.assertEqual(data["metrics"]["analyzed_repos_count"], 2)

        # Portfolio: has README (+1), recent push (+1), 15 commits (+1) -> 3 points (Excellent)
        portfolio = data["repositories"][0]
        self.assertEqual(portfolio["score"], 3)
        self.assertEqual(portfolio["rating"], "Excellent")
        self.assertEqual(portfolio["commit_count"], 15)
        self.assertEqual(portfolio["commit_count_display"], "15")
        self.assertTrue(portfolio["checks"]["commits_ge_10"])

        # Algo: has README (+1), recent push (+1), 5 commits (+0) -> 2 points (Very Good)
        algo = data["repositories"][1]
        self.assertEqual(algo["score"], 2)
        self.assertEqual(algo["rating"], "Very Good")
        self.assertEqual(algo["commit_count"], 5)
        self.assertFalse(algo["checks"]["commits_ge_10"])

    @patch("lambda_function.fetch_user_profile")
    def test_nonexistent_user_returns_404(self, mock_profile):
        mock_profile.side_effect = LookupError("GitHub user 'nonexistent-user-404' was not found.")

        event = {
            "requestContext": {"http": {"method": "GET"}},
            "queryStringParameters": {"username": "nonexistent-user-404"}
        }
        resp = lambda_function.lambda_handler(event, None)
        self.assertEqual(resp["statusCode"], 404)
        body = json.loads(resp["body"])
        self.assertEqual(body["code"], "USER_NOT_FOUND")

    @patch("lambda_function.fetch_user_profile")
    def test_rate_limit_exceeded_returns_429(self, mock_profile):
        mock_profile.side_effect = PermissionError("GitHub API rate limit exceeded.")

        event = {
            "requestContext": {"http": {"method": "GET"}},
            "queryStringParameters": {"username": "busyuser"}
        }
        resp = lambda_function.lambda_handler(event, None)
        self.assertEqual(resp["statusCode"], 429)
        body = json.loads(resp["body"])
        self.assertEqual(body["code"], "RATE_LIMIT_OR_PERMISSION_ERROR")

    @patch("lambda_function.fetch_graphql_contributions")
    @patch("lambda_function.fetch_user_repos")
    @patch("lambda_function.fetch_user_profile")
    def test_account_with_zero_repositories(self, mock_profile, mock_repos, mock_graphql):
        mock_profile.return_value = {
            "login": "zerorepos",
            "name": "Zero Repos User",
            "public_repos": 0,
            "created_at": "2024-01-01T00:00:00Z"
        }
        mock_repos.return_value = []
        mock_graphql.return_value = (None, "No GITHUB_TOKEN configured")

        event = {
            "requestContext": {"http": {"method": "GET"}},
            "queryStringParameters": {"username": "zerorepos"}
        }
        resp = lambda_function.lambda_handler(event, None)
        self.assertEqual(resp["statusCode"], 200)
        data = json.loads(resp["body"])
        self.assertEqual(data["metrics"]["eligible_repos_count"], 0)
        self.assertEqual(len(data["repositories"]), 0)

    @patch("lambda_function.fetch_repo_commit_count")
    @patch("lambda_function.fetch_graphql_contributions")
    @patch("lambda_function.check_repo_readme")
    @patch("lambda_function.fetch_user_repos")
    @patch("lambda_function.fetch_user_profile")
    def test_repo_commit_api_failure(self, mock_profile, mock_repos, mock_readme, mock_graphql, mock_commits):
        mock_profile.return_value = {"login": "dev", "public_repos": 1, "created_at": "2024-01-01T00:00:00Z"}
        mock_repos.return_value = [
            {
                "name": "project-error",
                "fork": False,
                "size": 50,
                "description": "Test",
                "language": "Go",
                "pushed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "default_branch": "main",
                "owner": {"login": "dev"}
            }
        ]
        mock_readme.return_value = (True, True)
        # Commit check fails
        mock_commits.return_value = (None, False)
        mock_graphql.return_value = (None, None)

        event = {
            "requestContext": {"http": {"method": "GET"}},
            "queryStringParameters": {"username": "dev"}
        }
        resp = lambda_function.lambda_handler(event, None)
        self.assertEqual(resp["statusCode"], 200)
        data = json.loads(resp["body"])
        repo = data["repositories"][0]
        self.assertFalse(repo["checks"]["commits_evaluated"])
        self.assertEqual(repo["rating"], "Not evaluated")
        self.assertEqual(repo["commit_count_display"], "N/A")


if __name__ == "__main__":
    unittest.main()
