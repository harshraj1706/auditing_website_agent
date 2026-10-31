/**
 * AI Citability & Readiness Score Calculator.
 *
 * Computes a mathematically grounded, 0-100 composite index from audit findings,
 * partitioned into 3 core pillars:
 * 1. Crawl & Indexability (35%)
 * 2. Schema & Fact Citability (40%)
 * 3. Visitor Actionability (25%)
 */

import type { AuditReport, Finding } from '../types/audit';

export interface PillarScore {
  name: string;
  weight: number;
  score: number; // 0 - 100
  status: 'optimal' | 'moderate' | 'critical';
  issuesCount: number;
  description: string;
}

export interface CitabilityScoreResult {
  overallScore: number; // 0 - 100
  grade: 'A+' | 'A' | 'B' | 'C' | 'D' | 'F';
  statusLabel: string;
  colorHex: string;
  badgeBg: string;
  badgeText: string;
  pillars: {
    crawl: PillarScore;
    citability: PillarScore;
    actionability: PillarScore;
  };
  summary: {
    criticalCount: number;
    highCount: number;
    mediumCount: number;
    lowCount: number;
    totalFindings: number;
  };
}

export function calculateCitabilityScore(report: AuditReport): CitabilityScoreResult {
  const findings: Finding[] = report.findings || [];

  // Deductions by severity:
  // Critical: -25 pts
  // High: -14 pts
  // Medium: -6 pts
  // Low: -2 pts

  let crawlDeduction = 0;
  let crawlIssues = 0;

  let citabilityDeduction = 0;
  let citabilityIssues = 0;

  let actionabilityDeduction = 0;
  let actionabilityIssues = 0;

  let criticalCount = 0;
  let highCount = 0;
  let mediumCount = 0;
  let lowCount = 0;

  findings.forEach((f) => {
    const sev = (f.severity || 'low').toLowerCase();
    const id = (f.id || '').toUpperCase();

    if (sev === 'critical') criticalCount++;
    else if (sev === 'high') highCount++;
    else if (sev === 'medium') mediumCount++;
    else lowCount++;

    const penalty =
      sev === 'critical' ? 28 : sev === 'high' ? 14 : sev === 'medium' ? 6 : 2;

    // Categorize into pillars
    if (
      id.startsWith('CRA-01') ||
      id.startsWith('CRA-02') ||
      id.startsWith('CRA-03') ||
      id.startsWith('CRA-05') ||
      id.startsWith('CRA-06') ||
      id.startsWith('CRA-07') ||
      id.startsWith('NET-')
    ) {
      crawlDeduction += penalty;
      crawlIssues++;
    } else if (
      id.startsWith('FC-') ||
      id.startsWith('CRA-04-PDF')
    ) {
      citabilityDeduction += penalty;
      citabilityIssues++;
    } else {
      // ENG-*, CRA-04 (images), etc.
      actionabilityDeduction += penalty;
      actionabilityIssues++;
    }
  });

  // Check if network failed or site unreachable
  if (report.limitations?.crawl_incomplete === 'origin_unreachable') {
    crawlDeduction = Math.max(crawlDeduction, 90);
  }

  const crawlScore = Math.max(0, Math.min(100, Math.round(100 - crawlDeduction)));
  const citabilityScore = Math.max(0, Math.min(100, Math.round(100 - citabilityDeduction)));
  const actionabilityScore = Math.max(0, Math.min(100, Math.round(100 - actionabilityDeduction)));

  // Weighted overall composite:
  // Crawl: 35%, Citability: 40%, Actionability: 25%
  const weighted =
    crawlScore * 0.35 + citabilityScore * 0.40 + actionabilityScore * 0.25;
  const overallScore = Math.max(0, Math.min(100, Math.round(weighted)));

  // Assign grade and status
  let grade: CitabilityScoreResult['grade'] = 'A+';
  let statusLabel = 'High AI Readiness';
  let colorHex = '#10B981'; // emerald-500
  let badgeBg = 'bg-emerald-950/70 border-emerald-800/60 text-emerald-300';
  let badgeText = 'Optimal AI Ingestion';

  if (overallScore >= 92) {
    grade = 'A+';
    statusLabel = 'Exceptional AI Readiness';
    colorHex = '#10B981';
    badgeBg = 'bg-emerald-950/70 border-emerald-800/60 text-emerald-300';
    badgeText = 'Prime AI Ingestion & Quotability';
  } else if (overallScore >= 80) {
    grade = 'A';
    statusLabel = 'Strong AI Readiness';
    colorHex = '#06B6D4'; // cyan-500
    badgeBg = 'bg-cyan-950/70 border-cyan-800/60 text-cyan-300';
    badgeText = 'Fully Crawlable & Discoverable';
  } else if (overallScore >= 68) {
    grade = 'B';
    statusLabel = 'Moderate AI Friction';
    colorHex = '#38BDF8'; // sky-400
    badgeBg = 'bg-sky-950/70 border-sky-800/60 text-sky-300';
    badgeText = 'Minor Citation Friction';
  } else if (overallScore >= 50) {
    grade = 'C';
    statusLabel = 'Significant AI Citability Barriers';
    colorHex = '#F59E0B'; // amber-500
    badgeBg = 'bg-amber-950/70 border-amber-800/60 text-amber-300';
    badgeText = 'Requires Immediate Schema / Crawl Fixes';
  } else if (overallScore >= 35) {
    grade = 'D';
    statusLabel = 'Severe AI Indexing Risk';
    colorHex = '#F97316'; // orange-500
    badgeBg = 'bg-orange-950/70 border-orange-800/60 text-orange-300';
    badgeText = 'High Ingestion Blockers';
  } else {
    grade = 'F';
    statusLabel = 'Critical AI Ingestion Failure';
    colorHex = '#F43F5E'; // rose-500
    badgeBg = 'bg-rose-950/70 border-rose-800/60 text-rose-300';
    badgeText = 'Blocked or Unquotable by AI Agents';
  }

  const getPillarStatus = (score: number): PillarScore['status'] =>
    score >= 75 ? 'optimal' : score >= 45 ? 'moderate' : 'critical';

  return {
    overallScore,
    grade,
    statusLabel,
    colorHex,
    badgeBg,
    badgeText,
    pillars: {
      crawl: {
        name: 'Crawl & Indexability',
        weight: 35,
        score: crawlScore,
        status: getPillarStatus(crawlScore),
        issuesCount: crawlIssues,
        description:
          'Evaluates robots.txt permissions, sitemap validity, WAF rate-limiting, and raw HTML renderability.',
      },
      citability: {
        name: 'Schema & Fact Citability',
        weight: 40,
        score: citabilityScore,
        status: getPillarStatus(citabilityScore),
        issuesCount: citabilityIssues,
        description:
          'Measures Schema.org Organization, sameAs triangulation, dateModified timestamps, and llms.txt discovery.',
      },
      actionability: {
        name: 'Visitor Actionability',
        weight: 25,
        score: actionabilityScore,
        status: getPillarStatus(actionabilityScore),
        issuesCount: actionabilityIssues,
        description:
          'Assesses functional CTAs, semantic H1/breadcrumbs hierarchy, and complete FAQ answer bodies.',
      },
    },
    summary: {
      criticalCount,
      highCount,
      mediumCount,
      lowCount,
      totalFindings: findings.length,
    },
  };
}
