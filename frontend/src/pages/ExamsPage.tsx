import React, { useState, useEffect } from 'react';
import { Plus, Upload, Download, CheckCircle2, AlertCircle } from 'lucide-react';
import { api } from '../api/client';

export const ExamsPage: React.FC = () => {
  const [exams, setExams] = useState<any[]>([]);
  const [selectedExam, setSelectedExam] = useState<any | null>(null);
  const [selectedSet, setSelectedSet] = useState<string>('A');
  const [keys, setKeys] = useState<Record<number, string>>({});
  const [isSaving, setIsSaving] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [statusMsg, setStatusMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // New Exam Form
  const [newExamName, setNewExamName] = useState('');
  const [newExamCode, setNewExamCode] = useState('');
  const [newTotalQ, setNewTotalQ] = useState(50);
  const [newMarksCorrect, setNewMarksCorrect] = useState(4.0);
  const [newNegativeMarks, setNewNegativeMarks] = useState(1.0);
  const [newMultiRule, setNewMultiRule] = useState('COUNT_AS_WRONG');

  useEffect(() => {
    loadExams();
  }, []);

  const loadExams = async () => {
    try {
      const data = await api.listExams(false);
      setExams(data);
      if (data.length > 0 && !selectedExam) {
        selectExam(data[0]);
      }
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || 'Failed to load exams' });
    }
  };

  const selectExam = async (exam: any) => {
    setSelectedExam(exam);
    const setCode = exam.sets && exam.sets.length > 0 ? exam.sets[0] : 'A';
    setSelectedSet(setCode);
    loadAnswerKeys(exam.id, setCode);
  };

  const loadAnswerKeys = async (examId: number, setCode: string) => {
    try {
      const keyList = await api.getAnswerKeys(examId, setCode);
      const keyMap: Record<number, string> = {};
      keyList.forEach((k: any) => {
        keyMap[k.question_no] = k.correct_option;
      });
      setKeys(keyMap);
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || 'Failed to load answer keys' });
    }
  };

  const handleSetChange = (setCode: string) => {
    setSelectedSet(setCode);
    if (selectedExam) {
      loadAnswerKeys(selectedExam.id, setCode);
    }
  };

  const handleOptionClick = (qNo: number, option: string) => {
    setKeys(prev => ({
      ...prev,
      [qNo]: prev[qNo] === option ? '' : option,
    }));
  };

  const handleSaveManualKeys = async () => {
    if (!selectedExam) return;
    setIsSaving(true);
    setStatusMsg(null);
    try {
      const keysPayload = Object.entries(keys)
        .filter(([_, opt]) => opt)
        .map(([q, opt]) => ({ question_no: Number(q), correct_option: opt }));

      await api.saveAnswerKeys(selectedExam.id, {
        set_code: selectedSet,
        keys: keysPayload,
      });

      setStatusMsg({ type: 'success', text: `Saved ${keysPayload.length} answer keys for Set ${selectedSet}!` });
      loadExams();
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || 'Failed to save answer keys' });
    } finally {
      setIsSaving(false);
    }
  };

  const handleCsvUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!selectedExam || !e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    setIsSaving(true);
    setStatusMsg(null);
    try {
      const res = await api.uploadAnswerKeysCsv(selectedExam.id, file);
      setStatusMsg({
        type: 'success',
        text: `Successfully imported ${res.total_keys_imported} answer keys for sets: ${res.sets_updated.join(', ')}!`,
      });
      loadExams();
      if (selectedExam) {
        loadAnswerKeys(selectedExam.id, selectedSet);
      }
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || 'CSV import failed' });
    } finally {
      setIsSaving(false);
      e.target.value = '';
    }
  };

  const handleDownloadTemplate = () => {
    if (!selectedExam) return;
    window.open(`/api/v1/exams/${selectedExam.id}/answer-keys/template?format_type=columns`, '_blank');
  };

  const handleCreateExam = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setStatusMsg(null);
    try {
      const created = await api.createExam({
        name: newExamName.trim(),
        code: newExamCode.trim().toUpperCase(),
        total_questions: Number(newTotalQ),
        marks_per_correct: Number(newMarksCorrect),
        negative_marks: Number(newNegativeMarks),
        multi_marked_rule: newMultiRule,
      });
      setShowCreateModal(false);
      setNewExamName('');
      setNewExamCode('');
      setStatusMsg({ type: 'success', text: `Exam ${created.code} created successfully!` });
      await loadExams();
      selectExam(created);
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || 'Failed to create exam' });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Bar */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Exams & Answer Keys</h1>
          <p className="text-sm text-slate-500 mt-1">
            Configure exams, scoring policies, and answer keys across multiple sets (A, B, C, D).
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl text-sm shadow flex items-center gap-2 self-start md:self-auto"
        >
          <Plus className="w-4 h-4" /> Create New Exam
        </button>
      </div>

      {statusMsg && (
        <div
          className={`p-4 rounded-xl text-sm flex items-center gap-2 ${
            statusMsg.type === 'success'
              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
              : 'bg-rose-50 text-rose-800 border border-rose-200'
          }`}
        >
          {statusMsg.type === 'success' ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
          {statusMsg.text}
        </div>
      )}

      {/* Main Grid: Exams List & Key Editor */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left: Exams Navigation */}
        <div className="lg:col-span-4 bg-white p-4 rounded-2xl border border-slate-200 shadow-sm space-y-2">
          <h2 className="text-xs font-bold text-slate-500 uppercase tracking-wider px-2 mb-2">Available Exams</h2>
          <div className="space-y-1.5 max-h-[600px] overflow-y-auto">
            {exams.map(exam => {
              const isSelected = selectedExam?.id === exam.id;
              return (
                <div
                  key={exam.id}
                  onClick={() => selectExam(exam)}
                  className={`p-3 rounded-xl border transition-all cursor-pointer ${
                    isSelected
                      ? 'border-indigo-600 bg-indigo-50/50 text-indigo-900 shadow-sm'
                      : 'border-slate-100 hover:border-slate-300 bg-white text-slate-800'
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <h3 className="font-bold text-sm leading-tight">{exam.name}</h3>
                    <span className="font-mono text-xs font-bold px-1.5 py-0.5 bg-white border border-slate-200 rounded">
                      {exam.code}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 mt-2 text-xs text-slate-500">
                    <span>{exam.total_questions} Qs</span>
                    <span>+{exam.marks_per_correct} / -{exam.negative_marks}</span>
                    <span className="font-medium text-indigo-600">
                      Sets: {exam.sets && exam.sets.length > 0 ? exam.sets.join(', ') : 'None'}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Answer Key Editor */}
        <div className="lg:col-span-8 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-6">
          {selectedExam ? (
            <>
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-100 pb-4">
                <div>
                  <h2 className="text-lg font-bold text-slate-900">
                    Answer Key — {selectedExam.name} ({selectedExam.code})
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {selectedExam.total_questions} Questions | Marking: +{selectedExam.marks_per_correct} / -{selectedExam.negative_marks}
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <button
                    onClick={handleDownloadTemplate}
                    className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg flex items-center gap-1.5"
                  >
                    <Download className="w-3.5 h-3.5" /> CSV Template
                  </button>

                  <label className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg flex items-center gap-1.5 cursor-pointer">
                    <Upload className="w-3.5 h-3.5" /> Upload CSV
                    <input
                      type="file"
                      accept=".csv"
                      className="hidden"
                      onChange={handleCsvUpload}
                    />
                  </label>

                  <button
                    onClick={handleSaveManualKeys}
                    disabled={isSaving}
                    className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-bold rounded-lg shadow flex items-center gap-1.5"
                  >
                    Save Set {selectedSet} Keys
                  </button>
                </div>
              </div>

              {/* Set Tabs */}
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-500 mr-2 uppercase tracking-wide">Select Set:</span>
                {['A', 'B', 'C', 'D'].map(sCode => (
                  <button
                    key={sCode}
                    onClick={() => handleSetChange(sCode)}
                    className={`px-4 py-1.5 rounded-lg text-sm font-bold transition-all ${
                      selectedSet === sCode
                        ? 'bg-indigo-600 text-white shadow'
                        : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
                    }`}
                  >
                    Set {sCode}
                  </button>
                ))}
              </div>

              {/* Interactive Bubble Key Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3 max-h-[500px] overflow-y-auto p-3 border border-slate-100 rounded-xl bg-slate-50/50">
                {Array.from({ length: selectedExam.total_questions }, (_, i) => i + 1).map(qNo => {
                  const marked = keys[qNo];
                  return (
                    <div
                      key={qNo}
                      className="p-2.5 bg-white border border-slate-200 rounded-xl shadow-xs flex flex-col justify-between"
                    >
                      <div className="flex justify-between items-center text-xs font-semibold text-slate-500 mb-1.5">
                        <span>Q{String(qNo).padStart(2, '0')}</span>
                        {marked && <span className="font-bold text-indigo-600">[{marked}]</span>}
                      </div>

                      <div className="flex justify-between gap-1">
                        {['A', 'B', 'C', 'D'].map(opt => (
                          <button
                            key={opt}
                            onClick={() => handleOptionClick(qNo, opt)}
                            className={`w-6 h-6 rounded-full text-xs font-bold transition-all ${
                              marked === opt
                                ? 'bg-indigo-600 text-white shadow ring-2 ring-indigo-400'
                                : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
                            }`}
                          >
                            {opt}
                          </button>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          ) : (
            <div className="p-12 text-center text-slate-400">Select an exam from the left to configure answer keys.</div>
          )}
        </div>
      </div>

      {/* Create Exam Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-slate-900">Create New Exam</h3>

            <form onSubmit={handleCreateExam} className="space-y-4 text-sm">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Exam Name</label>
                <input
                  type="text"
                  required
                  value={newExamName}
                  onChange={e => setNewExamName(e.target.value)}
                  placeholder="e.g. Mathematics Entrance 2026"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Exam Code</label>
                <input
                  type="text"
                  required
                  value={newExamCode}
                  onChange={e => setNewExamCode(e.target.value)}
                  placeholder="e.g. MATH-2026"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg uppercase font-mono"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Questions</label>
                  <input
                    type="number"
                    min="1"
                    max="500"
                    value={newTotalQ}
                    onChange={e => setNewTotalQ(Number(e.target.value))}
                    className="w-full px-2 py-2 border border-slate-300 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Marks / Q</label>
                  <input
                    type="number"
                    step="0.5"
                    value={newMarksCorrect}
                    onChange={e => setNewMarksCorrect(Number(e.target.value))}
                    className="w-full px-2 py-2 border border-slate-300 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Negative</label>
                  <input
                    type="number"
                    step="0.25"
                    value={newNegativeMarks}
                    onChange={e => setNewNegativeMarks(Number(e.target.value))}
                    className="w-full px-2 py-2 border border-slate-300 rounded-lg"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Multi-Marked Bubble Rule</label>
                <select
                  value={newMultiRule}
                  onChange={e => setNewMultiRule(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-white"
                >
                  <option value="COUNT_AS_WRONG">Count as Wrong (-negative marks)</option>
                  <option value="COUNT_AS_NOT_ATTEMPTED">Count as Not Attempted (0 marks)</option>
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 border border-slate-300 hover:bg-slate-50 rounded-lg font-semibold text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSaving}
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-bold text-xs"
                >
                  Create Exam
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
