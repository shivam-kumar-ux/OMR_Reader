import React, { useState, useEffect } from 'react';
import { CheckCircle2, AlertTriangle, FileText, ArrowRight, Upload, Camera, Users, Award } from 'lucide-react';
import { api } from '../api/client';

interface DashboardPageProps {
  onNavigate: (tab: string, param?: any) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ onNavigate }) => {
  const [exams, setExams] = useState<any[]>([]);
  const [students, setStudents] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    setIsLoading(true);
    try {
      const [exList, stList] = await Promise.all([
        api.listExams(false),
        api.searchStudents(''),
      ]);
      setExams(exList);
      setStudents(stList);
    } catch {
      // Ignore initial error
    } finally {
      setIsLoading(false);
    }
  };

  const pendingVerificationCount = students.filter(s => !s.verified_flag).length;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Overview Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
            <FileText className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs text-slate-500 font-semibold block uppercase">Active Exams</span>
            <span className="text-2xl font-bold text-slate-900">{exams.length}</span>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs text-slate-500 font-semibold block uppercase">Total Students</span>
            <span className="text-2xl font-bold text-slate-900">{students.length}</span>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs text-slate-500 font-semibold block uppercase">Pending Review</span>
            <span className="text-2xl font-bold text-slate-900">{pendingVerificationCount}</span>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-sky-50 text-sky-600 flex items-center justify-center">
            <Award className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs text-slate-500 font-semibold block uppercase">Auto-Accepted</span>
            <span className="text-2xl font-bold text-slate-900">{students.length - pendingVerificationCount}</span>
          </div>
        </div>
      </div>

      {/* Quick Actions Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div
          onClick={() => onNavigate('scan')}
          className="bg-gradient-to-br from-indigo-500 to-indigo-700 p-6 rounded-2xl text-white shadow-sm hover:shadow-md transition-all cursor-pointer flex flex-col justify-between"
        >
          <div>
            <Upload className="w-8 h-8 text-indigo-200 mb-3" />
            <h3 className="text-lg font-bold">Upload & Batch Scan</h3>
            <p className="text-xs text-indigo-100 mt-1">
              Upload multiple images or multi-page PDFs to process answer sheets in bulk.
            </p>
          </div>
          <div className="mt-4 flex items-center gap-1 text-xs font-semibold text-white/90">
            Open Scan Ingestion <ArrowRight className="w-4 h-4" />
          </div>
        </div>

        <div
          onClick={() => onNavigate('scan')}
          className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-all cursor-pointer flex flex-col justify-between"
        >
          <div>
            <Camera className="w-8 h-8 text-emerald-600 mb-3" />
            <h3 className="text-lg font-bold text-slate-900">Live Camera Scan</h3>
            <p className="text-xs text-slate-500 mt-1">
              Capture answer sheets directly with your webcam or document camera with on-screen alignment.
            </p>
          </div>
          <div className="mt-4 flex items-center gap-1 text-xs font-semibold text-emerald-700">
            Launch Camera <ArrowRight className="w-4 h-4" />
          </div>
        </div>

        <div
          onClick={() => onNavigate('students')}
          className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-all cursor-pointer flex flex-col justify-between"
        >
          <div>
            <Users className="w-8 h-8 text-sky-600 mb-3" />
            <h3 className="text-lg font-bold text-slate-900">Student Search</h3>
            <p className="text-xs text-slate-500 mt-1">
              Search by Roll Number, Name, or Mobile to inspect answer sheet scans and results.
            </p>
          </div>
          <div className="mt-4 flex items-center gap-1 text-xs font-semibold text-sky-700">
            Lookup Records <ArrowRight className="w-4 h-4" />
          </div>
        </div>
      </div>

      {/* Active Exams Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-slate-900">Configured Exams</h2>
          <button
            onClick={() => onNavigate('exams')}
            className="text-indigo-600 hover:text-indigo-700 font-semibold text-xs flex items-center gap-1"
          >
            Manage Exams & Keys <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-4">Exam Name</th>
                <th className="py-2.5 px-4">Code</th>
                <th className="py-2.5 px-4">Questions</th>
                <th className="py-2.5 px-4">Marking</th>
                <th className="py-2.5 px-4">Sets</th>
                <th className="py-2.5 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {exams.map((ex: any) => (
                <tr key={ex.id} className="hover:bg-slate-50">
                  <td className="py-3 px-4 font-semibold text-slate-900">{ex.name}</td>
                  <td className="py-3 px-4 font-mono text-slate-700">{ex.code}</td>
                  <td className="py-3 px-4 text-slate-600">{ex.total_questions} Questions</td>
                  <td className="py-3 px-4 text-slate-600">
                    +{ex.marks_per_correct} / -{ex.negative_marks}
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex gap-1">
                      {ex.sets && ex.sets.length > 0 ? (
                        ex.sets.map((s: string) => (
                          <span key={s} className="px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded text-xs font-bold">
                            {s}
                          </span>
                        ))
                      ) : (
                        <span className="text-xs text-slate-400">No keys loaded</span>
                      )}
                    </div>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <button
                      onClick={() => onNavigate('scan')}
                      className="px-3 py-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded-lg text-xs font-semibold"
                    >
                      Scan Sheets
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
