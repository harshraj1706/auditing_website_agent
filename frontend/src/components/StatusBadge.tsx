import React from 'react';
import type { JobStatus, SeverityLevel } from '../types/audit';
import { AlertCircle, AlertTriangle, CheckCircle2, Clock, Loader2, ShieldAlert } from 'lucide-react';

interface StatusBadgeProps {
  status: JobStatus;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const isSm = size === 'sm';
  const sizeClasses = isSm ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-xs font-semibold';

  switch (status) {
    case 'queued':
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700 ${sizeClasses}`}>
          <Clock className={isSm ? 'w-3 h-3 text-slate-400' : 'w-3.5 h-3.5 text-slate-400'} />
          Queued
        </span>
      );
    case 'running':
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-full bg-cyan-950/70 text-cyan-300 border border-cyan-800/60 shadow-[0_0_10px_rgba(6,182,212,0.2)] ${sizeClasses}`}>
          <Loader2 className={`animate-spin text-cyan-400 ${isSm ? 'w-3 h-3' : 'w-3.5 h-3.5'}`} />
          Analyzing Site...
        </span>
      );
    case 'completed':
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-full bg-emerald-950/70 text-emerald-300 border border-emerald-800/60 ${sizeClasses}`}>
          <CheckCircle2 className={`text-emerald-400 ${isSm ? 'w-3 h-3' : 'w-3.5 h-3.5'}`} />
          Completed
        </span>
      );
    case 'failed':
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-full bg-rose-950/70 text-rose-300 border border-rose-800/60 ${sizeClasses}`}>
          <AlertCircle className={`text-rose-400 ${isSm ? 'w-3 h-3' : 'w-3.5 h-3.5'}`} />
          Failed
        </span>
      );
    default:
      return null;
  }
};

interface SeverityBadgeProps {
  severity: SeverityLevel;
  className?: string;
}

export const SeverityBadge: React.FC<SeverityBadgeProps> = ({ severity, className = '' }) => {
  switch (severity.toLowerCase()) {
    case 'critical':
      return (
        <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-mono font-bold tracking-wider uppercase bg-rose-950/60 text-rose-400 border border-rose-700/50 ${className}`}>
          <ShieldAlert className="w-3 h-3 text-rose-400" />
          Critical
        </span>
      );
    case 'high':
      return (
        <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-mono font-bold tracking-wider uppercase bg-amber-950/60 text-amber-400 border border-amber-700/50 ${className}`}>
          <AlertTriangle className="w-3 h-3 text-amber-400" />
          High
        </span>
      );
    case 'medium':
      return (
        <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-mono font-bold tracking-wider uppercase bg-yellow-950/50 text-yellow-300 border border-yellow-700/40 ${className}`}>
          <AlertCircle className="w-3 h-3 text-yellow-400" />
          Medium
        </span>
      );
    case 'low':
      return (
        <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-mono font-bold tracking-wider uppercase bg-cyan-950/50 text-cyan-300 border border-cyan-800/40 ${className}`}>
          Low / Proactive
        </span>
      );
    default:
      return (
        <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-mono font-bold uppercase bg-slate-800 text-slate-300 ${className}`}>
          {severity}
        </span>
      );
  }
};
