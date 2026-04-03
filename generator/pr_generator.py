"""Deterministic PR generator for benchmark tasks."""

from __future__ import annotations
from typing import Any, Dict, List


class PRGenerator:
    """Generates deterministic simulated pull request data for each difficulty level."""

    BENCHMARK_VERSION = "v1"

    @staticmethod
    def generate_easy_pr() -> Dict[str, Any]:
        return {
            "file_name": "utils.py",
            "diff": (
                "def calculate_total(items):\n"
                "    x = 0\n"
                "    total = 0\n"
                "    for item in items:\n"
                "        total += item.price\n"
                "    return total\n"
            ),
            "issues": ["missing_docstring", "unused_variable"],
            "metadata": {
                "lines_changed": 6,
                "task_type": "style_documentation_review",
                "difficulty": "easy",
                "benchmark_version": PRGenerator.BENCHMARK_VERSION,
            },
        }

    @staticmethod
    def generate_medium_pr() -> Dict[str, Any]:
        return {
            "file_name": "login.py",
            "diff": (
                'def authenticate(user_id, password):\n'
                '    query = "SELECT * FROM users WHERE id=" + user_id\n'
                '    result = db.execute(query)\n'
                '    if result and result.password == password:\n'
                '        return True\n'
                '    return False\n'
                '    # TODO: add unit tests\n'
            ),
            "issues": ["sql_injection", "missing_unit_tests", "logic_bug"],
            "metadata": {
                "lines_changed": 14,
                "task_type": "security_review",
                "difficulty": "medium",
                "benchmark_version": PRGenerator.BENCHMARK_VERSION,
            },
        }

    @staticmethod
    def generate_hard_pr() -> Dict[str, Any]:
        return {
            "file_name": "auth_middleware.py",
            "diff": (
                "class AuthMiddleware:\n"
                "    def process_request(self, request):\n"
                "        token = request.headers.get('Authorization')\n"
                "        if token is None:\n"
                "            return  # silently passes unauthenticated requests\n"
                "        user = self.validate_token(token)\n"
                "        request.user = user\n"
                "\n"
                "    def validate_token(self, token):\n"
                "        try:\n"
                "            payload = jwt.decode(token, SECRET_KEY)\n"
                "            return User.objects.get(id=payload['user_id'])\n"
                "        except Exception:\n"
                "            return None  # swallows all errors\n"
                "\n"
                "    def get_user_data(self, user_id):\n"
                "        results = []\n"
                "        for record in Record.objects.all():  # full table scan\n"
                "            if record.user_id == user_id:\n"
                "                results.append(record)\n"
                "        return results\n"
                "\n"
                "    def run_health_check(self):\n"
                "        import time\n"
                "        if time.time() % 2 == 0:\n"
                "            return True\n"
                "        return False  # flaky: depends on system clock\n"
            ),
            "issues": [
                "authentication_bypass",
                "performance_regression",
                "flaky_test_behavior",
            ],
            "metadata": {
                "lines_changed": 27,
                "task_type": "security_and_performance_review",
                "difficulty": "hard",
                "benchmark_version": PRGenerator.BENCHMARK_VERSION,
            },
        }
