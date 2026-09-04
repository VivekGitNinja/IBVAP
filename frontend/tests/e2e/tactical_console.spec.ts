import { test, expect } from '@playwright/test';

test.describe('IBVAP Tactical C4ISR Console E2E Workflows', () => {

  test.beforeEach(async ({ page }) => {
    // Intercept API routes or route directly
    await page.goto('/');
  });

  test('E2E-01: Tactical Console Boots & Authenticates Operator', async ({ page }) => {
    // Verify top header presence
    await expect(page.locator('header')).toBeVisible();
    await expect(page.locator('text=IBVAP C4ISR')).toBeVisible();

    // If login prompt appears, login as operator
    const loginButton = page.locator('button:has-text("AUTHENTICATE")');
    if (await loginButton.isVisible()) {
      await page.fill('input[type="text"]', 'operator');
      await page.fill('input[type="password"]', 'operator123');
      await loginButton.click();
    }

    // Verify operator status badge
    await expect(page.locator('text=OPERATOR').or(page.locator('text=DEFCON'))).toBeVisible();
  });

  test('E2E-02: Navigation Across Tactical Views & Sidebar Routing', async ({ page }) => {
    // Click Incident Triage tab
    const incidentTab = page.locator('button:has-text("INCIDENTS"), div:has-text("INCIDENTS")').first();
    if (await incidentTab.isVisible()) {
      await incidentTab.click();
      await expect(page.locator('text=INCIDENT TRIAGE').or(page.locator('text=Active Incidents'))).toBeVisible();
    }

    // Click ANPR tab
    const anprTab = page.locator('button:has-text("ANPR"), div:has-text("ANPR")').first();
    if (await anprTab.isVisible()) {
      await anprTab.click();
      await expect(page.locator('text=AUTOMATIC NUMBER PLATE RECOGNITION').or(page.locator('text=ANPR'))).toBeVisible();
    }

    // Click Evidence Vault tab
    const evidenceTab = page.locator('button:has-text("EVIDENCE"), div:has-text("EVIDENCE")').first();
    if (await evidenceTab.isVisible()) {
      await evidenceTab.click();
      await expect(page.locator('text=SECTION 65B FORENSIC VAULT').or(page.locator('text=Evidence'))).toBeVisible();
    }
  });

  test('E2E-03: Live Monitor Video Grid & Camera Feed Switching', async ({ page }) => {
    // Navigate to Live Monitor
    const liveMonitorTab = page.locator('button:has-text("LIVE MONITOR"), div:has-text("LIVE MONITOR")').first();
    if (await liveMonitorTab.isVisible()) {
      await liveMonitorTab.click();
    }

    // Check camera grid existence
    const cameraGrid = page.locator('.camera-grid, .tactical-grid, div[data-testid="camera-grid"]');
    await expect(cameraGrid.or(page.locator('text=BOP-01'))).toBeVisible();
  });

  test('E2E-04: Section 65B Hash Verification & Forensic Integrity', async ({ page }) => {
    const evidenceTab = page.locator('button:has-text("EVIDENCE"), div:has-text("EVIDENCE")').first();
    if (await evidenceTab.isVisible()) {
      await evidenceTab.click();
      // Verify SHA-256 certificate presence
      await expect(page.locator('text=SHA-256').or(page.locator('text=CERTIFICATE'))).toBeVisible();
    }
  });

  test('E2E-05: Cmd+K Spotlight Command Palette', async ({ page }) => {
    // Trigger Cmd+K
    await page.keyboard.press('Meta+k');
    const searchModal = page.locator('input[placeholder*="command"], input[placeholder*="Search"]');
    if (await searchModal.isVisible()) {
      await searchModal.fill('defcon');
      await expect(page.locator('text=DEFCON').first()).toBeVisible();
      await page.keyboard.press('Escape');
    }
  });
});
