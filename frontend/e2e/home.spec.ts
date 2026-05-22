import { test, expect } from '@playwright/test';

const BASE_URL = process.env.E2E_BASE_URL || 'http://127.0.0.1:3000';

test.describe('Homepage', () => {
  test('renders hero and navigates FAQ + contact', async ({ page }) => {
    await page.goto(BASE_URL);
    await expect(page.getByText('Trouve les meilleurs')).toBeVisible();

    // Open FAQ first item
    const faqBtn = page.getByRole('button', { name: /Comment fonctionne le matching par IA\?/i });
    await faqBtn.click();
    await expect(page.getByText(/pipeline NER \+ embeddings sémantiques/i)).toBeVisible();

    // Fill contact form
    await page.locator('input[name="name"]').fill('Test User');
    await page.locator('input[name="email"]').fill('test@example.com');
    await page.locator('textarea[name="message"]').fill('Hello from Playwright');
    await page.locator('button:has-text("Envoyer")').click();

    // Success message (could be optimistic, allow either response)
    await expect(page.locator('text=Merci — message envoyé.')).toBeVisible({ timeout: 3000 });
  });
});
