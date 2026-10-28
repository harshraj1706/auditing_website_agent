import React, { useEffect, useState } from 'react';
import { NavLink, Link } from 'react-router-dom';
import {
  Cpu,
  PlusCircle,
  LayoutDashboard,
  Layers,
  Clock,
  Settings,
  ExternalLink,
  Menu,
  X,
} from 'lucide-react';
import { api } from '../services/api';

export const Sidebar: React.FC = () => {
  const [engineReady, setEngineReady] = useState<boolean | null>(null);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    api
      .checkHealth()
      .then((res) => setEngineReady(res.engine_ready))
      .catch(() => setEngineReady(false));
  }, []);

  const navItems = [
    { name: 'New Audit', to: '/audit/new', icon: PlusCircle },
    { name: 'Dashboard', to: '/dashboard', icon: LayoutDashboard },
    { name: 'Detailed Findings', to: '/findings', icon: Layers },
    { name: 'Recent Audits', to: '/history', icon: Clock },
    { name: 'System & Engine Info', to: '/settings', icon: Settings },
  ];

  return (
    <>
      {/* Mobile Header */}
      <div className="md:hidden flex items-center justify-between p-4 bg-[#0B0F17] border-b border-slate-800">
        <Link to="/" className="flex items-center gap-2">
          <div className="w-7 h-7 rounded bg-gradient-to-tr from-cyan-500 to-teal-400 flex items-center justify-center">
            <Cpu className="w-4 h-4 text-slate-950 font-bold" />
          </div>
          <span className="font-bold text-sm text-slate-100">Brand AI Engine</span>
        </Link>
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="p-2 rounded bg-slate-800 text-slate-300"
          aria-label="Toggle menu"
        >
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Sidebar Container */}
      <aside
        className={`fixed md:sticky top-0 left-0 z-40 h-screen w-64 bg-[#0D121F] border-r border-slate-800 flex flex-col justify-between transition-transform duration-200 md:translate-x-0 ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="p-5 space-y-6">
          {/* Logo */}
          <Link
            to="/"
            onClick={() => setMobileOpen(false)}
            className="flex items-center gap-3 group"
          >
            <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-cyan-500 to-teal-400 flex items-center justify-center shadow-[0_0_15px_rgba(6,182,212,0.3)] group-hover:scale-105 transition-transform">
              <Cpu className="w-5 h-5 text-slate-950 font-bold" />
            </div>
            <div>
              <span className="font-bold text-sm text-slate-100 tracking-tight block">
                Brand AI-Readiness
              </span>
              <span className="text-[11px] font-mono text-cyan-400 block tracking-wider uppercase">
                Audit Workspace
              </span>
            </div>
          </Link>

          {/* Navigation */}
          <nav className="space-y-1.5 pt-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={() => setMobileOpen(false)}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                      isActive
                        ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 shadow-[0_0_12px_rgba(6,182,212,0.15)] font-semibold'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                    }`
                  }
                >
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  <span>{item.name}</span>
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* Engine status footer */}
        <div className="p-4 border-t border-slate-800/80 space-y-3 bg-[#0B0F17]/60">
          <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 text-xs space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-slate-400 font-medium">Audit Engine</span>
              {engineReady === null ? (
                <span className="text-slate-500">Checking...</span>
              ) : engineReady ? (
                <span className="inline-flex items-center gap-1 text-emerald-400 font-mono text-[11px] font-semibold">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                  Ready
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-rose-400 font-mono text-[11px] font-semibold">
                  <span className="w-2 h-2 rounded-full bg-rose-400"></span>
                  Offline
                </span>
              )}
            </div>
            <div className="text-[11px] text-slate-500">
              Robots-aware &bull; Bounded (≤12 pgs) &bull; Read-only
            </div>
          </div>

          <div className="flex items-center justify-between text-[11px] text-slate-500 font-mono px-1">
            <span>FastAPI &bull; Stdlib 3.10+</span>
            <a
              href="https://github.com/harshraj1706/auditing_website_agent"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-cyan-400 flex items-center gap-0.5"
            >
              Docs <ExternalLink className="w-2.5 h-2.5" />
            </a>
          </div>
        </div>
      </aside>
    </>
  );
};
