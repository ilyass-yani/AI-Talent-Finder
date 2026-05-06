import { defineConfig, devices } from '@playwright/test';

const PROD_URL = 'https://ai-talent-finder-production-ed09.up.railway.app';

export default defineConfig({
  testDir: './e2e',
  /* Run tests sequentially — the full-app spec has ordered steps */
  fullyParallel: false,
  /* Fail the build on CI if you accidentally left test.only in the source */
  forbidOnly: !!process.env.CI,
  /* Retry flaky tests once on CI */
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [['html', { open: 'never' }], ['list']],

  use: {
    baseURL: PROD_URL,
    /* Keep a trace on first retry so failures are debuggable */
    trace: 'on-first-retry',
    /* Screenshot every step on failure */
    screenshot: 'only-on-failure',
    /* Record video on first retry */
    video: 'on-first-retry',
    /* Global timeout per action */
    actionTimeout: 15_000,
    /* Navigation timeout */
    navigationTimeout: 30_000,
  },

  /* CV upload can take up to 3 minutes on production */
  timeout: 3 * 60 * 1_000,

  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        /* Viewport big enough to see all dashboard cards */
        viewport: { width: 1440, height: 900 },
      },
    },
  ],
});
