import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sidebar } from '../components/Sidebar';
import { api, ApiError } from '../services/api';
import { sessionStore } from '../services/sessionStore';
import {
  Globe,
  Zap,
  Shield,
  AlertCircle,
  Loader2,
  ArrowRight,
} from 'lucide-react';

export const NewAuditPage: React.FC = () => {
  const navigate = useNavigate();
  const [url, setUrl] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim() || submitting) return;

    setSubmitting(true);
    setErrorMsg(null);

    try {
      const res = await api.submitAudit(url.trim());
      // Save in session store
      sessionStore.saveAudit({
        audit_id: res.audit_id,
        url: res.url,
        created_at: res.created_at,
        status: 'queued',
      });
      // Redirect to the audit status/report page
      navigate(`/audit/${res.audit_id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorMsg(err.detail);
      } else {
        setErrorMsg('Failed to submit audit. Please verify the API server is reachable.');
      }
      setSubmitting(false);
    }
  };

  const handleQuickSelect = (quickUrl: string) => {
    setUrl(quickUrl);
    setErrorMsg(null);
  };

  return (
    <div className="min-h-screen flex flex-col md:flex-row bg-[#0B0F17] text-slate-100">
      <Sidebar />

      <main className="flex-1 p-6 md:p-10 max-w-5xl mx-auto space-y-8">
        {/* Header */}
        <div className="space-y-2 border-b border-slate-800 pb-6">
          <div className="flex items-center gap-2 text-xs font-mono text-cyan-400">
            <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
            AUTONOMOUS AUDIT DISPATCHER
          </div>
          <h1 className="text-3xl font-extrabold text-slate-100 tracking-tight">
            Start a New Website Audit
          </h1>
          <p className="text-sm text-slate-400 max-w-2xl">
            Submit any public website URL. The engine crawls within safe robots-aware boundaries
            (≤12 pages) and evaluates citability, raw HTML quotability, and Schema.org markup.
          </p>
        </div>

        {/* Audit Configuration Form */}
        <div className="rounded-2xl bg-[#111827] border border-slate-800 p-6 md:p-8 space-y-8 shadow-xl">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Target URL Input */}
            <div className="space-y-2">
              <label htmlFor="target-url" className="block text-sm font-semibold text-slate-200">
                Target Website URL <span className="text-rose-400">*</span>
              </label>
              <div className="relative">
                <Globe className="w-5 h-5 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  id="target-url"
                  type="text"
                  value={url}
                  onChange={(e) => {
                    setUrl(e.target.value);
                    if (errorMsg) setErrorMsg(null);
                  }}
                  placeholder="https://example.com"
                  disabled={submitting}
                  className="w-full bg-[#0B0F17] border border-slate-700/80 rounded-xl pl-11 pr-4 py-3 text-slate-100 font-mono text-sm placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all"
                  required
                />
              </div>
              <p className="text-xs text-slate-500">
                Enter an HTTP or HTTPS URL. The crawler strictly obeys robots.txt and never performs live writes.
              </p>
            </div>

            {/* Quick Test URL Pills */}
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="text-slate-400">Quick suggestions:</span>
              {['https://example.com', 'https://stripe.com', 'https://kivihealth.com'].map(
                (quickUrl) => (
                  <button
                    key={quickUrl}
                    type="button"
                    onClick={() => handleQuickSelect(quickUrl)}
                    className="font-mono text-cyan-400 hover:text-cyan-300 bg-cyan-950/40 hover:bg-cyan-950/70 border border-cyan-800/50 px-2.5 py-1 rounded transition-colors"
                  >
                    {quickUrl}
                  </button>
                )
              )}
            </div>

            {/* Audit Mode Scope Card */}
            <div className="p-4 rounded-xl bg-[#0B0F17]/70 border border-slate-800 space-y-3">
              <div className="flex items-center gap-2.5 text-slate-200 font-semibold text-sm">
                <Shield className="w-4 h-4 text-cyan-400" />
                <span>Execution Scope & Calibration</span>
                <span className="ml-auto text-xs font-mono text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800/50">
                  Standard Bounded
                </span>
              </div>
              <ul className="text-xs text-slate-400 space-y-1.5 list-disc list-inside">
                <li><strong className="text-slate-300">Robots-aware Bounded Crawl:</strong> Maximum sample of 12 pages following sitemaps and on-origin links.</li>
                <li><strong className="text-slate-300">AI Crawler Probes:</strong> User-agent checks for GPTBot, ClaudeBot, and PerplexityBot.</li>
                <li><strong className="text-slate-300">Digital Consensus:</strong> Disambiguation check against Wikipedia, Wikidata, and community echo.</li>
                <li><strong className="text-slate-300">Strictly Read-Only:</strong> Zero form submissions, no cart flows, no authentication bypass.</li>
              </ul>
            </div>

            {/* Error Message */}
            {errorMsg && (
              <div className="flex items-start gap-3 p-4 rounded-xl bg-rose-950/60 border border-rose-800 text-rose-300 text-sm">
                <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <div className="font-semibold text-rose-200">Unable to Start Audit</div>
                  <div>{errorMsg}</div>
                </div>
              </div>
            )}

            {/* Submit Button */}
            <div className="flex items-center justify-end gap-4 pt-4 border-t border-slate-800">
              <button
                type="submit"
                disabled={submitting || !url.trim()}
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-teal-400 hover:from-cyan-400 hover:to-teal-300 text-slate-950 font-bold text-sm shadow-[0_0_20px_rgba(6,182,212,0.35)] transition-all disabled:opacity-50 disabled:cursor-not-allowed hover:scale-[1.02] active:scale-[0.98]"
              >
                {submitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin text-slate-950" />
                    Enqueuing Audit...
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4 fill-current" />
                    Run Audit Now <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
};
