import React, { useState, useEffect } from 'react';
import { 
  FileText, 
  Search, 
  Download, 
  Award, 
  Eye, 
  RefreshCw
} from 'lucide-react';
import { api } from '../api/client';

interface ResultsPageProps {
  onNavigateToVerify: (resultId: number) => void;
  onNavigateToStudent: (studentId: number) => void;
}

export const ResultsPage: React.FC<ResultsPageProps> = ({ onNavigateToVerify, onNavigateToStudent }) => {
  const [exams, setExams] = useState<any[]>([]);
  const [selectedExamId, setSelectedExamId] = useState<number | ''>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [results, setResults] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  // Selected Result Modal for 50-Question Visual Grid
  const [activeResult, setActiveResult] = useState<any | null>(null);

  useEffect(() => {
    loadExams();
  }, []);

  useEffect(() => {
    loadResults();
  }, [selectedExamId, statusFilter]);

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

  const loadResults = async () => {
    setIsLoading(true);
    try {
      const data = await api.listResults(
        selectedExamId ? Number(selectedExamId) : undefined,
        statusFilter || undefined
      );
      setResults(data.items || []);
    } catch {
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  };

  const openResultDetail = async (resultId: number) => {
    try {
      const detail = await api.getResult(resultId);
      setActiveResult(detail);
    } catch {
      // Ignore
    }
  };

  const handleDownloadPdf = async (resultId: number, rollNo: string) => {
    try {
      const blob = await api.downloadResultPdf(resultId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Scorecard_${rollNo}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err: any) {
      alert(`Download failed: ${err.message}`);
    }
  };

  const filteredResults = results.filter(r => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      (r.student_name && r.student_name.toLowerCase().includes(q)) ||
      (r.student_roll && r.student_roll.toLowerCase().includes(q)) ||
      (r.set_code && r.set_code.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-6">
      {/* Header and Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2.5">
            <Award className="w-6 h-6 text-indigo-600" />
            Exam Results & Scorecards
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Browse evaluation outcomes, audit item responses, and export student scorecards.
          </p>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={selectedExamId}
            onChange={(e) => setSelectedExamId(e.target.value ? Number(e.target.value) : '')}
            className="px-3.5 py-2 text-xs font-semibold rounded-xl border border-slate-200 bg-slate-50 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Exams</option>
            {exams.map(e => (
              <option key={e.id} value={e.id}>{e.code} - {e.name}</option>
            ))}
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3.5 py-2 text-xs font-semibold rounded-xl border border-slate-200 bg-slate-50 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Statuses</option>
            <option value="AUTO_ACCEPTED">Auto Accepted</option>
            <option value="NEEDS_REVIEW">Needs Review</option>
            <option value="CONFIRMED">Confirmed</option>
          </select>

          <button
            onClick={loadResults}
            className="p-2 border border-slate-200 rounded-xl hover:bg-slate-50 text-slate-600"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Search Bar */}
      <div className="relative">
        <Search className="w-4 h-4 text-slate-400 absolute left-4 top-3.5" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search by student name, roll number, or set code..."
          className="w-full pl-11 pr-4 py-2.5 rounded-xl border border-slate-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      {/* Results Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center p-16">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
          </div>
        ) : filteredResults.length === 0 ? (
          <div className="p-16 text-center">
            <FileText className="w-10 h-10 text-slate-300 mx-auto mb-3" />
            <h4 className="text-sm font-bold text-slate-700">No Evaluation Records Found</h4>
            <p className="text-xs text-slate-400 mt-1">
              No sheets match your selected exam or status filter.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-50 border-b border-slate-200 uppercase font-bold text-slate-500">
                <tr>
                  <th className="px-5 py-3">Roll No</th>
                  <th className="px-5 py-3">Candidate</th>
                  <th className="px-5 py-3">Exam</th>
                  <th className="px-4 py-3 text-center">Set</th>
                  <th className="px-5 py-3 text-right">Score</th>
                  <th className="px-4 py-3 text-center">C / W / Blank</th>
                  <th className="px-4 py-3 text-center">Confidence</th>
                  <th className="px-4 py-3 text-center">Status</th>
                  <th className="px-5 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredResults.map(r => (
                  <tr key={r.id} className="hover:bg-slate-50/75 transition-colors">
                    <td className="px-5 py-3 font-mono font-bold text-slate-900">
                      {r.student_roll || '-'}
                    </td>
                    <td className="px-5 py-3 font-semibold text-slate-800">
                      <button
                        onClick={() => r.student_id && onNavigateToStudent(r.student_id)}
                        className="hover:text-indigo-600 hover:underline flex items-center gap-1.5"
                      >
                        {r.student_name || 'Unnamed Student'}
                      </button>
                    </td>
                    <td className="px-5 py-3 text-slate-500 truncate max-w-[160px]">
                      {r.exam_name || '-'}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="px-2 py-0.5 rounded-md bg-slate-100 font-bold text-slate-700">
                        {r.set_code || 'A'}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-right font-black text-slate-900 text-sm">
                      {r.total_score}
                    </td>
                    <td className="px-4 py-3 text-center font-medium">
                      <span className="text-emerald-600 font-bold">{r.correct_count}</span>
                      <span className="text-slate-300 mx-1">/</span>
                      <span className="text-rose-500 font-bold">{r.wrong_count}</span>
                      <span className="text-slate-300 mx-1">/</span>
                      <span className="text-slate-400">{r.not_attempted_count}</span>
                    </td>
                    <td className="px-4 py-3 text-center font-semibold">
                      {intPct(r.confidence_score)}%
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        r.status === 'AUTO_ACCEPTED'
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          : r.status === 'CONFIRMED'
                          ? 'bg-indigo-50 text-indigo-700 border border-indigo-200'
                          : 'bg-amber-50 text-amber-700 border border-amber-200'
                      }`}>
                        {r.status}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => openResultDetail(r.id)}
                          className="px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-semibold flex items-center gap-1"
                          title="Open Scorecard"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>View</span>
                        </button>
                        {r.status === 'NEEDS_REVIEW' && (
                          <button
                            onClick={() => onNavigateToVerify(r.id)}
                            className="px-2.5 py-1.5 bg-amber-500 hover:bg-amber-600 text-white rounded-lg font-semibold"
                            title="Verify Sheet"
                          >
                            Verify
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Scorecard Modal with 50-Question Visual Grid */}
      {activeResult && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto border border-slate-200 shadow-2xl p-6 space-y-6 animate-in fade-in zoom-in-95 duration-150">
            
            {/* Modal Header */}
            <div className="flex items-start justify-between border-b border-slate-100 pb-4">
              <div>
                <span className="text-xs font-bold text-indigo-600 uppercase tracking-wider block">
                  Official Scorecard & Question Grid
                </span>
                <h3 className="text-xl font-bold text-slate-900 mt-1">
                  {activeResult.student?.name_final || 'Candidate Scorecard'}
                </h3>
                <p className="text-xs text-slate-500">
                  Roll No: <b className="text-slate-800">{activeResult.student?.roll_no}</b> &bull; Set: <b className="text-slate-800">{activeResult.set_code}</b> &bull; Exam: <b className="text-slate-800">{activeResult.exam?.name}</b>
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleDownloadPdf(activeResult.id, activeResult.student?.roll_no || 'scorecard')}
                  className="px-3.5 py-2 bg-indigo-600 text-white rounded-xl text-xs font-semibold hover:bg-indigo-700 flex items-center gap-1.5 shadow-sm"
                >
                  <Download className="w-3.5 h-3.5" />
                  PDF Card
                </button>
                <button
                  onClick={() => setActiveResult(null)}
                  className="w-8 h-8 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-600 flex items-center justify-center font-bold text-sm"
                >
                  &times;
                </button>
              </div>
            </div>

            {/* Score Banner */}
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 p-4 bg-slate-50 rounded-xl border border-slate-200 text-center">
              <div>
                <span className="text-[10px] text-slate-400 uppercase font-bold block">Total Score</span>
                <span className="text-2xl font-black text-indigo-600">{activeResult.total_score}</span>
              </div>
              <div>
                <span className="text-[10px] text-slate-400 uppercase font-bold block">Correct</span>
                <span className="text-2xl font-black text-emerald-600">{activeResult.correct_count}</span>
              </div>
              <div>
                <span className="text-[10px] text-slate-400 uppercase font-bold block">Wrong</span>
                <span className="text-2xl font-black text-rose-500">{activeResult.wrong_count}</span>
              </div>
              <div>
                <span className="text-[10px] text-slate-400 uppercase font-bold block">Unattempted</span>
                <span className="text-2xl font-black text-slate-500">{activeResult.not_attempted_count}</span>
              </div>
              <div>
                <span className="text-[10px] text-slate-400 uppercase font-bold block">Confidence</span>
                <span className="text-2xl font-black text-slate-800">{intPct(activeResult.confidence_score)}%</span>
              </div>
            </div>

            {/* Green / Red / Grey / Yellow Question Response Grid */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                  Itemized Question Responses (50 Questions)
                </h4>
                <div className="flex items-center gap-3 text-[11px] font-semibold">
                  <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-emerald-500 inline-block"></span> Correct</span>
                  <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-rose-500 inline-block"></span> Wrong</span>
                  <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-slate-300 inline-block"></span> Blank</span>
                  <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-amber-400 inline-block"></span> Multi</span>
                </div>
              </div>

              <div className="grid grid-cols-5 sm:grid-cols-10 gap-2 p-4 bg-slate-50/70 border border-slate-200 rounded-xl">
                {(activeResult.answers || []).map((ans: any) => {
                  const isMulti = ans.status === 'MULTI' || (ans.marked_option && ans.marked_option.length > 1);
                  const isBlank = !ans.marked_option || ans.status === 'EMPTY';
                  const isCorrect = ans.is_correct;

                  let colorClass = 'bg-slate-200 border-slate-300 text-slate-600'; // Default Blank
                  if (isMulti) {
                    colorClass = 'bg-amber-100 border-amber-300 text-amber-800';
                  } else if (isCorrect) {
                    colorClass = 'bg-emerald-100 border-emerald-300 text-emerald-800';
                  } else if (!isBlank) {
                    colorClass = 'bg-rose-100 border-rose-300 text-rose-800';
                  }

                  return (
                    <div
                      key={ans.question_no}
                      className={`p-2 rounded-xl border flex flex-col items-center justify-center text-center shadow-2xs ${colorClass}`}
                    >
                      <span className="text-[10px] font-bold opacity-75">Q{ans.question_no}</span>
                      <span className="text-sm font-black mt-0.5">
                        {ans.marked_option || '-'}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Actions Footer */}
            <div className="flex items-center justify-between border-t border-slate-100 pt-4">
              <span className="text-xs text-slate-500">
                Status: <b className="text-slate-800">{activeResult.status}</b>
              </span>
              <div className="flex gap-2">
                {activeResult.status === 'NEEDS_REVIEW' && (
                  <button
                    onClick={() => {
                      const id = activeResult.id;
                      setActiveResult(null);
                      onNavigateToVerify(id);
                    }}
                    className="px-4 py-2 bg-amber-500 text-white rounded-xl text-xs font-semibold hover:bg-amber-600"
                  >
                    Open in Verification Desk
                  </button>
                )}
                <button
                  onClick={() => setActiveResult(null)}
                  className="px-4 py-2 bg-slate-100 text-slate-700 rounded-xl text-xs font-semibold hover:bg-slate-200"
                >
                  Close
                </button>
              </div>
            </div>

          </div>
        </div>
      )}
    </div>
  );
};

function intPct(val: any): number {
  if (val === undefined || val === null) return 0;
  const num = typeof val === 'number' ? val : parseFloat(val);
  return Math.round(num * 100);
}
export default ResultsPage;
