/**
 * In-browser session audit history helper.
 * Strictly labeled as session-only local storage per requirements.
 */

import type { AuditHistoryItem } from '../types/audit';

const STORAGE_KEY = 'brand_ai_readiness_session_audits';

export const sessionStore = {
  getAudits(): AuditHistoryItem[] {
    try {
      const data = localStorage.getItem(STORAGE_KEY);
      if (!data) return [];
      return JSON.parse(data) as AuditHistoryItem[];
    } catch {
      return [];
    }
  },

  saveAudit(item: AuditHistoryItem): void {
    try {
      const list = this.getAudits();
      const existingIdx = list.findIndex((a) => a.audit_id === item.audit_id);
      if (existingIdx >= 0) {
        list[existingIdx] = { ...list[existingIdx], ...item };
      } else {
        list.unshift(item);
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(list.slice(0, 20)));
    } catch {
      // Storage unavailable or quota exceeded
    }
  },

  updateAudit(auditId: string, updates: Partial<AuditHistoryItem>): void {
    try {
      const list = this.getAudits();
      const idx = list.findIndex((a) => a.audit_id === auditId);
      if (idx >= 0) {
        list[idx] = { ...list[idx], ...updates };
        localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
      }
    } catch {
      // Ignore storage errors
    }
  },

  clear(): void {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      // Ignore
    }
  },
};
