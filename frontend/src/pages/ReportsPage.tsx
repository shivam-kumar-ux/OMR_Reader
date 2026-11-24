import React, { useState, useEffect } from 'react';
import { 
  FileSpreadsheet, 
  FileText, 
  Download, 
  BarChart, 
  CheckCircle2, 
  Award, 
  Layers
} from 'lucide-react';
import { api } from '../api/client';

export const ReportsPage: React.FC = () => {
  const [exams, setExams] = useState<any[]>([]);
  const [selectedExamId, setSelectedExamId] = useState<number | ''>('');
  const [results, setResults] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isExportingPdf, setIsExportingPdf] = useState(false);
  const [isExportingExcel, setIsExportingExcel] = useState(false);

  useEffect(() => {
    loadExams();
  }, []);

  useEffect(() => {
    if (selectedExamId) {
      loadExamResults(Number(selectedExamId));
    }
  }, [selectedExamId]);

  const loadExams = async () => {
    try {
      const data = await api.listExams(false);
      setExams(data);
      if (data.length > 0) {
        setSelectedExamId(data[0].id);
      }
    } catch {
      // Ignore
    }
  };

  const loadExamResults = async (examId: number) => {
    setIsLoading(true);
    try {
      const data = await api.listResults(examId);
      setResults(data.items || []);
    } catch {
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleExportPdf = async () => {
    if (!selectedExamId) return;
    setIsExportingPdf(true);
    try {
      const blob = await api.downloadExamPdf(Number(selectedExamId));
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const ex = exams.find(x => x.id === selectedExamId);
      a.download = `Exam_Report_${ex?.code || 'omr'}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err: any) {
      alert(`PDF Export Failed: ${err.message}`);
    } finally {
      setIsExportingPdf(false);
    }
  };

  const handleExportExcel = async () => {
    if (!selectedExamId) return;
    setIsExportingExcel(true);
    try {
      const blob = await api.downloadExamExcel(Number(selectedExamId));
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const ex = exams.find(x => x.id === selectedExamId);
      a.download = `Exam_Results_${ex?.code || 'omr'}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err: any) {
      alert(`Excel Export Failed: ${err.message}`);
    } finally {
      setIsExportingExcel(false);
    }
  };

  const totalCandidates = results.length;
  const scores = results.map(r => r.total_score || 0);
  const avgScore = totalCandidates > 0 ? (scores.reduce((a, b) => a + b, 0) / totalCandidates).toFixed(1) : '0';
  const highestScore = totalCandidates > 0 ? Math.max(...scores) : '0';
  const autoAccepted = results.filter(r => r.status === 'AUTO_ACCEPTED').length;
  const autoRate = totalCandidates > 0 ? Math.round((autoAccepted / totalCandidates) * 100) : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2.5">
            <FileSpreadsheet className="w-6 h-6 text-indigo-600" />
            Executive Reports & Analytics
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Generate formal publication-quality ReportLab PDFs and openpyxl multi-tab Excel reports.
          </p>
        </div>

        {/* Exam Selector */}
        <div className="flex items-center gap-3">
          <label className="text-xs font-bold text-slate-600 uppercase">Exam:</label>
          <select
            value={selectedExamId}
            onChange={(e) => setSelectedExamId(Number(e.target.value))}
            className="px-3.5 py-2 text-xs font-semibold rounded-xl border border-slate-200 bg-slate-50 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {exams.map(e => (
              <option key={e.id} value={e.id}>{e.code} &bull; {e.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* KPI Cards */}
      {isLoading && (
        <div className="text-xs font-semibold text-indigo-600 animate-pulse">Loading exam statistics...</div>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
            <Layers className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs text-slate-500 font-semibold uppercase block">Total Scans</span>
            <span className="text-2xl font-black text-slate-900">{totalCandidates}</span>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <Award className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs text-slate-500 font-semibold uppercase block">Top Score</span>
            <span className="text-2xl font-black text-emerald-600">{highestScore}</span>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
            <BarChart className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs text-slate-500 font-semibold uppercase block">Average Score</span>
            <span className="text-2xl font-black text-blue-600">{avgScore}</span>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs text-slate-500 font-semibold uppercase block">Auto-Accepted Rate</span>
            <span className="text-2xl font-black text-purple-600">{autoRate}%</span>
          </div>
        </div>
      </div>

      {/* Export Action Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* PDF Merit & Summary Card */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <div className="w-10 h-10 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center mb-4">
              <FileText className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-slate-900">
              Exam Summary & Merit List (PDF)
            </h3>
            <p className="text-xs text-slate-500 mt-2 leading-relaxed">
              Generates an executive PDF report built with <b>ReportLab Platypus</b>. Includes exam metadata, statistical overview cards, and candidate merit ranking with item scores and verification stamps.
            </p>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium">Format: ReportLab Vector PDF</span>
            <button
              onClick={handleExportPdf}
              disabled={isExportingPdf || !selectedExamId}
              className="px-4 py-2.5 bg-rose-600 hover:bg-rose-700 disabled:opacity-50 text-white rounded-xl text-xs font-semibold flex items-center gap-2 shadow-sm"
            >
              <Download className="w-4 h-4" />
              {isExportingPdf ? 'Compiling PDF...' : 'Download PDF Report'}
            </button>
          </div>
        </div>

        {/* Excel Roster Card */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center mb-4">
              <FileSpreadsheet className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-slate-900">
              Complete Candidate Roster (Excel .xlsx)
            </h3>
            <p className="text-xs text-slate-500 mt-2 leading-relaxed">
              Generates a formatted multi-tab spreadsheet using <b>openpyxl</b>. Sheet 1 includes all student fields (Roll, Name, Father's Name, Mobile, Class, Set, Marks, Ranks). Sheet 2 provides an Executive Summary.
            </p>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium">Format: Microsoft Excel XML (.xlsx)</span>
            <button
              onClick={handleExportExcel}
              disabled={isExportingExcel || !selectedExamId}
              className="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white rounded-xl text-xs font-semibold flex items-center gap-2 shadow-sm"
            >
              <Download className="w-4 h-4" />
              {isExportingExcel ? 'Exporting Excel...' : 'Download Excel Roster'}
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};

export default ReportsPage;
