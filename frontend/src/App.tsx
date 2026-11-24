import React, { useState, useEffect } from 'react';
import { 
  FileText, 
  Camera, 
  CheckSquare, 
  BarChart3, 
  LogOut, 
  Shield, 
  Layers,
  Award,
  Users,
  FileSpreadsheet,
  ShieldAlert
} from 'lucide-react';
import { getStoredUser, clearAuthToken, getAuthToken } from './api/client';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { ExamsPage } from './pages/ExamsPage';
import { ScanPage } from './pages/ScanPage';
import { VerifyPage } from './pages/VerifyPage';
import { ResultsPage } from './pages/ResultsPage';
import { StudentsPage } from './pages/StudentsPage';
import { ReportsPage } from './pages/ReportsPage';
import { AdminPage } from './pages/AdminPage';

export const App: React.FC = () => {
  const [currentUser, setCurrentUser] = useState<any | null>(getStoredUser());
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [activeVerifyId, setActiveVerifyId] = useState<number | null>(null);

  useEffect(() => {
    const handleUnauthorized = () => {
      setCurrentUser(null);
    };
    window.addEventListener('auth:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized);
  }, []);

  const handleLogout = () => {
    clearAuthToken();
    setCurrentUser(null);
    setCurrentTab('dashboard');
  };

  const handleNavigateToVerify = (resultId: number) => {
    setActiveVerifyId(resultId);
    setCurrentTab('verify');
  };

  if (!currentUser || !getAuthToken()) {
    return <LoginPage onLoginSuccess={(u) => setCurrentUser(u)} />;
  }

  const isAdmin = currentUser.role === 'Admin';

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      {/* Top Navbar */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-40 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            
            {/* Logo & Brand */}
            <div className="flex items-center gap-3 cursor-pointer" onClick={() => setCurrentTab('dashboard')}>
              <div className="w-9 h-9 rounded-xl bg-indigo-600 text-white font-black text-lg flex items-center justify-center shadow-sm">
                O
              </div>
              <div>
                <span className="text-base font-bold text-slate-900 tracking-tight leading-none block">
                  OMR Recognition
                </span>
                <span className="text-xs text-slate-400 font-medium leading-none block mt-0.5">
                  Enterprise Grading Engine
                </span>
              </div>
            </div>

            {/* Navigation Tabs */}
            <nav className="hidden md:flex items-center space-x-1">
              <button
                onClick={() => setCurrentTab('dashboard')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  currentTab === 'dashboard'
                    ? 'bg-indigo-50 text-indigo-700'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                <BarChart3 className="w-3.5 h-3.5" />
                Dashboard
              </button>

              <button
                onClick={() => setCurrentTab('exams')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  currentTab === 'exams'
                    ? 'bg-indigo-50 text-indigo-700'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                <FileText className="w-3.5 h-3.5" />
                Exams
              </button>

              <button
                onClick={() => setCurrentTab('scan')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  currentTab === 'scan'
                    ? 'bg-indigo-50 text-indigo-700'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                <Camera className="w-3.5 h-3.5" />
                Scan
              </button>

              <button
                onClick={() => setCurrentTab('results')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  currentTab === 'results'
                    ? 'bg-indigo-50 text-indigo-700'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                <Award className="w-3.5 h-3.5" />
                Results
              </button>

              <button
                onClick={() => setCurrentTab('students')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  currentTab === 'students'
                    ? 'bg-indigo-50 text-indigo-700'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                <Users className="w-3.5 h-3.5" />
                Students
              </button>

              <button
                onClick={() => setCurrentTab('reports')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  currentTab === 'reports'
                    ? 'bg-indigo-50 text-indigo-700'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                <FileSpreadsheet className="w-3.5 h-3.5" />
                Reports
              </button>

              {isAdmin && (
                <button
                  onClick={() => setCurrentTab('admin')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                    currentTab === 'admin'
                      ? 'bg-indigo-50 text-indigo-700'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                  }`}
                >
                  <ShieldAlert className="w-3.5 h-3.5" />
                  Admin
                </button>
              )}

              {activeVerifyId && (
                <button
                  onClick={() => setCurrentTab('verify')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                    currentTab === 'verify'
                      ? 'bg-amber-100 text-amber-800 ring-1 ring-amber-400'
                      : 'bg-amber-50 text-amber-700 hover:bg-amber-100'
                  }`}
                >
                  <CheckSquare className="w-3.5 h-3.5" />
                  Verify (#{activeVerifyId})
                </button>
              )}
            </nav>

            {/* User Profile & Logout */}
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2.5 px-3 py-1.5 bg-slate-100 rounded-xl">
                <div className="w-7 h-7 rounded-lg bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-xs">
                  {currentUser.username ? currentUser.username[0].toUpperCase() : 'U'}
                </div>
                <div className="text-left hidden sm:block">
                  <div className="text-xs font-bold text-slate-800 leading-none">
                    {currentUser.username}
                  </div>
                  <div className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider flex items-center gap-1 mt-0.5">
                    <Shield className="w-2.5 h-2.5 text-indigo-500" />
                    {currentUser.role}
                  </div>
                </div>
              </div>

              <button
                onClick={handleLogout}
                title="Sign out"
                className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Viewport */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        {currentTab === 'dashboard' && (
          <DashboardPage
            onNavigate={(tab, param) => {
              if (tab === 'verify' && param) {
                handleNavigateToVerify(param);
              } else {
                setCurrentTab(tab);
              }
            }}
          />
        )}

        {currentTab === 'exams' && <ExamsPage />}

        {currentTab === 'scan' && (
          <ScanPage onNavigateToVerify={handleNavigateToVerify} />
        )}

        {currentTab === 'results' && (
          <ResultsPage 
            onNavigateToVerify={handleNavigateToVerify}
            onNavigateToStudent={(_sid) => {
              setCurrentTab('students');
            }}
          />
        )}

        {currentTab === 'students' && (
          <StudentsPage
            onNavigateToResult={(_rid) => {
              setCurrentTab('results');
            }}
            onNavigateToVerify={handleNavigateToVerify}
          />
        )}

        {currentTab === 'reports' && <ReportsPage />}

        {currentTab === 'admin' && <AdminPage />}

        {currentTab === 'verify' && (
          activeVerifyId ? (
            <VerifyPage
              resultId={activeVerifyId}
              onBack={() => setCurrentTab('scan')}
              onNext={() => setCurrentTab('scan')}
            />
          ) : (
            <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center max-w-md mx-auto mt-12">
              <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-400 mx-auto flex items-center justify-center mb-4">
                <Layers className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-slate-800">No Sheet Selected for Verification</h3>
              <p className="text-sm text-slate-500 mt-2">
                Select a flagged sheet from the Scan tab or the Results tab to open side-by-side verification.
              </p>
              <button
                onClick={() => setCurrentTab('scan')}
                className="mt-6 px-4 py-2 bg-indigo-600 text-white rounded-xl text-sm font-semibold hover:bg-indigo-700"
              >
                Go to Scan Ingest
              </button>
            </div>
          )
        )}
      </main>
    </div>
  );
};

export default App;
