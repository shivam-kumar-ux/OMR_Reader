import React from 'react';

export const App: React.FC = () => {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <header className="bg-white border-b border-slate-200 px-6 py-4 shadow-sm">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-indigo-600 rounded-lg flex items-center justify-center text-white font-bold text-lg shadow-sm">
              OMR
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-900 leading-none">OMR Recognition System</h1>
              <p className="text-xs text-slate-500 mt-1">High-Precision Optical Mark Recognition</p>
            </div>
          </div>
        </div>
      </header>
      <main className="flex-1 max-w-7xl mx-auto w-full p-6">
        <div className="bg-white rounded-xl border border-slate-200 p-8 shadow-sm text-center">
          <h2 className="text-lg font-semibold text-slate-800">System Ready</h2>
          <p className="text-sm text-slate-500 mt-2">Ready to scan and process student OMR answer sheets.</p>
        </div>
      </main>
    </div>
  );
};

export default App;
