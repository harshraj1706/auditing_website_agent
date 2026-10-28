import React from 'react';
import { Link } from 'react-router-dom';
import { Cpu, Play, ExternalLink } from 'lucide-react';

export const Navbar: React.FC = () => {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-slate-800/80 bg-[#0B0F17]/90 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <Link to="/" className="flex items-center gap-3 group">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-cyan-600 to-teal-400 flex items-center justify-center shadow-[0_0_15px_rgba(6,182,212,0.3)] group-hover:scale-105 transition-transform">
            <Cpu className="w-5 h-5 text-slate-950 font-bold" />
          </div>
          <span className="font-bold text-lg text-slate-100 tracking-tight flex items-center gap-1.5">
            Brand AI-Readiness <span className="text-cyan-400 font-mono text-sm uppercase px-1.5 py-0.5 rounded bg-cyan-950/60 border border-cyan-800/50">Engine</span>
          </span>
        </Link>

        {/* Desktop Navigation */}
        <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-slate-300">
          <Link to="/" className="hover:text-cyan-400 transition-colors">
            Home
          </Link>
          <a href="#how-it-works" className="hover:text-cyan-400 transition-colors">
            How It Works
          </a>
          <a href="#features" className="hover:text-cyan-400 transition-colors">
            Features
          </a>
          <a href="#methodology" className="hover:text-cyan-400 transition-colors">
            Methodology
          </a>
          <a
            href="https://github.com/harshraj1706/auditing_website_agent"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 font-mono text-xs text-slate-400 hover:text-cyan-300 transition-colors"
          >
            &lt;&gt; GitHub
            <ExternalLink className="w-3 h-3" />
          </a>
        </nav>

        {/* CTA Button */}
        <div className="flex items-center gap-3">
          <Link
            to="/audit/new"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-cyan-500 to-teal-400 hover:from-cyan-400 hover:to-teal-300 text-slate-950 font-semibold text-sm shadow-[0_0_20px_rgba(6,182,212,0.35)] transition-all hover:scale-[1.02] active:scale-[0.98]"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            Start Free Audit
          </Link>
        </div>
      </div>
    </header>
  );
};
