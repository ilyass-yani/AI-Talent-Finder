/**
 * Tests for the admin service module.
 * Follows the same describe/test/mock pattern as services.test.ts.
 */

import { adminApi, ModerationStatus } from '@/services/admin';
import apiClient from '@/services/api';

jest.mock('@/services/api', () => ({
  __esModule: true,
  default: {
    get: jest.fn(),
    patch: jest.fn(),
    delete: jest.fn(),
  },
}));

const mockedApi = apiClient as jest.Mocked<typeof apiClient>;

const mockUser = {
  id: 1,
  email: 'alice@example.com',
  full_name: 'Alice',
  role: 'recruiter',
  is_active: true,
  created_at: '2026-01-01T00:00:00',
};

const mockJob = {
  id: 10,
  title: 'Senior Dev',
  description: 'Great job',
  moderation_status: 'pending' as ModerationStatus,
  recruiter_id: 2,
  recruiter_email: 'bob@example.com',
  created_at: '2026-01-02T00:00:00',
};

const mockStats = {
  total_candidates: 42,
  total_recruiters: 8,
  total_active_jobs: 5,
  total_matchings: 120,
};

// ---------------------------------------------------------------------------
// getUsers
// ---------------------------------------------------------------------------

describe('adminApi.getUsers', () => {
  test('calls GET /admin/users with no params', async () => {
    mockedApi.get.mockResolvedValueOnce({ data: { total: 1, items: [mockUser] } });
    const res = await adminApi.getUsers();
    expect(mockedApi.get).toHaveBeenCalledWith('/admin/users', { params: undefined });
    expect(res.data.total).toBe(1);
    expect(res.data.items[0].email).toBe('alice@example.com');
  });

  test('passes role filter as query param', async () => {
    mockedApi.get.mockResolvedValueOnce({ data: { total: 0, items: [] } });
    await adminApi.getUsers({ role: 'candidate', skip: 0, limit: 10 });
    expect(mockedApi.get).toHaveBeenCalledWith('/admin/users', {
      params: { role: 'candidate', skip: 0, limit: 10 },
    });
  });

  test('propagates API errors', async () => {
    mockedApi.get.mockRejectedValueOnce({ response: { data: { detail: 'Admin access required' } } });
    await expect(adminApi.getUsers()).rejects.toMatchObject({
      response: { data: { detail: 'Admin access required' } },
    });
  });
});

// ---------------------------------------------------------------------------
// setUserStatus
// ---------------------------------------------------------------------------

describe('adminApi.setUserStatus', () => {
  test('calls PATCH /admin/users/:id/status with is_active=false', async () => {
    mockedApi.patch.mockResolvedValueOnce({ data: { ...mockUser, is_active: false } });
    const res = await adminApi.setUserStatus(1, false);
    expect(mockedApi.patch).toHaveBeenCalledWith('/admin/users/1/status', { is_active: false });
    expect(res.data.is_active).toBe(false);
  });

  test('calls PATCH with is_active=true to re-enable', async () => {
    mockedApi.patch.mockResolvedValueOnce({ data: { ...mockUser, is_active: true } });
    await adminApi.setUserStatus(1, true);
    expect(mockedApi.patch).toHaveBeenCalledWith('/admin/users/1/status', { is_active: true });
  });
});

// ---------------------------------------------------------------------------
// deleteUser
// ---------------------------------------------------------------------------

describe('adminApi.deleteUser', () => {
  test('calls DELETE /admin/users/:id', async () => {
    mockedApi.delete.mockResolvedValueOnce({ data: null });
    await adminApi.deleteUser(1);
    expect(mockedApi.delete).toHaveBeenCalledWith('/admin/users/1');
  });
});

// ---------------------------------------------------------------------------
// getJobs
// ---------------------------------------------------------------------------

describe('adminApi.getJobs', () => {
  test('calls GET /admin/jobs with no params', async () => {
    mockedApi.get.mockResolvedValueOnce({ data: { total: 1, items: [mockJob] } });
    const res = await adminApi.getJobs();
    expect(mockedApi.get).toHaveBeenCalledWith('/admin/jobs', { params: undefined });
    expect(res.data.items[0].title).toBe('Senior Dev');
  });

  test('passes moderation_status filter', async () => {
    mockedApi.get.mockResolvedValueOnce({ data: { total: 0, items: [] } });
    await adminApi.getJobs({ moderation_status: 'pending' });
    expect(mockedApi.get).toHaveBeenCalledWith('/admin/jobs', {
      params: { moderation_status: 'pending' },
    });
  });
});

// ---------------------------------------------------------------------------
// moderateJob
// ---------------------------------------------------------------------------

describe('adminApi.moderateJob', () => {
  test('sends approved status', async () => {
    mockedApi.patch.mockResolvedValueOnce({ data: { ...mockJob, moderation_status: 'approved' } });
    const res = await adminApi.moderateJob(10, 'approved');
    expect(mockedApi.patch).toHaveBeenCalledWith('/admin/jobs/10/moderate', {
      moderation_status: 'approved',
    });
    expect(res.data.moderation_status).toBe('approved');
  });

  test('sends rejected status', async () => {
    mockedApi.patch.mockResolvedValueOnce({ data: { ...mockJob, moderation_status: 'rejected' } });
    await adminApi.moderateJob(10, 'rejected');
    expect(mockedApi.patch).toHaveBeenCalledWith('/admin/jobs/10/moderate', {
      moderation_status: 'rejected',
    });
  });
});

// ---------------------------------------------------------------------------
// deleteJob
// ---------------------------------------------------------------------------

describe('adminApi.deleteJob', () => {
  test('calls DELETE /admin/jobs/:id', async () => {
    mockedApi.delete.mockResolvedValueOnce({ data: null });
    await adminApi.deleteJob(10);
    expect(mockedApi.delete).toHaveBeenCalledWith('/admin/jobs/10');
  });
});

// ---------------------------------------------------------------------------
// getStats
// ---------------------------------------------------------------------------

describe('adminApi.getStats', () => {
  test('returns all stat fields', async () => {
    mockedApi.get.mockResolvedValueOnce({ data: mockStats });
    const res = await adminApi.getStats();
    expect(mockedApi.get).toHaveBeenCalledWith('/admin/stats');
    expect(res.data.total_candidates).toBe(42);
    expect(res.data.total_recruiters).toBe(8);
    expect(res.data.total_active_jobs).toBe(5);
    expect(res.data.total_matchings).toBe(120);
  });

  test('propagates 403 when called by non-admin', async () => {
    mockedApi.get.mockRejectedValueOnce({ response: { status: 403, data: { detail: 'Admin access required' } } });
    await expect(adminApi.getStats()).rejects.toMatchObject({
      response: { status: 403 },
    });
  });
});
