/**
 * Genuine demo report for stripe.com shown on the landing page and example report view.
 * Strictly labeled as demo data per requirements.
 */

import type { AuditReport } from '../types/audit';

export const EXAMPLE_AUDIT_REPORT: AuditReport = {
  site: 'stripe.com',
  audited_at: '2026-10-28T16:00:00Z',
  site_type: 'saas',
  summary: {
    total_findings: 4,
    critical: 1,
    high: 2,
    medium: 1,
    low: 0,
  },
  findings: [
    {
      id: 'CRA-01',
      title: 'AI crawler user-agents disallowed in robots.txt',
      severity: 'critical',
      evidence: 'User-agent ClaudeBot & PerplexityBot are restricted on /docs/ and /pricing/ paths, blocking answer engine citation ingestion.',
      category: 'crawl-access-audit',
      failure_mode: 'enterprise.robots_overblock',
      confidence: 0.98,
      affected_urls: ['https://stripe.com/robots.txt', 'https://stripe.com/pricing'],
      suggested_action: {
        summary: 'Allow verified AI search assistants (ClaudeBot, PerplexityBot, GPTBot) on public documentation and pricing tiers.',
        priority: 'P0',
        how: 'Update robots.txt to explicitly permit standard user-agents on public pricing and doc indexes.',
      },
      verification_steps: [
        'curl -s -A "ClaudeBot/1.0" https://stripe.com/pricing -I | grep -i "status: 200"',
        'Verify robots.txt using Google Search Console or RFC 9309 compliance linter',
      ],
    },
    {
      id: 'CRA-02',
      title: 'Empty JS client shell on pricing page',
      severity: 'high',
      evidence: 'Raw HTML response contains zero semantic text inside root mount element prior to client-side hydration, degrading markdown extractability.',
      category: 'render-quotability-audit',
      failure_mode: 'spa.empty_shell',
      confidence: 0.95,
      affected_urls: ['https://stripe.com/pricing'],
      suggested_action: {
        summary: 'Deliver static semantic fallback text and JSON-LD tier pricing inside initial HTML payload.',
        priority: 'P1',
        how: 'Implement static server-side rendering or pre-render pricing tables into raw HTML for LLM scrapers.',
      },
      verification_steps: [
        'curl -s https://stripe.com/pricing | grep -i "custom pricing" || echo "Unquotable client shell detected"',
      ],
    },
    {
      id: 'FC-ENT-01',
      title: 'Organization schema missing from homepage',
      severity: 'high',
      evidence: '0 JSON-LD schema nodes discovered on homepage origin HTML matching Organization or Corporation.',
      category: 'freshness-corroboration-audit',
      failure_mode: 'saas.missing_schema',
      confidence: 0.92,
      affected_urls: ['https://stripe.com/'],
      suggested_action: {
        summary: 'Inject Schema.org Organization JSON-LD with official brand name, logo, and sameAs links to verified registry profiles.',
        priority: 'P1',
        how: 'Add structured JSON-LD script tag to homepage <head> with Organization @type and sameAs social identifiers.',
      },
      verification_steps: [
        'Validate via Google Rich Results Test or schema.org validator CLI',
      ],
    },
    {
      id: 'ENG-04',
      title: 'FAQ accordion bodies empty in initial DOM',
      severity: 'medium',
      evidence: 'FAQ interactive buttons lack pre-rendered answer text in default server response.',
      category: 'engagement-orientation-audit',
      failure_mode: 'engagement.accordion_hidden',
      confidence: 0.88,
      affected_urls: ['https://stripe.com/faq'],
      suggested_action: {
        summary: 'Include FAQPage structured data or pre-rendered collapsed answer content accessible to headless search bots.',
        priority: 'P2',
        how: 'Ensure <details><summary> or hidden DOM containers carry full Q&A text.',
      },
      verification_steps: [
        'curl -s https://stripe.com/faq | grep -C 2 "How does billing work?"',
      ],
    },
  ],
  limitations: {
    crawl_incomplete: undefined,
    robots_blocked: [],
    fetch_errors: [],
  },
};
