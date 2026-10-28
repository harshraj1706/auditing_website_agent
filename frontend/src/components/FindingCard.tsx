import React, { useState } from 'react';
import type { Finding } from '../types/audit';
import { SeverityBadge } from './StatusBadge';
import {
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Terminal,
  Copy,
  Check,
  Lightbulb,
} from 'lucide-react';

interface FindingCardProps {
  finding: Finding;
  defaultExpanded?: boolean;
}

export const FindingCard: React.FC<FindingCardProps> = ({
  finding,
  defaultExpanded = false,
}) => {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [copiedStep, setCopiedStep] = useState<number | null>(null);

  const verificationSteps = Array.isArray(finding.verification_steps)
    ? finding.verification_steps
    : finding.verification_steps
    ? [finding.verification_steps]
    : [];

  const copyToClipboard = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedStep(index);
    setTimeout(() => setCopiedStep(null), 2000);
  };

  const getBorderColor = () => {
    switch (finding.severity.toLowerCase()) {
      case 'critical':
        return 'border-rose-900/40 hover:border-rose-700/60';
      case 'high':
        return 'border-amber-900/40 hover:border-amber-700/60';
      case 'medium':
        return 'border-yellow-900/30 hover:border-yellow-700/50';
      default:
        return 'border-slate-800 hover:border-slate-700';
    }
  };

  return (
    <div
      className={`rounded-xl bg-[#111827] border ${getBorderColor()} transition-all duration-200 overflow-hidden shadow-lg`}
    >
      {/* Header bar */}
      <div
        onClick={() => setExpanded(!expanded)}
        className="p-5 cursor-pointer hover:bg-slate-800/30 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-4"
      >
        <div className="space-y-2 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
              {finding.id}
            </span>
            <SeverityBadge severity={finding.severity} />
            {finding.category && (
              <span className="font-mono text-[11px] text-slate-400 bg-slate-900/80 px-2 py-0.5 rounded border border-slate-800">
                {finding.category}
              </span>
            )}
            {finding.confidence && (
              <span className="text-[11px] text-slate-500 font-mono ml-auto md:ml-0">
                {Math.round(finding.confidence * 100)}% confidence
              </span>
            )}
          </div>

          <h3 className="text-base font-semibold text-slate-100 leading-snug">
            {finding.title}
          </h3>

          <p className="text-sm text-slate-400 line-clamp-2">
            {finding.evidence}
          </p>
        </div>

        <button
          type="button"
          aria-label={expanded ? 'Collapse details' : 'Expand details'}
          className="self-end md:self-center p-2 rounded-lg bg-slate-800/60 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
        >
          {expanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </button>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="px-5 pb-5 pt-2 border-t border-slate-800/80 space-y-4 bg-slate-950/40">
          {/* Affected URLs */}
          {finding.affected_urls && finding.affected_urls.length > 0 && (
            <div className="space-y-1.5">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Affected URLs ({finding.affected_urls.length})
              </span>
              <div className="flex flex-wrap gap-2">
                {finding.affected_urls.map((url, i) => (
                  <a
                    key={i}
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs font-mono text-cyan-400 hover:text-cyan-300 bg-cyan-950/40 hover:bg-cyan-950/70 border border-cyan-900/50 px-2.5 py-1 rounded transition-colors"
                  >
                    <span className="truncate max-w-xs">{url}</span>
                    <ExternalLink className="w-3 h-3 flex-shrink-0" />
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* Evidence Full Block */}
          <div className="space-y-1.5">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Evidence Detected
            </span>
            <div className="p-3.5 rounded-lg bg-[#0B0F17] border border-slate-800/90 text-sm font-mono text-slate-300 leading-relaxed overflow-x-auto whitespace-pre-wrap">
              {finding.evidence}
            </div>
          </div>

          {/* Suggested Remediation Action */}
          <div className="space-y-2 p-4 rounded-xl bg-gradient-to-br from-slate-900/90 to-cyan-950/20 border border-cyan-900/30">
            <div className="flex items-center gap-2 text-cyan-300">
              <Lightbulb className="w-4 h-4 text-cyan-400 flex-shrink-0" />
              <span className="text-xs font-bold uppercase tracking-wider">
                Recommended Remediation
              </span>
              <span className="ml-auto text-[11px] font-mono px-2 py-0.5 rounded bg-cyan-900/50 text-cyan-200 border border-cyan-800/50">
                Priority: {finding.suggested_action?.priority || finding.severity}
              </span>
            </div>

            <p className="text-sm font-medium text-slate-200">
              {finding.suggested_action?.summary || (finding as any).remediation || 'No remediation required.'}
            </p>

            {finding.suggested_action.how && (
              <div className="pt-2 text-xs text-slate-400 leading-relaxed border-t border-slate-800">
                <span className="text-slate-300 font-semibold">How to fix: </span>
                {finding.suggested_action.how}
              </div>
            )}
          </div>

          {/* Verification Steps */}
          {verificationSteps.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center gap-1.5 text-slate-400 text-xs font-semibold uppercase tracking-wider">
                <Terminal className="w-3.5 h-3.5 text-slate-400" />
                <span>Verification Command & Validation</span>
              </div>
              <div className="space-y-2">
                {verificationSteps.map((step, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between gap-3 p-2.5 rounded-lg bg-[#0B0F17] border border-slate-800/80 font-mono text-xs text-emerald-400"
                  >
                    <code className="truncate select-all">{step}</code>
                    <button
                      type="button"
                      onClick={() => copyToClipboard(step, idx)}
                      title="Copy command"
                      className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors flex-shrink-0"
                    >
                      {copiedStep === idx ? (
                        <Check className="w-4 h-4 text-emerald-400" />
                      ) : (
                        <Copy className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
