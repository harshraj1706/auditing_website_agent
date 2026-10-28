import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { LandingPage } from './pages/LandingPage';
import { NewAuditPage } from './pages/NewAuditPage';
import { DashboardPage } from './pages/DashboardPage';
import { FindingsExplorerPage } from './pages/FindingsExplorerPage';
import { RecentAuditsPage } from './pages/RecentAuditsPage';
import { SettingsPage } from './pages/SettingsPage';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public Landing Page */}
        <Route path="/" element={<LandingPage />} />

        {/* Audit Dispatcher */}
        <Route path="/audit/new" element={<NewAuditPage />} />

        {/* Specific Audit Dashboard / Report View */}
        <Route path="/audit/:auditId" element={<DashboardPage />} />

        {/* General Dashboard (shows latest or demo) */}
        <Route path="/dashboard" element={<DashboardPage />} />

        {/* Findings Explorer */}
        <Route path="/findings" element={<FindingsExplorerPage />} />

        {/* Session Audit History */}
        <Route path="/history" element={<RecentAuditsPage />} />

        {/* System & Engine Settings */}
        <Route path="/settings" element={<SettingsPage />} />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
