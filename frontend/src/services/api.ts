/**
 * API client service connecting the React frontend to the FastAPI backend.
 */

import type {
  AuditAcceptedResponse,
  AuditReport,
  AuditStatusResponse,
  HealthResponse,
} from '../types/audit';

// Allow base URL override from environment; default to empty string to use Vite's dev proxy
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(detail: string, status: number) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  let response: Response;
  try {
    response = await fetch(url, { ...options, headers });
  } catch (err) {
    throw new ApiError(
      'Unable to connect to the audit API. Please verify the backend server is running.',
      0
    );
  }

  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`;
    try {
      const errorJson = await response.json();
      if (errorJson.detail) {
        errorDetail = errorJson.detail;
      }
    } catch {
      // Non-JSON response
    }
    throw new ApiError(errorDetail, response.status);
  }

  return response.json() as Promise<T>;
}

export const api = {
  /** Check engine health and readiness */
  async checkHealth(): Promise<HealthResponse> {
    return request<HealthResponse>('/api/health');
  },

  /** Submit a website URL for asynchronous audit */
  async submitAudit(targetUrl: string): Promise<AuditAcceptedResponse> {
    return request<AuditAcceptedResponse>('/api/audits', {
      method: 'POST',
      body: JSON.stringify({ url: targetUrl }),
    });
  },

  /** Retrieve the real-time status of an audit job */
  async getAuditStatus(auditId: string): Promise<AuditStatusResponse> {
    return request<AuditStatusResponse>(`/api/audits/${encodeURIComponent(auditId)}`);
  },

  /** Retrieve the completed JSON report */
  async getAuditReport(auditId: string): Promise<AuditReport> {
    return request<AuditReport>(`/api/audits/${encodeURIComponent(auditId)}/report`);
  },
};
