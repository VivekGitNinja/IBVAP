"""
IBVAP — Tactical C4ISR High-Concurrency Load Testing Engine
Simulates multi-operator border control load, live video queries,
incident triage spikes, and Prometheus telemetry scraping.
Target SLA: 95th percentile latency < 200ms at 100+ concurrent operators.
"""

from locust import HttpUser, task, between, events
import logging

logger = logging.getLogger("ibvap.locust")


class TacticalOperatorUser(HttpUser):
    """Simulates active field border operators monitoring live feeds and triaging alerts."""

    weight = 3
    wait_time = between(0.5, 2.0)

    def on_start(self):
        """Authenticate as operator and retain JWT bearer token."""
        self.headers = {}
        try:
            res = self.client.post(
                "/api/v1/auth/token",
                data={"username": "operator", "password": "operator123"},
                name="/api/v1/auth/token [Login]",
            )
            if res.status_code == 200:
                token = res.json().get("access_token")
                self.headers["Authorization"] = f"Bearer {token}"
        except Exception as e:
            logger.warning(f"Operator authentication failed during load test: {e}")

    @task(5)
    def poll_dashboard_status(self):
        """High-frequency dashboard status polling."""
        self.client.get("/api/v1/status", headers=self.headers, name="/api/v1/status")

    @task(3)
    def fetch_cameras_grid(self):
        """Fetch active camera feeds for the surveillance grid."""
        self.client.get("/api/v1/cameras", headers=self.headers, name="/api/v1/cameras")

    @task(2)
    def view_incidents(self):
        """Fetch real-time prioritized security incidents."""
        self.client.get("/api/v1/incidents", headers=self.headers, name="/api/v1/incidents")

    @task(1)
    def check_alerts(self):
        """Check active alerts."""
        self.client.get("/api/v1/alerts", headers=self.headers, name="/api/v1/alerts")


class TacticalCommanderUser(HttpUser):
    """Simulates command staff reviewing defense analytics and audit trails."""

    weight = 1
    wait_time = between(1.0, 3.0)

    def on_start(self):
        self.headers = {}
        try:
            res = self.client.post(
                "/api/v1/auth/token",
                data={"username": "commander", "password": "commander123"},
                name="/api/v1/auth/token [Commander Login]",
            )
            if res.status_code == 200:
                token = res.json().get("access_token")
                self.headers["Authorization"] = f"Bearer {token}"
        except Exception as e:
            logger.warning(f"Commander login failed: {e}")

    @task(3)
    def review_audit_logs(self):
        """Audit trail verification."""
        self.client.get("/api/v1/audit", headers=self.headers, name="/api/v1/audit")

    @task(2)
    def detailed_system_health(self):
        """Detailed system health check."""
        self.client.get("/api/v1/health/detailed", headers=self.headers, name="/api/v1/health/detailed")


class PrometheusTelemetryScraper(HttpUser):
    """Simulates external Prometheus scraper gathering cluster metrics."""

    weight = 1
    wait_time = between(4.0, 6.0)

    @task
    def scrape_metrics(self):
        self.client.get("/metrics", name="/metrics [Scrape]")


@events.quitting.add_listener
def verify_load_sla(environment, **_kwargs):
    """Enforce automated CI/CD SLA quality gates."""
    stats = environment.runner.stats.total
    if stats.num_requests > 0:
        p95 = stats.get_response_time_percentile(0.95)
        fail_ratio = stats.fail_ratio
        print("\n" + "=" * 60)
        print(f"IBVAP LOAD SLA REPORT:")
        print(f"Total Requests: {stats.num_requests}")
        print(f"Fail Ratio:     {fail_ratio * 100:.2f}% (Threshold: < 1%)")
        print(f"95th Pct Lat:   {p95:.1f}ms (Threshold: < 200ms)")
        print("=" * 60)
        if fail_ratio > 0.01:
            logger.error("SLA BREACH: Failure ratio exceeded 1% threshold!")
            environment.process_exit_code = 1
        elif p95 > 200:
            logger.warning("SLA WARNING: P95 latency exceeded 200ms target.")
