import React, { useState, useEffect } from 'react';
import { Sidebar } from '../components/Sidebar';
import { FindingCard } from '../components/FindingCard';
import { ScoreGauge } from '../components/ScoreGauge';
import { calculateCitabilityScore } from '../services/scoreCalculator';
import { api } from '../services/api';
import { sessionStore } from '../services/sessionStore';
import { EXAMPLE_AUDIT_REPORT } from '../services/exampleData';
import type { AuditReport } from '../types/audit';
import {
  Layers,
  Search,
  CheckCircle2,
} from 'lucide-react';

export const FindingsExplorerPage: React.FC = () => {
  const [report, setReport] = useState<AuditReport>(EXAMPLE_AUDIT_REPORT);
  const [search, setSearch] = useState('');
  const [selectedSeverity, setSelectedSeverity] = useState('all');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [isLiveAudit, setIsLiveAudit] = useState(false);

  useEffect(() => {
    // Check if there is a completed live audit in session store
    const recent = sessionStore.getAudits().find((a) => a.status === 'completed');
    if (recent) {
      api
        .getAuditReport(recent.audit_id)
        .then((liveReport) => {
          setReport(liveReport);
          setIsLiveAudit(true);
        })
        .catch(() => {
          // Fallback to example report
        });
    }
  }, []);

  const findings = report.findings || [];

  const filteredFindings = findings.filter((f) => {
    const matchesSearch =
      f.title.toLowerCase().includes(search.toLowerCase()) ||
      f.id.toLowerCase().includes(search.toLowerCase()) ||
      f.evidence.toLowerCase().includes(search.toLowerCase());

    const matchesSeverity =
      selectedSeverity === 'all' || f.severity.toLowerCase() === selectedSeverity.toLowerCase();

    const matchesCategory =
      selectedCategory === 'all' || (f.category && f.category.toLowerCase() === selectedCategory.toLowerCase());

    return matchesSearch && matchesSeverity && matchesCategory;
  });

  const categories = Array.from(new Set(findings.map((f) => f.category).filter(Boolean)));
  const scoreResult = calculateCitabilityScore(report);

  return (
    <div className="min-h-screen flex flex-col md:flex-row bg-[#0B0F17] text-slate-100">
      <Sidebar />

      <main className="flex-1 p-6 md:p-10 max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div className="space-y-2 border-b border-slate-800 pb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-mono text-cyan-400">
              <Layers className="w-4 h-4" />
              DETAILED FINDINGS EXPLORER
            </div>
            <span className="text-xs font-mono text-slate-400">
              Source:{' '}
              <strong className="text-cyan-300">
                {report.site} {isLiveAudit ? '(Live Audit)' : '(Example Demo)'}
              </strong>
            </span>
          </div>

          <h1 className="text-3xl font-extrabold text-slate-100 tracking-tight">
            Audit Findings & Remediation Guide
          </h1>
          <p className="text-sm text-slate-400 max-w-2xl">
            Deep technical inspection of verified citability barriers. Every finding includes
            grounded evidence, priority actions, and reproducible verification commands.
          </p>
        </div>

        {/* AI Citability Score & Pillar Gauges */}
        <ScoreGauge scoreData={scoreResult} siteName={report.site} />

        {/* Summary Metrics Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          <button
            type="button"
            onClick={() => setSelectedSeverity('all')}
            className={`p-4 rounded-xl text-left transition-all ${
              selectedSeverity === 'all'
                ? 'bg-[#111827] border-2 border-cyan-500 shadow-[0_0_15px_rgba(6,182,212,0.15)]'
                : 'bg-[#111827] border border-slate-800 hover:border-slate-700'
            } space-y-1`}
          >
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              Total Findings
            </span>
            <div className="text-2xl font-extrabold text-slate-100 font-mono">
              {report.summary?.total_findings ?? findings.length}
            </div>
            <span className="text-[10px] text-slate-500">Across 5 dimensions</span>
          </button>

          <button
            type="button"
            onClick={() => setSelectedSeverity('critical')}
            className={`p-4 rounded-xl text-left transition-all ${
              selectedSeverity === 'critical'
                ? 'bg-rose-950/30 border-2 border-rose-500 shadow-[0_0_15px_rgba(244,63,94,0.2)]'
                : 'bg-rose-950/20 border border-rose-900/40 hover:border-rose-800'
            } space-y-1`}
          >
            <span className="text-[11px] font-semibold uppercase tracking-wider text-rose-400">
              Critical
            </span>
            <div className="text-2xl font-extrabold text-rose-400 font-mono">
              {report.summary?.critical ?? 0}
            </div>
            <span className="text-[10px] text-rose-300/60">Severe blockers</span>
          </button>

          <button
            type="button"
            onClick={() => setSelectedSeverity('high')}
            className={`p-4 rounded-xl text-left transition-all ${
              selectedSeverity === 'high'
                ? 'bg-amber-950/30 border-2 border-amber-500 shadow-[0_0_15px_rgba(245,158,11,0.2)]'
                : 'bg-amber-950/20 border border-amber-900/40 hover:border-amber-800'
            } space-y-1`}
          >
            <span className="text-[11px] font-semibold uppercase tracking-wider text-amber-400">
              High Severity
            </span>
            <div className="text-2xl font-extrabold text-amber-400 font-mono">
              {report.summary?.high ?? 0}
            </div>
            <span className="text-[10px] text-amber-300/60">Citability gaps</span>
          </button>

          <button
            type="button"
            onClick={() => setSelectedSeverity('medium')}
            className={`p-4 rounded-xl text-left transition-all ${
              selectedSeverity === 'medium'
                ? 'bg-yellow-950/30 border-2 border-yellow-500 shadow-[0_0_15px_rgba(234,179,8,0.2)]'
                : 'bg-yellow-950/20 border border-yellow-900/40 hover:border-yellow-800'
            } space-y-1`}
          >
            <span className="text-[11px] font-semibold uppercase tracking-wider text-yellow-300">
              Medium
            </span>
            <div className="text-2xl font-extrabold text-yellow-300 font-mono">
              {report.summary?.medium ?? 0}
            </div>
            <span className="text-[10px] text-yellow-200/60">Landability issues</span>
          </button>

          <button
            type="button"
            onClick={() => setSelectedSeverity('low')}
            className={`p-4 rounded-xl text-left transition-all ${
              selectedSeverity === 'low'
                ? 'bg-cyan-950/30 border-2 border-cyan-500 shadow-[0_0_15px_rgba(6,182,212,0.2)]'
                : 'bg-cyan-950/20 border border-cyan-900/40 hover:border-cyan-800'
            } space-y-1 col-span-2 sm:col-span-1`}
          >
            <span className="text-[11px] font-semibold uppercase tracking-wider text-cyan-400">
              Low
            </span>
            <div className="text-2xl font-extrabold text-cyan-300 font-mono">
              {report.summary?.low ?? 0}
            </div>
            <span className="text-[10px] text-cyan-200/60">Proactive hygiene</span>
          </button>
        </div>

        {/* Search & Filters */}
        <div className="space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-xl bg-[#111827] border border-slate-800">
            {/* Search Input */}
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search rule ID, title, or evidence..."
                className="w-full bg-[#0B0F17] border border-slate-700/80 rounded-lg pl-10 pr-4 py-2 text-slate-100 text-xs font-mono placeholder-slate-500 focus:outline-none focus:border-cyan-500"
              />
            </div>

            {/* Severity Filters */}
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

          {/* Categories */}
          {categories.length > 0 && (
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
                All
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
          </div>

          {filteredFindings.length === 0 ? (
            <div className="p-12 text-center rounded-2xl bg-[#111827] border border-slate-800 space-y-3">
              <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto" />
              <h3 className="text-base font-bold text-slate-200">No Findings Found</h3>
              <p className="text-xs text-slate-400 max-w-sm mx-auto">
                No findings match the current filter criteria.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredFindings.map((finding) => (
                <FindingCard
                  key={finding.id}
                  finding={finding}
                  defaultExpanded={true}
                  siteContext={{
                    site: report.site,
                    siteType: report.site_type,
                  }}
                />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
};
