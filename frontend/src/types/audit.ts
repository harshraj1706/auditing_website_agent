/**
 * TypeScript types for the Brand AI-Readiness Audit Engine.
 * Aligned strictly with assets/report.schema.json and the Phase 1 REST API contracts.
 */

export type SeverityLevel = 'critical' | 'high' | 'medium' | 'low';

export type JobStatus = 'queued' | 'running' | 'completed' | 'failed';

export interface SuggestedAction {
  summary: string;
  priority: string;
  how?: string;
}

export interface Finding {
  id: string;
  title: string;
  severity: SeverityLevel;
  evidence: string;
  category?: 'discoverability' | 'engagement' | string;
  failure_mode?: string;
  confidence?: number;
  confidence_note?: string;
  affected_urls?: string[];
  suggested_action: SuggestedAction;
  verification_steps?: string[] | string;
  signals?: Record<string, unknown>;
  self_check_failed?: boolean;
}

export interface AuditSummary {
  total_findings: number;
  critical: number;
  high: number;
  medium: number;
  low?: number;
}

export interface AuditLimitations {
  crawl_incomplete?: string;
  robots_blocked?: string[];
  fetch_errors?: Array<{ url: string; status: number; error?: string }>;
  [key: string]: unknown;
}

export interface AuditReport {
  site: string;
  audited_at: string;
  site_type?: string;
  site_scale?: Record<string, unknown>;
  summary: AuditSummary;
  findings: Finding[];
  limitations?: AuditLimitations;
  proactive_recommendations?: unknown[];
  [key: string]: unknown;
}

export interface AuditRequestPayload {
  url: string;
}

export interface AuditAcceptedResponse {
  audit_id: string;
  status: 'queued' | string;
  url: string;
  created_at: string;
  message: string;
}

export interface AuditStatusResponse {
  audit_id: string;
  status: JobStatus;
  url: string;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  error?: string | null;
}

export interface HealthResponse {
  status: string;
  engine_ready: boolean;
  version: string;
  details?: Record<string, boolean | string>;
}

export interface AuditHistoryItem {
  audit_id: string;
  url: string;
  created_at: string;
  status: JobStatus;
  total_findings?: number;
  critical?: number;
}
