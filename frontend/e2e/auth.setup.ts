import { writeFileSync } from 'fs';
import { resolve } from 'path';
import { randomUUID } from 'crypto';

const STORAGE_STATE_PATH = resolve(__dirname, 'storageState.json');
const FRONTEND_ORIGIN = process.env.E2E_BASE_URL || 'http://localhost:3000';
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type AuthResponse = {
  access_token: string;
  token_type: string;
  user: {
    id: number;
    email: string;
    full_name: string;
    role: string;
    created_at: string;
  };
};

async function registerOrLoginTestUser(): Promise<AuthResponse> {
  const email = process.env.E2E_AUTH_EMAIL || `e2e-${randomUUID()}@example.com`;
  const password = process.env.E2E_AUTH_PASSWORD || 'Password123!';
  const fullName = process.env.E2E_AUTH_FULL_NAME || 'E2E Recruiter';

  const registerResponse = await fetch(`${API_BASE_URL}/api/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, full_name: fullName, role: 'recruiter' }),
  });

  if (registerResponse.ok) {
    return (await registerResponse.json()) as AuthResponse;
  }

  const loginResponse = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  if (!loginResponse.ok) {
    const registerBody = await registerResponse.text().catch(() => '');
    const loginBody = await loginResponse.text().catch(() => '');
    throw new Error(
      `Unable to create test auth state. Register status ${registerResponse.status}: ${registerBody}. Login status ${loginResponse.status}: ${loginBody}`
    );
  }

  return (await loginResponse.json()) as AuthResponse;
}

export default async function globalSetup() {
  const auth = await registerOrLoginTestUser();
  const storageState = {
    cookies: [],
    origins: [
      {
        origin: FRONTEND_ORIGIN,
        localStorage: [
          { name: 'access_token', value: auth.access_token },
          { name: 'user_role', value: auth.user.role },
          { name: 'user_name', value: auth.user.full_name },
          { name: 'user_id', value: String(auth.user.id) },
          { name: 'user', value: JSON.stringify(auth.user) },
        ],
      },
    ],
  };

  writeFileSync(STORAGE_STATE_PATH, JSON.stringify(storageState, null, 2));
  // Keep the setup quiet during normal runs; the file is the signal.
}