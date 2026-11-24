import React, { useState, useEffect } from 'react';
import { AlertTriangle, RefreshCw, ZoomIn, ZoomOut, Save, ArrowLeft, ShieldCheck } from 'lucide-react';
import { api } from '../api/client';

interface VerifyPageProps {
  resultId: number;
  onBack: () => void;
  onNext?: () => void;
}

export const VerifyPage: React.FC<VerifyPageProps> = ({ resultId, onBack, onNext }) => {
  const [data, setData] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [activeImageTab, setActiveImageTab] = useState<'processed' | 'raw'>('processed');
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Editable Form State
  const [nameFinal, setNameFinal] = useState('');
  const [fatherNameFinal, setFatherNameFinal] = useState('');
  const [rollNoFinal, setRollNoFinal] = useState('');
  const [mobileFinal, setMobileFinal] = useState('');
  const [dobFinal, setDobFinal] = useState('');
  const [classFinal, setClassFinal] = useState('');
  const [setCodeFinal, setSetCodeFinal] = useState('');
  const [questionCorrections, setQuestionCorrections] = useState<Record<number, string | null>>({});

  useEffect(() => {
    loadResultDetails(resultId);
  }, [resultId]);

  const loadResultDetails = async (id: number) => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const res = await api.getResult(id);
      setData(res);
      const s = res.student || {};
      setNameFinal(s.name_final || '');
      setFatherNameFinal(s.father_name_final || '');
      setRollNoFinal(s.roll_no || '');
      setMobileFinal(s.mobile_final || '');
      setDobFinal(s.dob_final || '');
      setClassFinal(s.class_name_final || '');
      setSetCodeFinal(res.set_code || 'A');

      const initialCorr: Record<number, string | null> = {};
      (res.answers || []).forEach((a: any) => {
        initialCorr[a.question_no] = a.marked_option;
      });
      setQuestionCorrections(initialCorr);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load sheet details');
    } finally {
      setIsLoading(false);
    }
  };

  const handleOptionOverride = (qNo: number, option: string) => {
    setQuestionCorrections(prev => {
      const current = prev[qNo];
      // Toggle if clicking same
      return {
        ...prev,
        [qNo]: current === option ? null : option,
      };
    });
  };

  const handleConfirmAndSave = async () => {
    if (!data) return;
    setIsSaving(true);
    setErrorMsg(null);

    const correctionsList = Object.entries(questionCorrections).map(([q, opt]) => ({
      question_no: Number(q),
      marked_option: opt,
    }));

    try {
      await api.confirmReview({
        result_id: data.id,
        student_fields: {
          name_final: nameFinal,
          father_name_final: fatherNameFinal,
          roll_no: rollNoFinal,
          mobile_final: mobileFinal,
          dob_final: dobFinal,
          class_name_final: classFinal,
          set_code: setCodeFinal,
        },
        question_corrections: correctionsList,
        comments: 'Verified by Operator via Verification UI',
      });

      if (onNext) {
        onNext();
      } else {
        onBack();
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to confirm and save changes');
    } finally {
      setIsSaving(false);
    }
  };

  const handleRecheckStrict = async () => {
    if (!data) return;
    setIsSaving(true);
    setErrorMsg(null);
    try {
      await api.recheckResult(data.id, true);
      await loadResultDetails(data.id);
    } catch (err: any) {
      setErrorMsg(err.message || 'Recheck failed');
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="p-12 text-center bg-white rounded-2xl border border-slate-200">
        <RefreshCw className="w-8 h-8 animate-spin text-indigo-600 mx-auto mb-2" />
        <p className="text-slate-600 font-medium">Loading sheet verification details...</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="p-8 text-center bg-white rounded-2xl border border-slate-200">
        <p className="text-rose-600 font-semibold mb-4">Result record could not be loaded.</p>
        <button onClick={onBack} className="px-4 py-2 bg-slate-200 hover:bg-slate-300 rounded-lg text-sm">
          Return to List
        </button>
      </div>
    );
  }

  const s = data.student || {};
  const imageSource = activeImageTab === 'processed' && data.processed_image_path
    ? `/${data.processed_image_path}`
    : `/${data.sheet_image_path}`;

  return (
    <div className="space-y-6">
      {/* Verification Header */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="p-2 hover:bg-slate-100 rounded-lg text-slate-600 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-slate-900">
                Verify Sheet — {s.name_final || 'Unnamed'} (Roll: {s.roll_no})
              </h1>
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                data.status === 'AUTO_ACCEPTED'
                  ? 'bg-emerald-100 text-emerald-800'
                  : data.status === 'CONFIRMED'
                  ? 'bg-blue-100 text-blue-800'
                  : 'bg-amber-100 text-amber-800'
              }`}>
                {data.status.replace('_', ' ')}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Exam: {data.exam?.name} ({data.exam?.code}) | Set {data.set_code} | Confidence: {Math.round((data.confidence_score || 0) * 100)}%
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleRecheckStrict}
            disabled={isSaving}
            className="px-4 py-2 border border-slate-300 hover:bg-slate-50 text-slate-700 text-sm font-semibold rounded-xl flex items-center gap-1.5 transition-colors"
            title="Re-run OMR with strict 50% fill threshold"
          >
            <RefreshCw className="w-4 h-4" /> Recheck (Strict)
          </button>

          <button
            onClick={handleConfirmAndSave}
            disabled={isSaving}
            className="px-6 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-sm font-bold rounded-xl shadow flex items-center gap-2 transition-all active:scale-95"
          >
            <Save className="w-4 h-4" /> Save & Next
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-sm flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 shrink-0" /> {errorMsg}
        </div>
      )}

      {/* Review Reasons Banner */}
      {data.review_reason && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-amber-800 text-sm flex items-start gap-2.5">
          <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold">Reasons Flagged for Operator Verification:</span>
            <p className="mt-0.5 text-xs text-amber-900 leading-relaxed">{data.review_reason}</p>
          </div>
        </div>
      )}

      {/* Main Split View: Left Image, Right Verification Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Pane: Interactive Scanned Sheet Viewer */}
        <div className="lg:col-span-6 bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex flex-col h-[780px]">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-3">
            <div className="flex bg-slate-100 rounded-lg p-1 text-xs font-semibold">
              <button
                onClick={() => setActiveImageTab('processed')}
                className={`px-3 py-1 rounded-md transition-colors ${
                  activeImageTab === 'processed' ? 'bg-white shadow text-indigo-700' : 'text-slate-600'
                }`}
              >
                Processed Overlay
              </button>
              <button
                onClick={() => setActiveImageTab('raw')}
                className={`px-3 py-1 rounded-md transition-colors ${
                  activeImageTab === 'raw' ? 'bg-white shadow text-indigo-700' : 'text-slate-600'
                }`}
              >
                Raw Scanned Sheet
              </button>
            </div>

            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setZoomLevel(prev => Math.max(prev - 0.25, 0.5))}
                className="p-1.5 hover:bg-slate-100 rounded-lg text-slate-600"
              >
                <ZoomOut className="w-4 h-4" />
              </button>
              <span className="text-xs text-slate-500 font-mono">{Math.round(zoomLevel * 100)}%</span>
              <button
                onClick={() => setZoomLevel(prev => Math.min(prev + 0.25, 3))}
                className="p-1.5 hover:bg-slate-100 rounded-lg text-slate-600"
              >
                <ZoomIn className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-auto bg-slate-900/5 rounded-xl border border-slate-200/60 p-4 flex items-center justify-center">
            <img
              src={imageSource}
              alt="OMR Sheet"
              style={{ transform: `scale(${zoomLevel})`, transformOrigin: 'top center' }}
              className="max-w-full rounded shadow transition-transform duration-150"
            />
          </div>
        </div>

        {/* Right Pane: Personal Details Verification & Question Overrides */}
        <div className="lg:col-span-6 space-y-6">
          {/* Section 1: Personal Details Comparison Table */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-indigo-600" />
              Personal Data Cross-Check
            </h2>

            <div className="space-y-4 text-xs divide-y divide-slate-100">
              {/* Roll Number */}
              <div className="pt-2">
                <div className="flex justify-between items-center mb-1">
                  <span className="font-semibold text-slate-700">Roll Number (Source of Truth: Bubbles)</span>
                  <span className="text-slate-400">OCR: {s.roll_no_ocr || '—'}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-1.5 bg-slate-100 rounded text-slate-700 font-mono font-bold">
                    Bubbled: {s.roll_no || '—'}
                  </span>
                  <input
                    type="text"
                    value={rollNoFinal}
                    onChange={e => setRollNoFinal(e.target.value)}
                    placeholder="Final Roll Number"
                    className="flex-1 px-3 py-1.5 border border-slate-300 rounded-lg font-mono text-sm font-semibold focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              {/* Candidate Name */}
              <div className="pt-3">
                <div className="flex justify-between items-center mb-1">
                  <span className="font-semibold text-slate-700">Candidate Name (Bubbles vs OCR)</span>
                  <span className="text-slate-400">OCR: {s.name_ocr || '—'}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-1.5 bg-slate-100 rounded text-slate-700 font-bold">
                    Bubbled: {s.name_bubble || '—'}
                  </span>
                  <input
                    type="text"
                    value={nameFinal}
                    onChange={e => setNameFinal(e.target.value)}
                    placeholder="Verified Candidate Name"
                    className="flex-1 px-3 py-1.5 border border-slate-300 rounded-lg text-sm font-semibold focus:ring-2 focus:ring-indigo-500 uppercase"
                  />
                </div>
              </div>

              {/* Father's Name */}
              <div className="pt-3">
                <div className="flex justify-between items-center mb-1">
                  <span className="font-semibold text-slate-700">Father's Name (Handwriting Crop)</span>
                  <span className="text-slate-400">OCR: {s.father_name_ocr || '—'}</span>
                </div>
                <input
                  type="text"
                  value={fatherNameFinal}
                  onChange={e => setFatherNameFinal(e.target.value)}
                  placeholder="Father's Name"
                  className="w-full px-3 py-1.5 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 uppercase"
                />
              </div>

              {/* Mobile, DOB, Class, Set in Grid */}
              <div className="pt-3 grid grid-cols-2 md:grid-cols-4 gap-3">
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Mobile</label>
                  <input
                    type="text"
                    value={mobileFinal}
                    onChange={e => setMobileFinal(e.target.value)}
                    className="w-full px-2 py-1.5 border border-slate-300 rounded-lg text-sm font-mono"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">DOB</label>
                  <input
                    type="text"
                    value={dobFinal}
                    onChange={e => setDobFinal(e.target.value)}
                    className="w-full px-2 py-1.5 border border-slate-300 rounded-lg text-sm font-mono"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Class</label>
                  <input
                    type="text"
                    value={classFinal}
                    onChange={e => setClassFinal(e.target.value)}
                    className="w-full px-2 py-1.5 border border-slate-300 rounded-lg text-sm font-mono"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Set Code</label>
                  <select
                    value={setCodeFinal}
                    onChange={e => setSetCodeFinal(e.target.value)}
                    className="w-full px-2 py-1.5 border border-slate-300 rounded-lg text-sm font-bold bg-white"
                  >
                    {['A', 'B', 'C', 'D'].map(code => (
                      <option key={code} value={code}>
                        Set {code}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          </div>

          {/* Section 2: Questions Grid Overrides */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-slate-900">Question Marked Answers</h2>
                <p className="text-xs text-slate-500">
                  Click on any option (A, B, C, D) to override detected value.
                </p>
              </div>
              <div className="flex items-center gap-3 text-xs">
                <span className="flex items-center gap-1 font-medium text-emerald-700">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span> Correct ({data.counts?.correct})
                </span>
                <span className="flex items-center gap-1 font-medium text-rose-700">
                  <span className="w-2.5 h-2.5 rounded-full bg-rose-500"></span> Wrong ({data.counts?.wrong})
                </span>
                <span className="flex items-center gap-1 font-medium text-amber-700">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span> Uncertain/Multi ({data.counts?.multi_marked})
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-5 gap-2 max-h-[380px] overflow-y-auto p-2 border border-slate-100 rounded-xl">
              {(data.answers || []).map((ans: any) => {
                const currentVal = questionCorrections[ans.question_no];
                const isCorrect = ans.correct_option && currentVal === ans.correct_option;
                const isWrong = currentVal && ans.correct_option && currentVal !== ans.correct_option;

                return (
                  <div
                    key={ans.question_no}
                    className={`p-2 rounded-lg border text-xs flex flex-col justify-between transition-all ${
                      ans.status === 'UNCERTAIN' || ans.status === 'MULTI'
                        ? 'border-amber-300 bg-amber-50/50'
                        : isCorrect
                        ? 'border-emerald-200 bg-emerald-50/30'
                        : isWrong
                        ? 'border-rose-200 bg-rose-50/30'
                        : 'border-slate-200 bg-white'
                    }`}
                  >
                    <div className="flex justify-between font-semibold text-slate-600 mb-1">
                      <span>Q{ans.question_no}</span>
                      <span className="text-slate-400">Key: {ans.correct_option || '—'}</span>
                    </div>

                    <div className="flex gap-1 justify-between">
                      {['A', 'B', 'C', 'D'].map(opt => (
                        <button
                          key={opt}
                          type="button"
                          onClick={() => handleOptionOverride(ans.question_no, opt)}
                          className={`w-5 h-5 rounded-full text-center font-bold text-[10px] transition-all ${
                            currentVal === opt
                              ? 'bg-indigo-600 text-white shadow-sm ring-2 ring-indigo-400'
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
          </div>
        </div>
      </div>
    </div>
  );
};
