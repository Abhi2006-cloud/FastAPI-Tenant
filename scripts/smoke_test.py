#!/usr/bin/env python3
"""
Production Verification & Smoke Test Script

Runs end-to-end verification against a deployed backend (Render / Local):
1. /health/live (Liveness check)
2. /health (Readiness / dependency check)
3. POST /demo/session (Real multi-tenant session generation)
4. GET /organizations/{org_id}/entitlements (Plan quotas & limits)
5. POST /files/upload (Small file upload)
6. GET /files/{file_id}/download (File retrieval)
7. GET /audit-logs/export (Feature gate: 402 PLAN_FEATURE_LOCKED on free)
8. Login burst to trigger rate limiting (429 RATE_LIMITED + Retry-After)
9. POST /auth/logout and access-token reuse (401 Session has been revoked)

Usage:
    python scripts/smoke_test.py [BASE_URL]
    python scripts/smoke_test.py https://ai-workspace-backend.onrender.com
"""

import io
import os
import sys
import time
import uuid
import requests


class SmokeTestRunner:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.results = []
        self.org_id = None
        self.access_token = None
        self.refresh_token = None
        self.file_id = None
        self.file_content = b"AI Workspace smoke test file payload - verification ok"
        self.test_ip = f"203.0.113.{int(time.time()) % 200 + 10}"

    def record(self, step: int, name: str, endpoint: str, status_code: int, duration_ms: float, passed: bool, notes: str = ""):
        self.results.append({
            "step": step,
            "name": name,
            "endpoint": endpoint,
            "status": status_code,
            "duration": f"{duration_ms:.1f}ms",
            "passed": passed,
            "notes": notes,
        })

    def run_all(self) -> bool:
        print("=" * 80)
        print(f"🚀 AI Workspace SaaS Backend - Smoke Test Runner")
        print(f"🎯 Target URL : {self.base_url}")
        print(f"🌐 Client IP  : {self.test_ip}")
        print("=" * 80)

        # 1. /health/live
        t0 = time.time()
        try:
            r = self.session.get(f"{self.base_url}/health/live", timeout=15)
            ms = (time.time() - t0) * 1000
            passed = r.status_code == 200 and r.json().get("status") == "ok"
            self.record(1, "Liveness Probe", "GET /health/live", r.status_code, ms, passed)
        except Exception as e:
            self.record(1, "Liveness Probe", "GET /health/live", 0, 0, False, str(e))

        # 2. /health
        t0 = time.time()
        try:
            r = self.session.get(f"{self.base_url}/health", timeout=15)
            ms = (time.time() - t0) * 1000
            data = r.json()
            passed = r.status_code == 200 and data.get("database") == "connected" and data.get("redis") == "connected"
            note = f"status={data.get('status')}, db={data.get('database')}, redis={data.get('redis')}"
            self.record(2, "Readiness / Dependency Probe", "GET /health", r.status_code, ms, passed, note)
        except Exception as e:
            self.record(2, "Readiness / Dependency Probe", "GET /health", 0, 0, False, str(e))

        # 3. POST /demo/session
        t0 = time.time()
        try:
            headers = {"X-Forwarded-For": self.test_ip}
            r = self.session.post(f"{self.base_url}/demo/session", headers=headers, timeout=15)
            ms = (time.time() - t0) * 1000
            passed = r.status_code == 201
            if passed:
                data = r.json()
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                self.org_id = data.get("organization_id")
                passed = bool(self.access_token and self.org_id and self.refresh_token)
            self.record(3, "Provision Demo Session", "POST /demo/session", r.status_code, ms, passed, f"org_id={self.org_id}")
        except Exception as e:
            self.record(3, "Provision Demo Session", "POST /demo/session", 0, 0, False, str(e))

        if not self.access_token or not self.org_id:
            print("\n❌ Aborting subsequent tests: could not obtain active session token.")
            self.print_summary()
            return False

        auth_headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Organization-Id": self.org_id,
            "X-Forwarded-For": self.test_ip,
        }

        # 4. GET /organizations/{org_id}/entitlements
        t0 = time.time()
        try:
            r = self.session.get(f"{self.base_url}/organizations/{self.org_id}/entitlements", headers=auth_headers, timeout=15)
            ms = (time.time() - t0) * 1000
            data = r.json()
            passed = r.status_code == 200 and data.get("plan") in ("free", "pro") and "limits" in data
            self.record(4, "Get Entitlements & Limits", f"GET /organizations/{self.org_id[:8]}.../entitlements", r.status_code, ms, passed, f"plan={data.get('plan')}")
        except Exception as e:
            self.record(4, "Get Entitlements & Limits", "GET .../entitlements", 0, 0, False, str(e))

        # 5. POST /files/upload
        t0 = time.time()
        try:
            files = {"file": ("smoke_test.txt", io.BytesIO(self.file_content), "text/plain")}
            r = self.session.post(f"{self.base_url}/files/upload", headers=auth_headers, files=files, timeout=15)
            ms = (time.time() - t0) * 1000
            passed = r.status_code == 201
            if passed:
                self.file_id = r.json().get("id")
                passed = bool(self.file_id)
            self.record(5, "Upload File (Storage Backend)", "POST /files/upload", r.status_code, ms, passed, f"file_id={self.file_id}")
        except Exception as e:
            self.record(5, "Upload File (Storage Backend)", "POST /files/upload", 0, 0, False, str(e))

        # 6. GET /files/{file_id}/download
        if self.file_id:
            t0 = time.time()
            try:
                r = self.session.get(f"{self.base_url}/files/{self.file_id}/download", headers=auth_headers, timeout=15)
                ms = (time.time() - t0) * 1000
                passed = r.status_code == 200 and r.content == self.file_content
                self.record(6, "Download & Verify File", f"GET /files/{self.file_id[:8]}.../download", r.status_code, ms, passed, f"bytes={len(r.content)}")
            except Exception as e:
                self.record(6, "Download & Verify File", "GET /files/.../download", 0, 0, False, str(e))
        else:
            self.record(6, "Download & Verify File", "GET /files/.../download", 0, 0, False, "Skipped (no file_id)")

        # 7. GET /audit-logs/export (Expect 402 on free tier)
        t0 = time.time()
        try:
            r = self.session.get(f"{self.base_url}/audit-logs/export", headers=auth_headers, timeout=15)
            ms = (time.time() - t0) * 1000
            data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            passed = r.status_code == 402 and data.get("detail", {}).get("code") == "PLAN_FEATURE_LOCKED"
            self.record(7, "Audit Export Feature Gate (402)", "GET /audit-logs/export", r.status_code, ms, passed, "PLAN_FEATURE_LOCKED")
        except Exception as e:
            self.record(7, "Audit Export Feature Gate (402)", "GET /audit-logs/export", 0, 0, False, str(e))

        # 8. Login burst to trigger rate limit (429 + Retry-After)
        burst_ip = f"198.51.100.{int(time.time()) % 150 + 20}"
        hit_429 = False
        retry_after_hdr = None
        t0 = time.time()
        try:
            for _ in range(12):
                res = self.session.post(
                    f"{self.base_url}/auth/login",
                    json={"email": f"burst_{uuid.uuid4().hex[:6]}@example.com", "password": "DummyPassword123!"},
                    headers={"X-Forwarded-For": burst_ip},
                    timeout=10,
                )
                if res.status_code == 429:
                    hit_429 = True
                    retry_after_hdr = res.headers.get("Retry-After")
                    break
            ms = (time.time() - t0) * 1000
            passed = hit_429 and bool(retry_after_hdr)
            self.record(8, "Burst Rate Limit (10/min/IP -> 429)", "POST /auth/login (burst)", 429 if hit_429 else 401, ms, passed, f"Retry-After={retry_after_hdr}s")
        except Exception as e:
            self.record(8, "Burst Rate Limit (10/min/IP -> 429)", "POST /auth/login (burst)", 0, 0, False, str(e))

        # 9. POST /auth/logout (Revoke session)
        t0 = time.time()
        try:
            r = self.session.post(
                f"{self.base_url}/auth/logout",
                json={"refresh_token": self.refresh_token},
                headers=auth_headers,
                timeout=15,
            )
            ms = (time.time() - t0) * 1000
            passed = r.status_code in (200, 204)
            self.record(9, "Logout & Revoke Session", "POST /auth/logout", r.status_code, ms, passed, "Session denylisted in Redis")
        except Exception as e:
            self.record(9, "Logout & Revoke Session", "POST /auth/logout", 0, 0, False, str(e))

        # 10. Reusing revoked access token -> 401 Session has been revoked
        t0 = time.time()
        try:
            r = self.session.get(f"{self.base_url}/organizations/{self.org_id}/entitlements", headers=auth_headers, timeout=15)
            ms = (time.time() - t0) * 1000
            detail = r.json().get("detail") if r.headers.get("content-type", "").startswith("application/json") else ""
            passed = r.status_code == 401 and "Session has been revoked" in str(detail)
            self.record(10, "Token Revocation Verification", "GET .../entitlements (revoked)", r.status_code, ms, passed, str(detail))
        except Exception as e:
            self.record(10, "Token Revocation Verification", "GET .../entitlements (revoked)", 0, 0, False, str(e))

        return self.print_summary()

    def print_summary(self) -> bool:
        print("\n" + "=" * 90)
        print(f"{'#':<3} | {'Test Check':<34} | {'Endpoint':<32} | {'HTTP':<5} | {'Duration':<8} | {'Result':<6}")
        print("-" * 90)
        all_passed = True
        for r in self.results:
            status_text = "PASS ✅" if r["passed"] else "FAIL ❌"
            if not r["passed"]:
                all_passed = False
            print(f"{r['step']:<3} | {r['name']:<34} | {r['endpoint']:<32} | {r['status']:<5} | {r['duration']:<8} | {status_text:<6}")
            if r["notes"]:
                print(f"    └─ Note: {r['notes']}")

        print("=" * 90)
        if all_passed:
            print("🎉 ALL SMOKE TESTS PASSED - Service is verified and production-ready!")
        else:
            print("⚠️ SOME SMOKE TESTS FAILED - Check server logs for failed assertions.")
        print("=" * 90 + "\n")
        return all_passed


def main():
    target_url = sys.argv[1] if len(sys.argv) > 1 else os.getenv("BASE_URL", "http://127.0.0.1:8000")
    runner = SmokeTestRunner(target_url)
    success = runner.run_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

