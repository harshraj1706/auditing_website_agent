/**
 * Multi-Format Audit Report Exporter.
 * Supports Markdown (.md) generation, formatted JSON export, and printable PDF triggering.
 */

import type { AuditReport, Finding } from '../types/audit';
import { calculateCitabilityScore, type CitabilityScoreResult } from './scoreCalculator';

/**
 * Generate a complete, executive-grade Markdown document from an AuditReport.
 */
export function generateMarkdownReport(
  report: AuditReport,
  scoreData?: CitabilityScoreResult
): string {
  const score = scoreData || calculateCitabilityScore(report);
  const site = report.site || 'Target Website';
  const auditedAt = new Date(report.audited_at).toUTCString();
  const findings = report.findings || [];

  // Group findings by severity
  const critical = findings.filter((f) => (f.severity || '').toLowerCase() === 'critical');
  const high = findings.filter((f) => (f.severity || '').toLowerCase() === 'high');
  const medium = findings.filter((f) => (f.severity || '').toLowerCase() === 'medium');
  const low = findings.filter((f) => (f.severity || '').toLowerCase() === 'low');

  const formatFindingSection = (finding: Finding) => {
    const urls =
      finding.affected_urls && finding.affected_urls.length > 0
        ? finding.affected_urls.map((u) => `  - \`${u}\``).join('\n')
        : '  - Homepage / Global Site Context';

    const verificationSteps = Array.isArray(finding.verification_steps)
      ? finding.verification_steps.map((v) => `\`\`\`bash\n${v}\n\`\`\``).join('\n')
      : finding.verification_steps
      ? `\`\`\`bash\n${finding.verification_steps}\n\`\`\``
      : '_No dedicated verification command provided._';

    return `### [${(finding.severity || 'LOW').toUpperCase()}] ${finding.id}: ${finding.title}

- **Category:** ${finding.category || 'Discoverability'}
- **Priority:** ${finding.suggested_action?.priority || finding.severity}
${finding.confidence ? `- **Confidence:** ${Math.round(finding.confidence * 100)}%\n` : ''}
#### Evidence Detected
> ${finding.evidence}

#### Affected URLs
${urls}

#### Recommended Remediation
**${finding.suggested_action?.summary || 'Review and remediate issue.'}**

${finding.suggested_action?.how ? `_${finding.suggested_action.how}_\n` : ''}
#### Verification & Validation Step
${verificationSteps}

---
`;
  };

  const md = `# Brand AI-Readiness Audit Report: ${site}

> Autonomous Brand AI-Readiness Audit evaluating indexing, fact citability, and visitor actionability for AI assistants (Gemini, ChatGPT, Perplexity, Claude, Siri).

- **Audited Target:** \`${site}\`
- **Audit Timestamp:** ${auditedAt}
- **Detected Architecture:** \`${report.site_type || 'Unknown'}\`
- **Overall AI Citability Score:** **${score.overallScore} / 100** (Grade **${score.grade}**) — *${score.statusLabel}*

---

## 1. Executive Scorecard & Pillar Breakdown

| Audit Pillar | Score | Weight | Status | Issues Detected |
|---|---|---|---|---|
| **Crawl & Indexability** | **${score.pillars.crawl.score}%** | 35% | \`${score.pillars.crawl.status.toUpperCase()}\` | ${score.pillars.crawl.issuesCount} |
| **Schema & Fact Citability** | **${score.pillars.citability.score}%** | 40% | \`${score.pillars.citability.status.toUpperCase()}\` | ${score.pillars.citability.issuesCount} |
| **Visitor Actionability** | **${score.pillars.actionability.score}%** | 25% | \`${score.pillars.actionability.status.toUpperCase()}\` | ${score.pillars.actionability.issuesCount} |

### Finding Counts by Severity
- **Critical (Index Blockers):** ${score.summary.criticalCount}
- **High (Citability Gaps):** ${score.summary.highCount}
- **Medium (Landability / Hygiene):** ${score.summary.mediumCount}
- **Low (Proactive Guidance):** ${score.summary.lowCount}
- **Total Issues Identified:** **${score.summary.totalFindings}**

---

## 2. Priority Action Plan & Detailed Findings

${
  findings.length === 0
    ? `### ✓ No Barriers Detected\n\nThe audited website satisfies all standard crawl accessibility, schema disambiguation, and engagement requirements with 0 findings.`
    : ''
}
${critical.length > 0 ? `## Critical Severity (Index Blockers)\n\n${critical.map(formatFindingSection).join('\n')}\n` : ''}
${high.length > 0 ? `## High Severity (Citability Gaps)\n\n${high.map(formatFindingSection).join('\n')}\n` : ''}
${medium.length > 0 ? `## Medium Severity (Landability & Freshness)\n\n${medium.map(formatFindingSection).join('\n')}\n` : ''}
${low.length > 0 ? `## Low Severity (Proactive Guidance)\n\n${low.map(formatFindingSection).join('\n')}\n` : ''}

${
  report.limitations && Object.keys(report.limitations).length > 0
    ? `## 3. Crawl Limitations & Safeguards\n\n\`\`\`json\n${JSON.stringify(report.limitations, null, 2)}\n\`\`\`\n\n---\n`
    : ''
}
## 4. Methodology & Engineering Standards

- **Standard Compliance:** Adheres to the [Agent Skills Standard](https://agentskills.io) with modular, provider-neutral skills.
- **Crawler Safeguards:** Operates strictly in read-only mode, respecting RFC 9309 robots wildcard inheritance, with zero paid APIs and zero on-site modifications.
- **Verification Grounding:** Every finding contains exact curl verification commands to confirm fixes independently.
`;

  return md;
}

/**
 * Triggers a browser download of a text/blob payload.
 */
export function downloadFile(content: string, filename: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Export Markdown format (.md).
 */
export function exportMarkdownReport(report: AuditReport): void {
  const md = generateMarkdownReport(report);
  const safeName = (report.site || 'website').replace(/[^a-zA-Z0-9.-]/g, '_');
  downloadFile(md, `${safeName}-ai-readiness-audit.md`, 'text/markdown;charset=utf-8');
}

/**
 * Export formatted JSON matching report.schema.json.
 */
export function exportJsonReport(report: AuditReport): void {
  const json = JSON.stringify(report, null, 2);
  const safeName = (report.site || 'website').replace(/[^a-zA-Z0-9.-]/g, '_');
  downloadFile(json, `${safeName}-audit-report.json`, 'application/json;charset=utf-8');
}

/**
 * Trigger browser print dialog for Save as PDF.
 */
export function printReport(): void {
  window.print();
}
