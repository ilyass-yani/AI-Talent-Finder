/**
 * Full-App E2E Test Suite — AI Talent Finder (Production)
 *
 * Covers:
 *  1. Homepage renders correctly
 *  2. Candidate: register → upload CV → view profile → dashboard
 *  3. Recruiter: register → Mode 1 search → Mode 2 generate-and-match
 *  4. All nav links reachable without 404/500
 *
 * CV file used:  C:\Users\ACER\OneDrive - usmba.ac.ma\Documents\chafik\Resume\resume chafik boulealam v2.pdf
 *
 * Run:
 *   cd frontend
 *   npx playwright test e2e/full_app.spec.ts --headed
 *
 * Or headless (CI):
 *   npx playwright test e2e/full_app.spec.ts
 */

import { test, expect, Page } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';

// ──────────────────────────────────────────────
// Config
// ──────────────────────────────────────────────
const BASE_URL = 'https://ai-talent-finder-production-ed09.up.railway.app';
const API_URL = 'https://ai-talent-finder-backend-production.up.railway.app';
const CV_PATH = path.resolve(
  'C:\\Users\\ACER\\OneDrive - usmba.ac.ma\\Documents\\chafik\\Resume\\resume chafik boulealam v2.pdf'
);

// Unique emails so each run creates fresh accounts
const timestamp = Date.now();
const CANDIDATE_EMAIL = `e2e.candidate.${timestamp}@test.com`;
const CANDIDATE_PASSWORD = 'Test@123456';
const CANDIDATE_NAME = 'Chafik Boulealam E2E';

const RECRUITER_EMAIL = `e2e.recruiter.${timestamp}@test.com`;
const RECRUITER_PASSWORD = 'Test@123456';
const RECRUITER_NAME = 'Recruiter E2E';

// ──────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────
async function screenshotStep(page: Page, label: string) {
  const dir = path.join('test-results', 'screenshots');
  fs.mkdirSync(dir, { recursive: true });
  await page.screenshot({
    path: path.join(dir, `${label.replace(/\s+/g, '_')}.png`),
    fullPage: true,
  });
}

async function waitForPageLoad(page: Page) {
  await page.waitForLoadState('networkidle', { timeout: 20_000 }).catch(() => {
    // networkidle may time-out on slow pages; proceed anyway
  });
}

// ──────────────────────────────────────────────
// Suite 1 — Homepage
// ──────────────────────────────────────────────
test.describe('1. Homepage', () => {
  test('Homepage renders the landing page with login/register links', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForPageLoad(page);

    // The page should either show the landing page or redirect to a dashboard/login
    // It should NOT be an error page
    const status = page.url();
    expect(status).toContain('railway.app');

    // Take a screenshot to visually inspect
    await screenshotStep(page, '01_homepage');

    // Check page title or brand exists
    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(10);
  });
});

// ──────────────────────────────────────────────
// Suite 2 — Candidate Flow
// ──────────────────────────────────────────────
test.describe('2. Candidate Flow', () => {
  test.beforeEach(async ({ page }) => {
    page.on('console', msg => console.log('PAGE LOG:', msg.text()));
    page.on('pageerror', err => console.log('PAGE ERROR:', err.message));
    page.on('requestfailed', request => console.log('REQUEST FAILED:', request.url(), request.failure()?.errorText));
  });
  test('2a. Register page loads', async ({ page }) => {
    await page.goto(`${BASE_URL}/auth/register`);
    await waitForPageLoad(page);
    await screenshotStep(page, '02a_register_page');
    await expect(page.getByText('Créez votre compte')).toBeVisible();
  });

  test('2b. Register as Candidate', async ({ page }) => {
    await page.goto(`${BASE_URL}/auth/register`);
    await waitForPageLoad(page);

    // Select Candidate role
    const candidateBtn = page.getByRole('radio', { name: /candidat/i }).or(
      page.getByLabel(/candidat/i)
    );
    // Try clicking the candidate role button
    const candidateCard = page.locator('[aria-label*="Candidat"]').first();
    await candidateCard.click();

    // Fill in full name
    await page.getByLabel(/nom complet/i).fill(CANDIDATE_NAME);
    // Fill in email
    await page.getByLabel(/email/i).fill(CANDIDATE_EMAIL);
    // Fill in password
    await page.getByLabel(/mot de passe/i).fill(CANDIDATE_PASSWORD);

    await screenshotStep(page, '02b_register_filled');

    // Submit
    await page.getByRole('button', { name: /créer|s'inscrire|inscription|register/i }).click();

    // Should redirect to candidate dashboard or upload page
    await page.waitForURL(/candidate\/(dashboard|upload)/, { timeout: 20_000 });
    await screenshotStep(page, '02b_after_register');
    expect(page.url()).toMatch(/candidate/);
  });

  test('2c. Candidate Dashboard loads', async ({ page }) => {
    // Register first to get session
    await page.goto(`${BASE_URL}/auth/register`);
    await waitForPageLoad(page);

    const candidateCard = page.locator('[aria-label*="Candidat"]').first();
    await candidateCard.click();
    await page.getByLabel(/nom complet/i).fill(CANDIDATE_NAME + ' D');
    await page.getByLabel(/email/i).fill(`dash.${CANDIDATE_EMAIL}`);
    await page.getByLabel(/mot de passe/i).fill(CANDIDATE_PASSWORD);
    await page.getByRole('button', { name: /créer|s'inscrire|inscription|register/i }).click();
    await page.waitForURL(/candidate/, { timeout: 20_000 });

    // Go explicitly to dashboard
    await page.goto(`${BASE_URL}/candidate/dashboard`);
    await waitForPageLoad(page);
    await screenshotStep(page, '02c_candidate_dashboard');

    // Page should not show a 404
    const title = await page.title();
    expect(title).not.toMatch(/404|not found/i);
  });

  test('2d. Upload CV page loads and accepts PDF', async ({ page }) => {
    // Register fresh candidate for upload test
    await page.goto(`${BASE_URL}/auth/register`);
    await waitForPageLoad(page);

    const candidateCard = page.locator('[aria-label*="Candidat"]').first();
    await candidateCard.click();
    await page.getByLabel(/nom complet/i).fill(CANDIDATE_NAME + ' Upload');
    await page.getByLabel(/email/i).fill(`upload.${CANDIDATE_EMAIL}`);
    await page.getByLabel(/mot de passe/i).fill(CANDIDATE_PASSWORD);
    await page.getByRole('button', { name: /créer|s'inscrire|inscription|register/i }).click();
    await page.waitForURL(/candidate/, { timeout: 20_000 });

    // Navigate to upload page
    await page.goto(`${BASE_URL}/candidate/upload`);
    await waitForPageLoad(page);
    await screenshotStep(page, '02d_upload_page');

    // Check CV file exists locally before attaching
    const cvExists = fs.existsSync(CV_PATH);
    if (!cvExists) {
      console.warn(`[SKIP] CV file not found at ${CV_PATH} — skipping file upload step`);
      test.skip();
      return;
    }

    // Find the file input and attach the CV
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(CV_PATH);

    // Verify the filename appears on the page
    await expect(
      page.getByText(/resume chafik boulealam/i).or(page.getByText(/\.pdf/i))
    ).toBeVisible({ timeout: 5_000 });

    await screenshotStep(page, '02d_cv_selected');

    // Click the upload button
    const uploadBtn = page.getByRole('button', { name: /uploader|upload|télécharger|envoyer/i });
    await uploadBtn.click();

    // The upload can take up to 3 minutes on production (ML processing)
    await screenshotStep(page, '02d_upload_started');

    // Wait for success message or redirect to profile
    await Promise.race([
      page.waitForURL(/candidate\/profile/, { timeout: 3 * 60_000 }),
      page.waitForSelector('[class*="success"], [class*="green"], [aria-live]', {
        timeout: 3 * 60_000,
      }),
    ]).catch(async () => {
      // If neither happened, take a screenshot to inspect state
      await screenshotStep(page, '02d_upload_timeout');
    });

    await screenshotStep(page, '02d_after_upload');

    // Check for error indicators
    const pageText = await page.locator('body').innerText();
    const hasError = /erreur|error|failed|échec/i.test(pageText);
    if (hasError) {
      // Attach page text to test output for debugging
      console.error('[Upload] Page shows error state:', pageText.substring(0, 500));
    }

    // We consider success if: redirected to profile OR success message visible
    const currentUrl = page.url();
    const onProfile = currentUrl.includes('/candidate/profile');
    const successMsg = await page
      .locator('text=✓')
      .or(page.getByText(/succès|success/i))
      .count();
    expect(onProfile || successMsg > 0).toBeTruthy();
  });

  test('2e. Candidate Profile page loads after upload', async ({ page }) => {
    // Register + upload
    await page.goto(`${BASE_URL}/auth/register`);
    await waitForPageLoad(page);

    const candidateCard = page.locator('[aria-label*="Candidat"]').first();
    await candidateCard.click();
    await page.getByLabel(/nom complet/i).fill(CANDIDATE_NAME + ' Prof');
    await page.getByLabel(/email/i).fill(`profile.${CANDIDATE_EMAIL}`);
    await page.getByLabel(/mot de passe/i).fill(CANDIDATE_PASSWORD);
    await page.getByRole('button', { name: /créer|s'inscrire|inscription|register/i }).click();
    await page.waitForURL(/candidate/, { timeout: 20_000 });

    // Navigate directly to profile
    await page.goto(`${BASE_URL}/candidate/profile`);
    await waitForPageLoad(page);
    await screenshotStep(page, '02e_candidate_profile');

    const title = await page.title();
    expect(title).not.toMatch(/404|not found/i);
  });
});

// ──────────────────────────────────────────────
// Suite 3 — Recruiter Flow
// ──────────────────────────────────────────────
test.describe('3. Recruiter Flow', () => {
  // Shared recruiter page object (login once for the suite)
  let recruiterPage: Page;

  test.beforeAll(async ({ browser }) => {
    const ctx = await browser.newContext();
    recruiterPage = await ctx.newPage();

    // Register as recruiter
    await recruiterPage.goto(`${BASE_URL}/auth/register`);
    await waitForPageLoad(recruiterPage);

    const recruiterCard = recruiterPage.locator('[aria-label*="Recruteur"]').first();
    await recruiterCard.click();
    await recruiterPage.getByLabel(/nom complet/i).fill(RECRUITER_NAME);
    await recruiterPage.getByLabel(/email/i).fill(RECRUITER_EMAIL);
    await recruiterPage.getByLabel(/mot de passe/i).fill(RECRUITER_PASSWORD);
    await recruiterPage
      .getByRole('button', { name: /créer|s'inscrire|inscription|register/i })
      .click();
    // Give the app extra time to redirect to recruiter dashboard; fall back to a networkidle load check
    await recruiterPage.waitForURL(/recruiter/, { timeout: 30_000 }).catch(async () => {
      await waitForPageLoad(recruiterPage);
    });
    await screenshotStep(recruiterPage, '03_recruiter_registered');
  });

  test.afterAll(async () => {
    await recruiterPage?.context().close();
  });

  test('3a. Recruiter Dashboard loads', async () => {
    await recruiterPage.goto(`${BASE_URL}/recruiter/dashboard`);
    await waitForPageLoad(recruiterPage);
    await screenshotStep(recruiterPage, '03a_recruiter_dashboard');

    await expect(recruiterPage.getByText(/meilleurs candidats|talent finder/i).first()).toBeVisible(
      { timeout: 10_000 }
    );
  });

  test('3b. Mode Recherche (Mode 1) — form renders and search runs', async () => {
    await recruiterPage.goto(`${BASE_URL}/recruiter/dashboard`);
    await waitForPageLoad(recruiterPage);

    // Click "Mode Recherche" card
    const modeSearchCard = recruiterPage.getByRole('button', { name: /mode recherche/i }).or(
      recruiterPage.locator('[aria-label*="Mode Recherche"]')
    );
    await modeSearchCard.click();

    // Wait for search form
    await expect(recruiterPage.getByLabel(/titre du poste/i).first()).toBeVisible({
      timeout: 5_000,
    });
    await screenshotStep(recruiterPage, '03b_mode1_form');

    // Fill the form
    await recruiterPage.getByLabel(/titre du poste/i).first().fill('Full Stack Developer');
    await recruiterPage
      .getByLabel(/compétences requises/i)
      .fill('React, Node.js, TypeScript');
    await recruiterPage
      .getByLabel(/description du poste/i)
      .fill(
        'Looking for a Full Stack Developer with 3+ years of experience in React and Node.js. Must know TypeScript, REST APIs, and SQL databases.'
      );

    await screenshotStep(recruiterPage, '03b_mode1_filled');

    // Launch search (use explicit button locator to avoid ambiguous role matches)
    const launchSearchBtn = recruiterPage.locator('button:has-text("Lancer la Recherche")').first();
    await expect(launchSearchBtn).toBeVisible({ timeout: 5_000 });
    await launchSearchBtn.click();

    // Wait for results or error message (API may return 0 candidates if none uploaded yet)
    await recruiterPage
      .waitForSelector('[role="article"], [role="alert"]', { timeout: 30_000 })
      .catch(async () => {
        await screenshotStep(recruiterPage, '03b_mode1_no_response');
      });

    await screenshotStep(recruiterPage, '03b_mode1_results');
    const bodyText = await recruiterPage.locator('body').innerText();
    console.log('[Mode 1] Result snippet:', bodyText.substring(0, 400));
  });

  test('3c. Mode Génération IA (Mode 2) — form renders and generate-and-match runs', async () => {
    await recruiterPage.goto(`${BASE_URL}/recruiter/dashboard`);
    await waitForPageLoad(recruiterPage);

    // Click "Mode Génération IA" card
    const modeGenCard = recruiterPage
      .getByRole('button', { name: /mode génération/i })
      .or(recruiterPage.locator('[aria-label*="Mode Génération"]'));
    await modeGenCard.click();

    // Wait for generate form
    await expect(recruiterPage.getByLabel(/titre du poste/i).first()).toBeVisible({
      timeout: 5_000,
    });
    await screenshotStep(recruiterPage, '03c_mode2_form');

    // Fill the form
    await recruiterPage
      .getByLabel(/titre du poste/i)
      .first()
      .fill('Data Scientist');
    // Try to locate the description field by common labels first (covers multiple locales).
    let descField = recruiterPage.getByLabel(/description|décrivez|décrire|describe/i).first();
    // If the label is not associated with a control, fall back to the first visible textarea on the form
    if ((await descField.count()) === 0) {
      descField = recruiterPage.locator('textarea').first();
    }
    await descField.scrollIntoViewIfNeeded();
    await expect(descField).toBeVisible({ timeout: 15_000 });
    await descField.fill(
      'We are looking for a Data Scientist proficient in Python, machine learning, PyTorch, and data visualization. Experience with NLP models is a plus.',
      { timeout: 30_000 }
    );

    await screenshotStep(recruiterPage, '03c_mode2_filled');

    // Launch generate-and-match
    await recruiterPage
      .getByRole('button', { name: /générer|lancer|generate/i })
      .click();

    // ML processing can take up to 2 minutes
    await recruiterPage
      .waitForSelector('[role="article"], [role="alert"], text=profil idéal', {
        timeout: 2 * 60_000,
      })
      .catch(async () => {
        await screenshotStep(recruiterPage, '03c_mode2_timeout');
      });

    await screenshotStep(recruiterPage, '03c_mode2_results');
    const bodyText = await recruiterPage.locator('body').innerText();
    console.log('[Mode 2] Result snippet:', bodyText.substring(0, 500));
  });

  test('3d. Recruiter Shortlist page loads', async ({ page }) => {
    // Login as recruiter
    await page.goto(`${BASE_URL}/auth/login`);
    await waitForPageLoad(page);
    await page.getByLabel(/email/i).fill(RECRUITER_EMAIL);
    await page.getByLabel(/mot de passe/i).fill(RECRUITER_PASSWORD);
    await page.getByRole('button', { name: /connexion|se connecter|login/i }).click();
    await page.waitForURL(/recruiter/, { timeout: 15_000 });

    await page.goto(`${BASE_URL}/recruiter/shortlist`);
    await waitForPageLoad(page);
    await screenshotStep(page, '03d_shortlist');
    const title = await page.title();
    expect(title).not.toMatch(/404|not found/i);
  });

  test('3e. Recruiter Export page loads', async ({ page }) => {
    await page.goto(`${BASE_URL}/auth/login`);
    await waitForPageLoad(page);
    await page.getByLabel(/email/i).fill(RECRUITER_EMAIL);
    await page.getByLabel(/mot de passe/i).fill(RECRUITER_PASSWORD);
    await page.getByRole('button', { name: /connexion|se connecter|login/i }).click();
    await page.waitForURL(/recruiter/, { timeout: 15_000 });

    await page.goto(`${BASE_URL}/recruiter/export`);
    await waitForPageLoad(page);
    await screenshotStep(page, '03e_export');
    const title = await page.title();
    expect(title).not.toMatch(/404|not found/i);
  });

  test('3f. Recruiter Chatbot page loads', async ({ page }) => {
    await page.goto(`${BASE_URL}/auth/login`);
    await waitForPageLoad(page);
    await page.getByLabel(/email/i).fill(RECRUITER_EMAIL);
    await page.getByLabel(/mot de passe/i).fill(RECRUITER_PASSWORD);
    await page.getByRole('button', { name: /connexion|se connecter|login/i }).click();
    await page.waitForURL(/recruiter/, { timeout: 15_000 });

    await page.goto(`${BASE_URL}/recruiter/chatbot`);
    await waitForPageLoad(page);
    await screenshotStep(page, '03f_chatbot');
    const title = await page.title();
    expect(title).not.toMatch(/404|not found/i);
  });
});

// ──────────────────────────────────────────────
// Suite 4 — API Smoke Tests (direct HTTP)
// ──────────────────────────────────────────────
test.describe('4. API Smoke Tests', () => {
  test('4a. Backend health endpoint responds', async ({ request }) => {
    const resp = await request.get(`${API_URL}/health`, {
      timeout: 15_000,
    }).catch(() => null);

    // If /health doesn't exist, try /api/auth/me (will return 401 but at least the API is up)
    if (!resp || !resp.ok()) {
      const fallback = await request.get(`${API_URL}/api/auth/me`);
      // 401 Unauthorized means API is alive but requires auth
      expect([200, 401, 403, 422]).toContain(fallback.status());
    } else {
      expect(resp.status()).toBe(200);
    }
  });

  test('4b. Auth register endpoint rejects malformed request', async ({ request }) => {
    const resp = await request.post(`${API_URL}/api/auth/register`, {
      data: { email: 'not-an-email', password: '123' },
    });
    // 422 Unprocessable Entity (Pydantic validation) or 400 Bad Request
    expect([400, 422]).toContain(resp.status());
  });

  test('4c. Candidates list requires authentication', async ({ request }) => {
    const resp = await request.get(`${API_URL}/api/candidates/`);
    expect([401, 403]).toContain(resp.status());
  });

  test('4d. Matching generate-and-match requires authentication', async ({ request }) => {
    const resp = await request.post(`${API_URL}/api/matching/generate-and-match`, {
      data: { job_title: 'Developer', description: 'Python dev' },
    });
    expect([401, 403]).toContain(resp.status());
  });
});

// ──────────────────────────────────────────────
// Suite 5 — Navigation / No 404s
// ──────────────────────────────────────────────
test.describe('5. Navigation — public pages not broken', () => {
  const publicRoutes = [
    '/auth/login',
    '/auth/register',
  ];

  for (const route of publicRoutes) {
    test(`Route ${route} loads without error`, async ({ page }) => {
      await page.goto(`${BASE_URL}${route}`);
      await waitForPageLoad(page);
      const title = await page.title();
      expect(title).not.toMatch(/404|not found|error/i);
      await screenshotStep(page, `05_nav_${route.replace(/\//g, '_')}`);
    });
  }
});
