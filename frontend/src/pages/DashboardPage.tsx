import React, { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Sidebar } from '../components/Sidebar';
import { FindingCard } from '../components/FindingCard';
import { StatusBadge } from '../components/StatusBadge';
import { api, ApiError } from '../services/api';
import { sessionStore } from '../services/sessionStore';
import { EXAMPLE_AUDIT_REPORT } from '../services/exampleData';
import type { AuditReport, AuditStatusResponse } from '../types/audit';
import {
  Download,
  PlusCircle,
  ExternalLink,
  Search,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Calendar,
} from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const { auditId } = useParams<{ auditId?: string }>();

  const [statusData, setStatusData] = useState<AuditStatusResponse | null>(null);
  const [report, setReport] = useState<AuditReport | null>(null);
  const [, setLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Filters & Search
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSeverity, setSelectedSeverity] = useState<string>('all');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Determine active audit ID
  const effectiveAuditId = auditId || sessionStore.getAudits()[0]?.audit_id;

  useEffect(() => {
    if (!effectiveAuditId) {
      // No active audit and no session history; show example demo report as reference
      setReport(EXAMPLE_AUDIT_REPORT);
      setStatusData({
        audit_id: 'demo-stripe-audit',
        status: 'completed',
        url: 'https://stripe.com',
        created_at: EXAMPLE_AUDIT_REPORT.audited_at,
        completed_at: EXAMPLE_AUDIT_REPORT.audited_at,
      });
      setLoading(false);
      return;
    }

    let isMounted = true;

    const fetchStatusAndReport = async () => {
      try {
        const currentStatus = await api.getAuditStatus(effectiveAuditId);
        if (!isMounted) return;
        setStatusData(currentStatus);

        // Update session store
        sessionStore.updateAudit(effectiveAuditId, { status: currentStatus.status });

        if (currentStatus.status === 'completed') {
          // Job complete; fetch real report
          const fullReport = await api.getAuditReport(effectiveAuditId);
          if (!isMounted) return;
          setReport(fullReport);
          setLoading(false);

          // Update session item with findings count
          sessionStore.updateAudit(effectiveAuditId, {
            total_findings: fullReport.summary.total_findings,
            critical: fullReport.summary.critical,
          });
        } else if (currentStatus.status === 'failed') {
          if (!isMounted) return;
          setErrorMsg(currentStatus.error || 'The audit encountered a fatal error during crawl.');
          setLoading(false);
        } else {
          // Still queued or running; continue polling
          setLoading(false);
          pollTimerRef.current = setTimeout(fetchStatusAndReport, 2000);
        }
      } catch (err) {
        if (!isMounted) return;
        if (err instanceof ApiError) {
          setErrorMsg(err.detail);
        } else {
          setErrorMsg('Failed to communicate with audit server.');
        }
        setLoading(false);
      }
    };

    setLoading(true);
    setErrorMsg(null);
    fetchStatusAndReport();

    return () => {
      isMounted = false;
      if (pollTimerRef.current) {
        clearTimeout(pollTimerRef.current);
      }
    };
  }, [effectiveAuditId]);

  // Export JSON Report
  const handleDownloadJson = () => {
    if (!report) return;
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit-report-${report.site || 'website'}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Filter findings
  const findings = report?.findings || [];
  const filteredFindings = findings.filter((f) => {
    const matchesSearch =
      f.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      f.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      f.evidence.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (f.affected_urls && f.affected_urls.some((u) => u.toLowerCase().includes(searchQuery.toLowerCase())));

    const matchesSeverity =
      selectedSeverity === 'all' || f.severity.toLowerCase() === selectedSeverity.toLowerCase();

    const matchesCategory =
      selectedCategory === 'all' || (f.category && f.category.toLowerCase() === selectedCategory.toLowerCase());

    return matchesSearch && matchesSeverity && matchesCategory;
  });

  // Extract unique categories
  const categories = Array.from(new Set(findings.map((f) => f.category).filter(Boolean)));

  const isDemo = effectiveAuditId === 'demo-stripe-audit' || (!auditId && !sessionStore.getAudits()[0]?.audit_id);

  return (
    <div className="min-h-screen flex flex-col md:flex-row bg-[#0B0F17] text-slate-100">
      <Sidebar />

      <main className="flex-1 p-6 md:p-10 max-w-6xl mx-auto space-y-8">
        {/* Demo banner if showing example */}
        {isDemo && (
          <div className="p-4 rounded-xl bg-cyan-950/40 border border-cyan-800/60 text-xs text-cyan-300 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="font-mono font-bold px-2 py-0.5 rounded bg-cyan-900/60 text-cyan-200">
                DEMO PREVIEW
              </span>
              <span>Showing example audit for stripe.com. Submit a live URL to inspect any real site.</span>
            </div>
            <Link
              to="/audit/new"
              className="px-3 py-1.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold self-start sm:self-auto transition-colors"
            >
              Start Real Audit
            </Link>
          </div>
        )}

        {/* Audit Status & Running Progress Indicator */}
        {statusData && statusData.status !== 'completed' && statusData.status !== 'failed' && (
          <div className="p-8 rounded-2xl bg-[#111827] border border-cyan-900/50 shadow-2xl space-y-6 text-center max-w-2xl mx-auto">
            <div className="w-14 h-14 rounded-full bg-cyan-950/80 border border-cyan-700/60 flex items-center justify-center mx-auto shadow-[0_0_25px_rgba(6,182,212,0.3)]">
              <Loader2 className="w-7 h-7 text-cyan-400 animate-spin" />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-center gap-2">
                <StatusBadge status={statusData.status} />
              </div>
              <h2 className="text-xl font-bold text-slate-100">
                Auditing {statusData.url}
              </h2>
              <p className="text-sm text-slate-400 max-w-md mx-auto">
                Crawling public entrypoints, probing robots.txt for AI bots, analyzing Schema.org JSON-LD, and checking digital consensus...
              </p>
            </div>

            <div className="p-3.5 rounded-xl bg-[#0B0F17] border border-slate-800 text-xs font-mono text-slate-400 flex items-center justify-between">
              <span>Job ID: {statusData.audit_id.slice(0, 16)}...</span>
              <span className="text-cyan-400">Bounded crawl ≤12 pages</span>
            </div>
          </div>
        )}

        {/* Failed State Display */}
        {statusData && statusData.status === 'failed' && (
          <div className="p-8 rounded-2xl bg-rose-950/30 border border-rose-800/60 space-y-4 max-w-2xl mx-auto">
            <div className="flex items-center gap-3 text-rose-300">
              <AlertTriangle className="w-6 h-6 text-rose-400 flex-shrink-0" />
              <h2 className="text-lg font-bold">Audit Execution Failed</h2>
            </div>
            <p className="text-sm text-slate-300 font-mono bg-[#0B0F17] p-4 rounded-xl border border-rose-900/40">
              {statusData.error || errorMsg || 'Target website was unreachable or crawl timed out.'}
            </p>
            <div className="flex items-center justify-end gap-3 pt-2">
              <Link
                to="/audit/new"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-slate-100 font-semibold text-xs transition-colors"
              >
                Try Another URL
              </Link>
            </div>
          </div>
        )}

        {/* Completed Report Display */}
        {report && (
          <div className="space-y-8">
            {/* Report Header Bar */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 rounded-2xl bg-[#111827] border border-slate-800 shadow-xl">
              <div className="space-y-1.5">
                <div className="flex flex-wrap items-center gap-2.5">
                  <h1 className="text-2xl md:text-3xl font-extrabold text-slate-100 font-mono tracking-tight">
                    {report.site}
                  </h1>
                  {statusData && <StatusBadge status={statusData.status} size="sm" />}
                  {report.site_type && (
                    <span className="font-mono text-xs px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700 uppercase">
                      Type: {report.site_type}
                    </span>
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 font-mono">
                  {(statusData?.url || report.site) && (
                    <a
                      href={statusData?.url || (report.site.startsWith('http') ? report.site : `https://${report.site}`)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="hover:text-cyan-400 flex items-center gap-1"
                    >
                      {statusData?.url || (report.site.startsWith('http') ? report.site : `https://${report.site}`)} <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5 text-slate-500" />
                    Audited: {new Date(report.audited_at).toLocaleString()}
                  </span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={handleDownloadJson}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors shadow-sm"
                >
                  <Download className="w-4 h-4 text-cyan-400" />
                  Download JSON
                </button>
                <Link
                  to="/audit/new"
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-teal-400 hover:from-cyan-400 hover:to-teal-300 text-slate-950 font-bold text-xs shadow-[0_0_15px_rgba(6,182,212,0.3)] transition-all hover:scale-105"
                >
                  <PlusCircle className="w-4 h-4" />
                  New Audit
                </Link>
              </div>
            </div>

            {/* Summary Metrics Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
              <button
                type="button"
                onClick={() => setSelectedSeverity('all')}
                className={`p-5 rounded-xl text-left transition-all ${
                  selectedSeverity === 'all'
                    ? 'bg-[#111827] border-2 border-cyan-500 shadow-[0_0_15px_rgba(6,182,212,0.15)]'
                    : 'bg-[#111827] border border-slate-800 hover:border-slate-700'
                } space-y-1`}
              >
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Total Findings
                </span>
                <div className="text-3xl font-extrabold text-slate-100 font-mono">
                  {report.summary.total_findings ?? report.findings.length}
                </div>
                <span className="text-[11px] text-slate-500">Across 5 dimensions</span>
              </button>

              <button
                type="button"
                onClick={() => setSelectedSeverity('critical')}
                className={`p-5 rounded-xl text-left transition-all ${
                  selectedSeverity === 'critical'
                    ? 'bg-rose-950/30 border-2 border-rose-500 shadow-[0_0_15px_rgba(244,63,94,0.2)]'
                    : 'bg-rose-950/20 border border-rose-900/40 hover:border-rose-800'
                } space-y-1`}
              >
                <span className="text-xs font-semibold uppercase tracking-wider text-rose-400">
                  Critical
                </span>
                <div className="text-3xl font-extrabold text-rose-400 font-mono">
                  {report.summary.critical ?? 0}
                </div>
                <span className="text-[11px] text-rose-300/60">Severe blockers</span>
              </button>

              <button
                type="button"
                onClick={() => setSelectedSeverity('high')}
                className={`p-5 rounded-xl text-left transition-all ${
                  selectedSeverity === 'high'
                    ? 'bg-amber-950/30 border-2 border-amber-500 shadow-[0_0_15px_rgba(245,158,11,0.2)]'
                    : 'bg-amber-950/20 border border-amber-900/40 hover:border-amber-800'
                } space-y-1`}
              >
                <span className="text-xs font-semibold uppercase tracking-wider text-amber-400">
                  High Severity
                </span>
                <div className="text-3xl font-extrabold text-amber-400 font-mono">
                  {report.summary.high ?? 0}
                </div>
                <span className="text-[11px] text-amber-300/60">Citability gaps</span>
              </button>

              <button
                type="button"
                onClick={() => setSelectedSeverity('medium')}
                className={`p-5 rounded-xl text-left transition-all ${
                  selectedSeverity === 'medium'
                    ? 'bg-yellow-950/30 border-2 border-yellow-500 shadow-[0_0_15px_rgba(234,179,8,0.2)]'
                    : 'bg-yellow-950/20 border border-yellow-900/40 hover:border-yellow-800'
                } space-y-1`}
              >
                <span className="text-xs font-semibold uppercase tracking-wider text-yellow-300">
                  Medium
                </span>
                <div className="text-3xl font-extrabold text-yellow-300 font-mono">
                  {report.summary.medium ?? 0}
                </div>
                <span className="text-[11px] text-yellow-200/60">Landability issues</span>
              </button>

              <button
                type="button"
                onClick={() => setSelectedSeverity('low')}
                className={`p-5 rounded-xl text-left transition-all ${
                  selectedSeverity === 'low'
                    ? 'bg-cyan-950/30 border-2 border-cyan-500 shadow-[0_0_15px_rgba(6,182,212,0.2)]'
                    : 'bg-cyan-950/20 border border-cyan-900/40 hover:border-cyan-800'
                } space-y-1 col-span-2 sm:col-span-1`}
              >
                <span className="text-xs font-semibold uppercase tracking-wider text-cyan-400">
                  Low
                </span>
                <div className="text-3xl font-extrabold text-cyan-300 font-mono">
                  {report.summary.low ?? 0}
                </div>
                <span className="text-[11px] text-cyan-200/60">Proactive hygiene</span>
              </button>
            </div>

            {/* Search and Filters Bar */}
            <div className="space-y-4">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-xl bg-[#111827] border border-slate-800">
                {/* Search Bar */}
                <div className="relative flex-1">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search findings by rule ID, title, evidence, or URL..."
                    className="w-full bg-[#0B0F17] border border-slate-700/80 rounded-lg pl-10 pr-4 py-2 text-slate-100 text-xs font-mono placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                  />
                </div>

                {/* Severity Filter Pills */}
                <div className="flex flex-wrap items-center gap-1.5">
                  {['all', 'critical', 'high', 'medium', 'low'].map((sev) => (
                    <button
                      key={sev}
                      type="button"
                      onClick={() => setSelectedSeverity(sev)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-mono uppercase tracking-wider transition-colors ${
                        selectedSeverity === sev
                          ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold'
                          : 'bg-[#0B0F17] text-slate-400 hover:text-slate-200 border border-slate-800'
                      }`}
                    >
                      {sev}
                    </button>
                  ))}
                </div>
              </div>

              {/* Category Pills (if multiple categories present) */}
              {categories.length > 1 && (
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <span className="text-slate-500 font-mono">Category:</span>
                  <button
                    type="button"
                    onClick={() => setSelectedCategory('all')}
                    className={`px-2.5 py-1 rounded text-xs font-mono transition-colors ${
                      selectedCategory === 'all'
                        ? 'bg-slate-700 text-slate-100 font-semibold'
                        : 'bg-slate-900 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    All Categories
                  </button>
                  {categories.map((cat) => (
                    <button
                      key={cat}
                      type="button"
                      onClick={() => setSelectedCategory(cat as string)}
                      className={`px-2.5 py-1 rounded text-xs font-mono transition-colors ${
                        selectedCategory === cat
                          ? 'bg-cyan-950 text-cyan-300 border border-cyan-800 font-semibold'
                          : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
                      }`}
                    >
                      {cat}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Findings List */}
            <div className="space-y-4">
              <div className="flex items-center justify-between text-xs font-mono text-slate-400 px-1">
                <span>
                  Showing {filteredFindings.length} of {findings.length} findings
                </span>
                {findings.length > 0 && (
                  <span className="text-slate-500">
                    Ranked by severity funnel: Index &gt; Cite &gt; Land
                  </span>
                )}
              </div>

              {filteredFindings.length === 0 ? (
                <div className="p-12 text-center rounded-2xl bg-[#111827] border border-slate-800 space-y-3">
                  <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto" />
                  <h3 className="text-base font-bold text-slate-200">
                    No Findings Match Your Filter
                  </h3>
                  <p className="text-xs text-slate-400 max-w-sm mx-auto">
                    Try adjusting your search query or severity filter to inspect other audit dimensions.
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {filteredFindings.map((finding) => (
                    <FindingCard key={finding.id} finding={finding} defaultExpanded={finding.severity === 'critical'} />
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
};
