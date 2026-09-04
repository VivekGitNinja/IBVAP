import { defineConfig, devices } from '@playwright/test';

/**
 * IBVAP — Playwright End-to-End Test Suite Configuration
 * Verifies tactical C4ISR console user journeys, telemetry, and forensic workflows.
 */
export default defineConfig({
  testDir: '.',
  testMatch: [
    'e2e/**/*.spec.ts',
    'frontend/tests/e2e/**/*.spec.ts',
  ],
  timeout: 90 * 1000,
  expect: {
    timeout: 10000,
  },
  fullyParallel: false,
  workers: 1,
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['list'],
  ],
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:5173',
    viewport: { width: 1440, height: 900 },
    trace: 'retain-on-failure',
    screenshot: 'on',
    video: {
      mode: 'on',
      size: { width: 1440, height: 900 },
    },
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        channel: 'chrome',
        viewport: { width: 1440, height: 900 },
      },
    },
  ],
});
