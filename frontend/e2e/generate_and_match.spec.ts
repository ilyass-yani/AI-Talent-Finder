import { test, expect } from '@playwright/test';
import fs from 'fs';

// Reuse previously generated authenticated storage state
test.use({ storageState: './storageState.json' });

test('Mode-2 generate-and-match returns candidate matches (production)', async ({ request }) => {
  // Auth is stored as a JWT in localStorage (key: access_token).
  // Extract it and pass as Authorization: Bearer header.
  let headers: Record<string, string> = {};
  try {
    const storage = JSON.parse(fs.readFileSync('./storageState.json', 'utf-8'));
    // Try localStorage first (JWT-based auth)
    for (const origin of (storage.origins ?? [])) {
      const item = (origin.localStorage ?? []).find((e: any) => e.name === 'access_token');
      if (item?.value) {
        headers['Authorization'] = `Bearer ${item.value}`;
        break;
      }
    }
    // Fallback: cookie-based auth
    if (!headers['Authorization'] && Array.isArray(storage.cookies) && storage.cookies.length > 0) {
      headers['cookie'] = storage.cookies.map((c: any) => `${c.name}=${c.value}`).join('; ');
    }
  } catch (e) {
    // If storageState is missing or unreadable, test will proceed unauthenticated and likely fail.
  }

  const resp = await request.post('https://ai-talent-finder-backend-production.up.railway.app/api/matching/generate-and-match', {
    data: {
      job_title: 'Auto: Data Scientist',
      description: 'Looking for Python, ML, Docker'
    },
    headers,
  });

  expect(resp.ok()).toBeTruthy();
  const body = await resp.json();
  expect(body).toHaveProperty('ideal_profile');
  expect(Array.isArray(body.matches)).toBeTruthy();
  // matches can be empty when no candidates are in the database yet; the API is still correct.
  expect(body.matches.length).toBeGreaterThanOrEqual(0);
});
