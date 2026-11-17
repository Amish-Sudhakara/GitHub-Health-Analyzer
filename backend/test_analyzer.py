"""
Comprehensive Unit Tests for GitHub Student Health Analyzer Backend.
Tests all requirements using Python's standard unittest and unittest.mock.
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

    def test_repository_rating(self):
        # All checks pass
        rating, score = lambda_function.rate_repository(has_desc=True, has_readme=True, recent_push=True, readme_evaluated=True)
        self.assertEqual((rating, score), ("Excellent", 3))

        # 2 checks pass
        rating, score = lambda_function.rate_repository(has_desc=True, has_readme=True, recent_push=False, readme_evaluated=True)
        self.assertEqual((rating, score), ("Very Good", 2))

        # 1 check passes
        rating, score = lambda_function.rate_repository(has_desc=False, has_readme=True, recent_push=False, readme_evaluated=True)
        self.assertEqual((rating, score), ("Good", 1))

        # 0 checks pass
        rating, score = lambda_function.rate_repository(has_desc=False, has_readme=False, recent_push=False, readme_evaluated=True)
        self.assertEqual((rating, score), ("Good", 0))

        # README check failed due to API error
        rating, score = lambda_function.rate_repository(has_desc=True, has_readme=False, recent_push=True, readme_evaluated=False)
        self.assertEqual(rating, "Not evaluated")


class TestContributionCalendarProcessing(unittest.TestCase):
    def test_contributions_boundary_and_filtering(self):
        now_utc = datetime(2026, 11, 17, 12, 0, 0, tzinfo=timezone.utc)
        one_year_ago = now_utc - timedelta(days=365)

        # Mock calendar containing days within, before, and after interval
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
        # 2024-01-01 should be excluded
        daily_dates = [d["date"] for d in result["daily"]]
        self.assertNotIn("2024-01-01", daily_dates)
        self.assertIn(one_year_ago.strftime("%Y-%m-%d"), daily_dates)
        self.assertIn("2025-12-31", daily_dates)
        self.assertIn("2026-01-01", daily_dates)
        self.assertIn(now_utc.strftime("%Y-%m-%d"), daily_dates)

        # Total contributions sum
        expected_total = 5 + 0 + 3 + 4 + 2
        self.assertEqual(result["total_contributions"], expected_total)
        # Active weeks (3 weeks with > 0 contributions)
        self.assertEqual(result["active_weeks"], 3)
        self.assertEqual(result["total_observed_weeks"], 3)


class TestSuggestions(unittest.TestCase):
    def test_suggestions_generation(self):
        # Case: Low activity, missing readmes, missing descriptions
        analyzed_repos = [
            {"checks": {"has_description": False, "has_readme": False, "recent_push": False, "readme_evaluated": True}},
            {"checks": {"has_description": True, "has_readme": False, "recent_push": False, "readme_evaluated": True}}
        ]
        suggestions = lambda_function.generate_suggestions(active_weeks=10, analyzed_repos=analyzed_repos, eligible_repo_count=2)
        self.assertTrue(2 <= len(suggestions) <= 3)
        # Should include activity, readme, and description suggestions
        joined = " ".join(suggestions)
        self.assertIn("regularly", joined)
        self.assertIn("README", joined)
        self.assertIn("descriptions", joined)

    def test_suggestions_stellar_profile(self):
        # Stellar profile
        analyzed_repos = [
            {"checks": {"has_description": True, "has_readme": True, "recent_push": True, "readme_evaluated": True}}
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
    @patch("lambda_function.fetch_graphql_contributions")
    @patch("lambda_function.check_repo_readme")
    @patch("lambda_function.fetch_user_repos")
    @patch("lambda_function.fetch_user_profile")
    def test_valid_public_user_success(self, mock_profile, mock_repos, mock_readme, mock_graphql):
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
                "owner": {"login": "studentcoder"}
            },
            {
                "name": "forked-library",
                "fork": True,  # Fork -> should be ignored!
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
                "size": 0,  # Empty -> should be ignored!
                "description": "Empty project",
                "language": None,
                "stargazers_count": 0,
                "pushed_at": now_iso,
                "owner": {"login": "studentcoder"}
            }
        ]

        # 3. Readme check
        mock_readme.side_effect = lambda owner, repo, token=None: (True, True)

        # 4. GraphQL contributions
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
        self.assertEqual(data["profile"]["created_year"], 2023)

        # Only 2 eligible repos (forked & empty excluded)
        self.assertEqual(data["metrics"]["eligible_repos_count"], 2)
        self.assertEqual(data["metrics"]["analyzed_repos_count"], 2)

        # Language distribution
        langs = [item["language"] for item in data["languages"]]
        self.assertIn("JavaScript", langs)
        self.assertIn("Python", langs)
        self.assertNotIn("C++", langs)

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
        self.assertEqual(data["metrics"]["analyzed_repos_count"], 0)
        self.assertEqual(len(data["repositories"]), 0)
        self.assertEqual(len(data["languages"]), 0)
        self.assertEqual(data["metrics"]["activity_rating"], "Insufficient data")

    @patch("lambda_function.fetch_graphql_contributions")
    @patch("lambda_function.fetch_user_repos")
    @patch("lambda_function.fetch_user_profile")
    def test_account_with_only_forked_repositories(self, mock_profile, mock_repos, mock_graphql):
        mock_profile.return_value = {
            "login": "onlyforks",
            "name": "Fork User",
            "public_repos": 5,
            "created_at": "2023-01-01T00:00:00Z"
        }
        mock_repos.return_value = [
            {"name": f"fork-{i}", "fork": True, "size": 100, "pushed_at": "2026-01-01T00:00:00Z"}
            for i in range(5)
        ]
        mock_graphql.return_value = (None, "Token missing")

        event = {
            "requestContext": {"http": {"method": "GET"}},
            "queryStringParameters": {"username": "onlyforks"}
        }
        resp = lambda_function.lambda_handler(event, None)
        self.assertEqual(resp["statusCode"], 200)
        data = json.loads(resp["body"])
        self.assertEqual(data["metrics"]["eligible_repos_count"], 0)
        self.assertEqual(data["repositories"], [])

    @patch("lambda_function.fetch_graphql_contributions")
    @patch("lambda_function.check_repo_readme")
    @patch("lambda_function.fetch_user_repos")
    @patch("lambda_function.fetch_user_profile")
    def test_repo_checks_missing_readme_and_description(self, mock_profile, mock_repos, mock_readme, mock_graphql):
        mock_profile.return_value = {"login": "dev", "public_repos": 1, "created_at": "2024-01-01T00:00:00Z"}
        old_push = "2024-01-01T00:00:00Z"  # > 180 days ago
        mock_repos.return_value = [
            {
                "name": "undocumented-project",
                "fork": False,
                "size": 50,
                "description": "",  # Missing description
                "language": None,    # Missing language
                "pushed_at": old_push,
                "owner": {"login": "dev"}
            }
        ]
        # Missing README (404 status simulated by check_repo_readme returning False, True)
        mock_readme.return_value = (False, True)
        mock_graphql.return_value = (None, None)

        event = {
            "requestContext": {"http": {"method": "GET"}},
            "queryStringParameters": {"username": "dev"}
        }
        resp = lambda_function.lambda_handler(event, None)
        self.assertEqual(resp["statusCode"], 200)
        data = json.loads(resp["body"])
        repo = data["repositories"][0]
        self.assertFalse(repo["checks"]["has_description"])
        self.assertFalse(repo["checks"]["has_readme"])
        self.assertFalse(repo["checks"]["recent_push"])
        self.assertEqual(repo["score"], 0)
        self.assertEqual(repo["rating"], "Good")
        self.assertEqual(repo["language"], "Not specified")

    @patch("lambda_function.fetch_graphql_contributions")
    @patch("lambda_function.check_repo_readme")
    @patch("lambda_function.fetch_user_repos")
    @patch("lambda_function.fetch_user_profile")
    def test_repo_readme_evaluation_failure(self, mock_profile, mock_repos, mock_readme, mock_graphql):
        mock_profile.return_value = {"login": "dev2", "public_repos": 1, "created_at": "2024-01-01T00:00:00Z"}
        mock_repos.return_value = [
            {
                "name": "project-x",
                "fork": False,
                "size": 50,
                "description": "Some description",
                "language": "Go",
                "pushed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "owner": {"login": "dev2"}
            }
        ]
        # README API error (simulated by readme_evaluated = False)
        mock_readme.return_value = (False, False)
        mock_graphql.return_value = (None, None)

        event = {
            "requestContext": {"http": {"method": "GET"}},
            "queryStringParameters": {"username": "dev2"}
        }
        resp = lambda_function.lambda_handler(event, None)
        self.assertEqual(resp["statusCode"], 200)
        data = json.loads(resp["body"])
        repo = data["repositories"][0]
        self.assertFalse(repo["checks"]["readme_evaluated"])
        self.assertEqual(repo["rating"], "Not evaluated")


if __name__ == "__main__":
    unittest.main()
