import { test, expect } from '@playwright/test';

const BASE_URL = process.env.E2E_BASE_URL || 'http://127.0.0.1:3000';
const API_URL = process.env.E2E_API_URL || 'http://127.0.0.1:8010';

test.describe('Stable UI smoke tests', () => {
  test('homepage renders the main hero and auth links', async ({ page }) => {
    await page.goto(BASE_URL);
    await expect(page.locator('a[href="/auth/login"]')).toBeVisible();
    await expect(page.locator('a[href="/auth/register"]')).toBeVisible();
    await expect(page.getByText(/Le recrutement intelligent/i).first()).toBeVisible();
  });

  test('register page renders the real form controls', async ({ page }) => {
    await page.goto(`${BASE_URL}/auth/register`);
    await expect(page.getByRole('heading', { name: /creer un compte/i })).toBeVisible();
    await expect(page.getByRole('radio', { name: /candidat/i })).toBeVisible();
    await expect(page.getByRole('radio', { name: /recruteur/i })).toBeVisible();
    await expect(page.getByLabel(/nom complet/i)).toBeVisible();
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.getByLabel(/mot de passe/i)).toBeVisible();
  });

  test('login page renders the real form controls', async ({ page }) => {
    await page.goto(`${BASE_URL}/auth/login`);
    await expect(page.getByRole('heading', { name: /se connecter/i })).toBeVisible();
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.getByLabel(/mot de passe/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /se connecter/i })).toBeVisible();
  });

  test('public auth routes load without 404', async ({ page }) => {
    await page.goto(`${BASE_URL}/auth/login`);
    expect(page.url()).toContain('/auth/login');
    await page.goto(`${BASE_URL}/auth/register`);
    expect(page.url()).toContain('/auth/register');
  });
});

test.describe('API smoke tests', () => {
  test('backend health endpoint responds', async ({ request }) => {
    const resp = await request.get(`${API_URL}/health`, { timeout: 15_000 }).catch(() => null);

    if (!resp || !resp.ok()) {
      const fallback = await request.get(`${API_URL}/api/auth/me`);
      expect([200, 401, 403, 422]).toContain(fallback.status());
    } else {
      expect(resp.status()).toBe(200);
    }
  });

  test('auth register rejects malformed request', async ({ request }) => {
    const resp = await request.post(`${API_URL}/api/auth/register`, {
      data: { email: 'not-an-email', password: '123' },
    });
    expect([400, 422]).toContain(resp.status());
  });

  test('candidates list requires authentication', async ({ request }) => {
    const resp = await request.get(`${API_URL}/api/candidates/`);
    expect([401, 403]).toContain(resp.status());
  });

  test('matching generate-and-match requires authentication', async ({ request }) => {
    const resp = await request.post(`${API_URL}/api/matching/generate-and-match`, {
      data: { job_title: 'Developer', description: 'Python dev' },
    });
    expect([401, 403]).toContain(resp.status());
  });
});
