#!/usr/bin/env python3
"""
IBVAP End-to-End Real Browser Verification Runner
SIH PS-26187 | SSB, Ministry of Home Affairs
Statute: Bharatiya Sakshya Adhiniyam, 2023 §63
"""

import os
import sys
import subprocess
import json
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = PROJECT_ROOT / "e2e" / "evidence"


def check_servers():
    print("\n[VERIFY] Checking Local Server Health Gates...")
    try:
        req = urllib.request.Request("http://localhost:8001/api/v1/system/readiness")
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                print("  ✓ Backend (port 8001) is ONLINE and READY.")
    except Exception as e:
        print(f"  ✗ Backend (port 8001) NOT reachable: {e}")
        return False

    try:
        req = urllib.request.Request("http://localhost:5173/")
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                print("  ✓ Frontend (port 5173) is ONLINE and serving 200 OK.")
    except Exception as e:
        print(f"  ✗ Frontend (port 5173) NOT reachable: {e}")
        return False

    return True


def run_playwright():
    print("\n[VERIFY] Executing Persistent Playwright Verification Suite...")
    cmd = [
        "npx", "playwright", "test",
        "e2e/browser_full_verification.spec.ts",
        "--project=chromium",
        "--reporter=list"
    ]
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    return proc.returncode


def print_telemetry_audit():
    report_path = EVIDENCE_DIR / "console_report.json"
    if not report_path.exists():
        print(f"\n[WARNING] Console report not found at {report_path}")
        return

    with open(report_path, "r") as f:
        data = json.load(f)

    print("\n=======================================================")
    print("        BROWSER CONSOLE & INTEGRITY AUDIT")
    print("=======================================================")
    print(f"Total Console Errors:  {data.get('total_console_errors', 0)}")
    print(f"Total Page Errors:     {data.get('total_page_errors', 0)}")
    print(f"Total Failed Requests: {data.get('total_failed_requests', 0)}")
    print(f"External Outbound Hosts: {data.get('external_hosts', [])}")
    print("=======================================================\n")


def main():
    if not check_servers():
        print("[ERROR] Servers must be running on ports 8001 and 5173 before test run.")
        sys.exit(1)

    code = run_playwright()
    print_telemetry_audit()
    sys.exit(code)


if __name__ == "__main__":
    main()
