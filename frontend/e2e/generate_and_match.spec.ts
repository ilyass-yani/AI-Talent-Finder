import { test, expect } from '@playwright/test';

// Reuse previously generated authenticated storage state
test.use({ storageState: './storageState.json' });

test('Mode-2 generate-and-match returns candidate matches (production)', async ({ request }) => {
  const resp = await request.post('https://ai-talent-finder-production-ed09.up.railway.app/api/matching/generate-and-match', {
    data: {
      job_title: 'Auto: Data Scientist',
      description: 'Looking for Python, ML, Docker'
    }
  });

  expect(resp.ok()).toBeTruthy();
  const body = await resp.json();
  expect(body).toHaveProperty('ideal_profile');
  expect(Array.isArray(body.matches)).toBeTruthy();
  expect(body.matches.length).toBeGreaterThan(0);
});
