"""
BotForge Load Test — Locust configuration.

Simulates realistic user traffic patterns against the API.

Usage:
    # Interactive (with web UI)
    locust -f tests/load/locustfile.py --host=http://localhost:8000

    # Headless (CI-friendly)
    locust -f tests/load/locustfile.py \
        --host=http://localhost:8000 \
        --users 30 --spawn-rate 5 --run-time 2m --headless

    # Against production
    locust -f tests/load/locustfile.py \
        --host=https://botforge.fenloai.com \
        --users 30 --spawn-rate 5 --run-time 5m --headless \
        --csv=results/phase5_load_test

Performance Targets (m7i-flex.large, 8GB RAM, 4 workers):
    Baseline (10 users):  All endpoints <500ms p95, 0% errors
    Normal (30 users):    Analytics <1s, Chat <3s, errors <0.5%
    Burst (100 users):    Analytics <2s, Chat <5s, errors <1%
"""

import random

from locust import HttpUser, between, task


class BotForgeUser(HttpUser):
    """Simulates a typical BotForge user session."""

    wait_time = between(1, 3)
    workspace_id = None

    def on_start(self):
        """Register a fresh user and authenticate."""
        email = f"loadtest-{random.randint(100000, 999999)}@example.com"
        # Register
        resp = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "LoadTest123!",  # pragma: allowlist secret
                "name": "Load Test User",
            },
            name="Auth Register",
        )
        if resp.status_code != 200:
            # If registration fails (user exists), try login
            resp = self.client.post(
                "/api/v1/auth/login",
                json={
                    "email": email,
                    "password": "LoadTest123!",  # pragma: allowlist secret
                },
                name="Auth Login",
            )

        # Extract workspace_id from /me endpoint
        me_resp = self.client.get("/api/v1/auth/me", name="Auth Me")
        if me_resp.status_code == 200:
            data = me_resp.json()
            self.workspace_id = data.get("workspace_id")

    @task(10)
    def get_analytics_overview(self):
        """GET /analytics/overview — Most frequently accessed."""
        self.client.get(
            "/api/v1/analytics/overview",
            name="Analytics Overview",
        )

    @task(5)
    def get_analytics_volume(self):
        """GET /analytics/volume — Chart data."""
        self.client.get(
            "/api/v1/analytics/volume",
            name="Analytics Volume",
        )

    @task(5)
    def get_inbox_conversations(self):
        """GET /inbox/conversations — Inbox list."""
        self.client.get(
            "/api/v1/inbox/conversations?per_page=20",
            name="Inbox Conversations",
        )

    @task(3)
    def get_dashboard_summary(self):
        """GET /dashboard/summary — Dashboard overview."""
        self.client.get(
            "/api/v1/dashboard/summary",
            name="Dashboard Summary",
        )

    @task(3)
    def get_analytics_sentiment(self):
        """GET /analytics/sentiment — Sentiment chart."""
        self.client.get(
            "/api/v1/analytics/sentiment",
            name="Analytics Sentiment",
        )

    @task(3)
    def get_analytics_top_questions(self):
        """GET /analytics/top-questions — FAQ analysis."""
        self.client.get(
            "/api/v1/analytics/top-questions?limit=10",
            name="Analytics Top Questions",
        )

    @task(2)
    def get_analytics_channels(self):
        """GET /analytics/channels — Channel breakdown."""
        self.client.get(
            "/api/v1/analytics/channels",
            name="Analytics Channels",
        )

    @task(2)
    def get_onboarding_progress(self):
        """GET /onboarding/progress — Onboarding state."""
        self.client.get(
            "/api/v1/onboarding/progress",
            name="Onboarding Progress",
        )

    @task(1)
    def get_weekly_insights(self):
        """GET /insights/weekly — LLM-backed, slower."""
        self.client.get(
            "/api/v1/insights/weekly",
            name="Weekly Insights",
        )

    @task(1)
    def get_csv_export(self):
        """GET /export/conversations/csv — CSV download."""
        self.client.get(
            "/api/v1/export/conversations/csv",
            name="Export CSV",
        )

    @task(1)
    def get_storage_usage(self):
        """GET /admin/storage — Storage monitoring."""
        if self.workspace_id:
            self.client.get(
                f"/api/v1/admin/storage/{self.workspace_id}",
                name="Admin Storage",
            )


class BotForgeAdminUser(HttpUser):
    """Simulates admin-specific operations (lower frequency)."""

    wait_time = between(5, 10)
    weight = 1  # 1 admin per 3 regular users
    workspace_id = None

    def on_start(self):
        """Register admin user."""
        email = f"admin-{random.randint(100000, 999999)}@example.com"
        self.client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "AdminTest123!",  # pragma: allowlist secret
                "name": "Load Test Admin",
            },
            name="Admin Register",
        )
        me_resp = self.client.get("/api/v1/auth/me", name="Admin Me")
        if me_resp.status_code == 200:
            self.workspace_id = me_resp.json().get("workspace_id")

    @task(5)
    def get_storage(self):
        """GET /admin/storage — Check storage usage."""
        if self.workspace_id:
            self.client.get(
                f"/api/v1/admin/storage/{self.workspace_id}",
                name="Admin Storage",
            )

    @task(3)
    def get_all_analytics(self):
        """Simulate admin reviewing all analytics pages."""
        self.client.get(
            "/api/v1/analytics/overview",
            name="Admin Analytics Overview",
        )
        self.client.get(
            "/api/v1/analytics/volume",
            name="Admin Analytics Volume",
        )
        self.client.get(
            "/api/v1/analytics/channels",
            name="Admin Analytics Channels",
        )

    @task(1)
    def get_settings(self):
        """GET /settings — Workspace settings."""
        self.client.get(
            "/api/v1/settings",
            name="Admin Settings",
        )
