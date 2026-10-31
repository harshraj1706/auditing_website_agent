import React from 'react';
import type { CitabilityScoreResult } from '../services/scoreCalculator';
import {
  ShieldCheck,
  Search,
  FileCheck,
  MousePointerClick,
  AlertOctagon,
  AlertTriangle,
  Info,
} from 'lucide-react';

interface ScoreGaugeProps {
  scoreData: CitabilityScoreResult;
  siteName?: string;
}

export const ScoreGauge: React.FC<ScoreGaugeProps> = ({ scoreData, siteName }) => {
  const { overallScore, grade, statusLabel, colorHex, badgeBg, pillars, summary } = scoreData;

  // Circular gauge calculations
  const radius = 54;
  const strokeWidth = 8;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (overallScore / 100) * circumference;

  const getPillarIcon = (name: string) => {
    if (name.includes('Crawl')) return <Search className="w-3.5 h-3.5 text-cyan-400" />;
    if (name.includes('Schema')) return <FileCheck className="w-3.5 h-3.5 text-emerald-400" />;
    return <MousePointerClick className="w-3.5 h-3.5 text-amber-400" />;
  };

  const getPillarBarColor = (score: number) => {
    if (score >= 75) return 'bg-emerald-500';
    if (score >= 50) return 'bg-cyan-500';
    if (score >= 30) return 'bg-amber-500';
    return 'bg-rose-500';
  };

  return (
    <div className="rounded-2xl bg-[#111827] border border-slate-800 p-6 shadow-xl relative overflow-hidden">
      {/* Subtle background glow */}
      <div
        className="absolute -right-20 -top-20 w-72 h-72 rounded-full opacity-10 blur-3xl pointer-events-none"
        style={{ backgroundColor: colorHex }}
      />

      <div className="flex flex-col lg:flex-row items-center gap-8">
        {/* Left: Circular Radial Gauge */}
        <div className="flex flex-col items-center flex-shrink-0">
          <div className="relative w-40 h-40 flex items-center justify-center">
            <svg className="w-full h-full -rotate-90 transform" viewBox="0 0 130 130">
              {/* Background circle */}
              <circle
                cx="65"
                cy="65"
                r={radius}
                className="stroke-slate-800"
                strokeWidth={strokeWidth}
                fill="transparent"
              />
              {/* Animated foreground score circle */}
              <circle
                cx="65"
                cy="65"
                r={radius}
                stroke={colorHex}
                strokeWidth={strokeWidth}
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                fill="transparent"
                className="transition-all duration-1000 ease-out"
              />
            </svg>

            {/* Inner Score Readout */}
            <div className="absolute flex flex-col items-center justify-center text-center">
              <span className="text-3xl font-extrabold tracking-tight text-white font-mono">
                {overallScore}
              </span>
              <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
                Score / 100
              </span>
              <span
                className="mt-1 px-2 py-0.5 rounded text-xs font-bold font-mono border"
                style={{
                  color: colorHex,
                  borderColor: `${colorHex}55`,
                  backgroundColor: `${colorHex}15`,
                }}
              >
                Grade {grade}
              </span>
            </div>
          </div>

          <div className="mt-2 text-center">
            <span className="text-xs font-semibold text-slate-300">
              {siteName || 'Domain'} AI Readiness
            </span>
          </div>
        </div>

        {/* Right: Pillars & Readiness Breakdown */}
        <div className="flex-1 w-full space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
            <div>
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-cyan-400" />
                <h3 className="text-base font-bold text-slate-100">
                  AI Citability & Indexing Readiness
                </h3>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Evaluation across autonomous search engines, assistant quotation, and landing usability.
              </p>
            </div>

            <div
              className={`self-start sm:self-auto px-3 py-1 rounded-full border text-xs font-semibold font-mono tracking-wide ${badgeBg}`}
            >
              {statusLabel}
            </div>
          </div>

          {/* 3 Pillars Breakdown */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {Object.values(pillars).map((pillar) => (
              <div
                key={pillar.name}
                className="p-3.5 rounded-xl bg-[#0B0F17] border border-slate-800/80 space-y-2 hover:border-slate-700 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    {getPillarIcon(pillar.name)}
                    <span className="text-xs font-semibold text-slate-200 truncate">
                      {pillar.name}
                    </span>
                  </div>
                  <span className="text-xs font-mono font-bold text-slate-100">
                    {pillar.score}%
                  </span>
                </div>

                {/* Progress bar */}
                <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
                  <div
                    className={`h-full rounded-full ${getPillarBarColor(pillar.score)} transition-all duration-700`}
                    style={{ width: `${pillar.score}%` }}
                  />
                </div>

                <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
                  <span>Weight: {pillar.weight}%</span>
                  <span
                    className={
                      pillar.issuesCount > 0 ? 'text-amber-400/90' : 'text-emerald-400/90'
                    }
                  >
                    {pillar.issuesCount} {pillar.issuesCount === 1 ? 'issue' : 'issues'}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Quick Stats Strip */}
          <div className="flex flex-wrap items-center gap-2 pt-1 text-xs font-mono">
            <span className="text-slate-400 mr-1">Finding Breakdown:</span>
            {summary.criticalCount > 0 && (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded bg-rose-950/60 border border-rose-800/50 text-rose-300">
                <AlertOctagon className="w-3 h-3 text-rose-400" />
                {summary.criticalCount} Critical
              </span>
            )}
            {summary.highCount > 0 && (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded bg-amber-950/60 border border-amber-800/50 text-amber-300">
                <AlertTriangle className="w-3 h-3 text-amber-400" />
                {summary.highCount} High
              </span>
            )}
            {summary.mediumCount > 0 && (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded bg-yellow-950/60 border border-yellow-800/50 text-yellow-300">
                <Info className="w-3 h-3 text-yellow-400" />
                {summary.mediumCount} Medium
              </span>
            )}
            {summary.lowCount > 0 && (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300">
                {summary.lowCount} Low
              </span>
            )}
            {summary.totalFindings === 0 && (
              <span className="text-emerald-400 font-semibold">
                ✓ 0 issues detected across all 6 skill categories
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
