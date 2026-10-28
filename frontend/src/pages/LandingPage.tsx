import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Navbar } from '../components/Navbar';
import { FindingCard } from '../components/FindingCard';
import { EXAMPLE_AUDIT_REPORT } from '../services/exampleData';
import { api, ApiError } from '../services/api';
import { sessionStore } from '../services/sessionStore';
import {
  Search,
  Zap,
  Shield,
  Bot,
  FileCode,
  FileCheck,
  Lock,
  Braces,
  ArrowRight,
  AlertCircle,
  Loader2,
} from 'lucide-react';

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const [urlInput, setUrlInput] = useState('https://stripe.com');
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!urlInput.trim() || submitting) return;

    setSubmitting(true);
    setErrorMsg(null);

    try {
      const res = await api.submitAudit(urlInput.trim());
      // Record in session store
      sessionStore.saveAudit({
        audit_id: res.audit_id,
        url: res.url,
        created_at: res.created_at,
        status: 'queued',
      });
      // Navigate to tracking/report page
      navigate(`/audit/${res.audit_id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorMsg(err.detail);
      } else {
        setErrorMsg('Failed to submit audit. Please ensure the backend API is running.');
      }
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#0B0F17] text-slate-100">
      <Navbar />

      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 md:py-16 space-y-20">
        {/* Hero Section matching Stitch layout */}
        <section className="text-center space-y-8 max-w-4xl mx-auto">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-cyan-950/60 text-cyan-300 border border-cyan-800/50 text-xs font-mono font-medium tracking-wide">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse"></span>
            AUTONOMOUS WEBSITE AUDIT ENGINE &bull; PROVIDER-NEUTRAL
          </div>

          {/* Main Headline */}
          <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold tracking-tight text-slate-100 leading-[1.15]">
            Find the barriers that make your website harder for{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-teal-300">
              AI assistants
            </span>{' '}
            to discover, understand, and cite.
          </h1>

          {/* Subtitle */}
          <p className="text-base sm:text-lg text-slate-400 max-w-2xl mx-auto leading-relaxed">
            Autonomous, robots-aware website auditing engine for LLMs, answer engines, and
            search assistants. Inspects crawl boundaries, raw HTML quotability, entity schema,
            and non-text blindspots.
          </p>

          {/* Prominent URL Search Bar */}
          <div className="max-w-2xl mx-auto space-y-3">
            <form onSubmit={handleSubmit} className="relative">
              <div className="flex items-center rounded-xl bg-[#111827] border border-slate-700/80 p-2 shadow-[0_0_35px_rgba(0,0,0,0.6)] focus-within:border-cyan-500 focus-within:ring-2 focus-within:ring-cyan-500/20 transition-all">
                <Search className="w-5 h-5 text-slate-400 ml-3 flex-shrink-0" />
                <input
                  type="text"
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  placeholder="https://yourwebsite.com"
                  disabled={submitting}
                  className="w-full bg-transparent px-3 py-2 text-slate-100 placeholder-slate-500 focus:outline-none font-mono text-sm"
                />
                <button
                  type="submit"
                  disabled={submitting || !urlInput.trim()}
                  className="flex-shrink-0 inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-gradient-to-r from-cyan-500 to-teal-400 hover:from-cyan-400 hover:to-teal-300 text-slate-950 font-semibold text-sm shadow-[0_0_20px_rgba(6,182,212,0.35)] transition-all disabled:opacity-60 disabled:cursor-not-allowed hover:scale-[1.02] active:scale-[0.98]"
                >
                  {submitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin text-slate-950" />
                      Starting...
                    </>
                  ) : (
                    <>
                      <Zap className="w-4 h-4 fill-current" />
                      Run Free Audit <span className="font-mono text-xs opacity-80">&crarr; Enter</span>
                    </>
                  )}
                </button>
              </div>
            </form>

            {errorMsg && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-rose-950/60 border border-rose-800/80 text-rose-300 text-sm">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            {/* Subtext info & Example report link */}
            <div className="flex flex-wrap items-center justify-between text-xs text-slate-400 px-2 gap-2">
              <span className="flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5 text-cyan-400" />
                Audits public entrypoints, sitemaps, and core content up to 12 pages with robots.txt compliance.
              </span>
              <a
                href="#example-report"
                className="text-cyan-400 hover:text-cyan-300 font-medium inline-flex items-center gap-1"
              >
                View Example Report &darr;
              </a>
            </div>
          </div>

          {/* Capability Pill Tags */}
          <div className="flex flex-wrap items-center justify-center gap-2.5 pt-4 text-xs font-mono">
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300">
              <Bot className="w-3.5 h-3.5 text-cyan-400" />
              Robots-aware Bounded Crawl
            </span>
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300">
              <FileCode className="w-3.5 h-3.5 text-teal-400" />
              Raw HTML & AST Quotability Check
            </span>
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300">
              <FileCheck className="w-3.5 h-3.5 text-emerald-400" />
              Evidence-Backed Findings & Verification Steps
            </span>
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300">
              <Lock className="w-3.5 h-3.5 text-slate-400" />
              Safe Read-Only Inspection (No Live Writes)
            </span>
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300">
              <Braces className="w-3.5 h-3.5 text-indigo-400" />
              JSON Report Export (RFC Schema Aligned)
            </span>
          </div>
        </section>

        {/* Demo Data Section matching Stitch UI */}
        <section id="example-report" className="space-y-6 pt-12 border-t border-slate-800/80">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-xl bg-slate-900/60 border border-slate-800">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="font-mono text-[11px] font-bold px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
                  EXAMPLE REPORT &bull; DEMO DATA (TARGET: STRIPE.COM)
                </span>
              </div>
              <h2 className="text-xl font-bold text-slate-100">
                4 Actionable Findings Detected across 5 Audit Dimensions
              </h2>
            </div>
            <Link
              to="/audit/new"
              className="inline-flex items-center gap-1.5 text-xs font-semibold px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors self-start sm:self-center"
            >
              Audit Your Website <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {/* Finding Cards Grid */}
          <div className="grid grid-cols-1 gap-4">
            {EXAMPLE_AUDIT_REPORT.findings.map((finding) => (
              <FindingCard key={finding.id} finding={finding} defaultExpanded={finding.id === 'CRA-01'} />
            ))}
          </div>
        </section>

        {/* Features / How It Works Section */}
        <section id="how-it-works" className="space-y-12 pt-12 border-t border-slate-800/80">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <h2 className="text-3xl font-extrabold text-slate-100">
              How the AI-Readiness Funnel Operates
            </h2>
            <p className="text-sm text-slate-400">
              AI assistants cite websites through a strict three-tier visibility funnel: Indexing, Citability, and Landability.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-6 rounded-xl bg-[#111827] border border-slate-800 space-y-3">
              <div className="w-10 h-10 rounded-lg bg-cyan-950/60 border border-cyan-800/60 text-cyan-400 flex items-center justify-center font-bold">
                1
              </div>
              <h3 className="text-lg font-bold text-slate-100">1. Index Barrier Check</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Evaluates robots.txt AI user-agent directives (ClaudeBot, GPTBot, PerplexityBot), sitemap accessibility, and whether SPA frameworks deliver blank empty client shells prior to JavaScript execution.
              </p>
            </div>

            <div className="p-6 rounded-xl bg-[#111827] border border-slate-800 space-y-3">
              <div className="w-10 h-10 rounded-lg bg-teal-950/60 border border-teal-800/60 text-teal-400 flex items-center justify-center font-bold">
                2
              </div>
              <h3 className="text-lg font-bold text-slate-100">2. Citability & Schema</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Inspects Schema.org JSON-LD nodes, Organization NAP, SpeakableSpecification for audio briefs, entity disambiguation, and Wikipedia/Wikidata offsite consensus consistency.
              </p>
            </div>

            <div className="p-6 rounded-xl bg-[#111827] border border-slate-800 space-y-3">
              <div className="w-10 h-10 rounded-lg bg-emerald-950/60 border border-emerald-800/60 text-emerald-400 flex items-center justify-center font-bold">
                3
              </div>
              <h3 className="text-lg font-bold text-slate-100">3. Landability & CTAs</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Verifies that once an AI assistant cites your brand and refers a visitor, the destination has working CTAs, semantic H1 hierarchy, breadcrumb navigation, and accessible non-empty FAQ accordions.
              </p>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-[#0B0F17] py-8 text-center text-xs text-slate-500 space-y-2">
        <p>Brand AI-Readiness Engine &bull; Provider-Neutral Autonomous Audit &bull; Python 3.10+ Stdlib</p>
        <p className="font-mono text-[11px]">MIT License &bull; Connected to FastAPI REST Backend</p>
      </footer>
    </div>
  );
};
