import React, { useState, useEffect } from 'react';
import { Camera, Upload, FolderUp, CheckCircle, AlertTriangle, XCircle, RefreshCw, Eye } from 'lucide-react';
import { api } from '../api/client';
import { CameraCapture } from '../components/CameraCapture';

interface ScanPageProps {
  onNavigateToVerify: (resultId: number) => void;
}

export const ScanPage: React.FC<ScanPageProps> = ({ onNavigateToVerify }) => {
  const [exams, setExams] = useState<any[]>([]);
  const [selectedExamId, setSelectedExamId] = useState<number | ''>('');
  const [selectedSetCode, setSelectedSetCode] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'upload' | 'camera' | 'scanner'>('upload');

  const [isProcessing, setIsProcessing] = useState(false);
  const [batchResults, setBatchResults] = useState<any | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    loadExams();
  }, []);

  const loadExams = async () => {
    try {
      const data = await api.listExams(true);
      setExams(data);
      if (data.length > 0) {
        setSelectedExamId(data[0].id);
        if (data[0].sets && data[0].sets.length > 0) {
          setSelectedSetCode(data[0].sets[0]);
        }
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to load exams');
    }
  };

  const handleExamChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const id = Number(e.target.value);
    setSelectedExamId(id);
    const ex = exams.find(x => x.id === id);
    if (ex && ex.sets && ex.sets.length > 0) {
      setSelectedSetCode(ex.sets[0]);
    } else {
      setSelectedSetCode('');
    }
  };

  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0 || !selectedExamId) return;
    setIsProcessing(true);
    setErrorMessage(null);
    setBatchResults(null);

    try {
      const fileArray = Array.from(files);
      const res = await api.scanBatchSheets(Number(selectedExamId), fileArray, selectedSetCode || undefined);
      setBatchResults(res);
    } catch (err: any) {
      setErrorMessage(err.message || 'Batch scanning failed');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleCameraCapture = async (file: File) => {
    if (!selectedExamId) return;
    setIsProcessing(true);
    setErrorMessage(null);

    try {
      const res = await api.scanSingleSheet(Number(selectedExamId), file, selectedSetCode || undefined);
      setBatchResults({
        batch_id: 'camera_capture',
        total_files_received: 1,
        total_sheets_processed: 1,
        auto_accepted_count: res.status === 'done' ? 1 : 0,
        needs_review_count: res.status === 'needs_review' ? 1 : 0,
        failed_count: res.status === 'failed' ? 1 : 0,
        results: [res],
      });
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to process camera capture');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleScanFolder = async () => {
    if (!selectedExamId) return;
    setIsProcessing(true);
    setErrorMessage(null);
    try {
      const res = await api.processScannerFolder(Number(selectedExamId));
      setBatchResults(res);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to import scanner folder');
    } finally {
      setIsProcessing(false);
    }
  };

  const activeExam = exams.find(x => x.id === Number(selectedExamId));

  return (
    <div className="space-y-6">
      {/* Top Banner & Exam Configuration */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Scan & Ingest Answer Sheets</h1>
            <p className="text-sm text-slate-500 mt-1">
              Supports browser camera with alignment guide, bulk PDF/images, and scanner hot-folder.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Target Exam</label>
              <select
                value={selectedExamId}
                onChange={handleExamChange}
                className="px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm font-medium focus:ring-2 focus:ring-indigo-500 min-w-[200px]"
              >
                {exams.map(exam => (
                  <option key={exam.id} value={exam.id}>
                    {exam.name} ({exam.code})
                  </option>
                ))}
              </select>
            </div>

            {activeExam && activeExam.sets && activeExam.sets.length > 0 && (
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Override Set</label>
                <select
                  value={selectedSetCode}
                  onChange={e => setSelectedSetCode(e.target.value)}
                  className="px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm font-medium focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="">Auto-Detect from Bubbles</option>
                  {activeExam.sets.map((s: string) => (
                    <option key={s} value={s}>
                      Set {s}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
        </div>

        {errorMessage && (
          <div className="mt-4 p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-sm flex items-center gap-2">
            <XCircle className="w-5 h-5 shrink-0" /> {errorMessage}
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 bg-white rounded-t-xl px-4 pt-2">
        <button
          onClick={() => setActiveTab('upload')}
          className={`px-5 py-3 font-semibold text-sm border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === 'upload'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Upload className="w-4 h-4" /> Files & Folders
        </button>
        <button
          onClick={() => setActiveTab('camera')}
          className={`px-5 py-3 font-semibold text-sm border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === 'camera'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Camera className="w-4 h-4" /> Browser Camera
        </button>
        <button
          onClick={() => setActiveTab('scanner')}
          className={`px-5 py-3 font-semibold text-sm border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === 'scanner'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <FolderUp className="w-4 h-4" /> Scanner Hot-Folder
        </button>
      </div>

      {/* Tab Panels */}
      <div className="bg-white p-6 rounded-b-xl border border-t-0 border-slate-200 shadow-sm">
        {activeTab === 'upload' && (
          <div className="space-y-4">
            <div
              onDragOver={e => e.preventDefault()}
              onDrop={e => {
                e.preventDefault();
                handleFileUpload(e.dataTransfer.files);
              }}
              className="border-2 border-dashed border-slate-300 hover:border-indigo-500 rounded-2xl p-10 text-center bg-slate-50/50 hover:bg-indigo-50/20 transition-all cursor-pointer flex flex-col items-center justify-center"
              onClick={() => document.getElementById('file-upload-input')?.click()}
            >
              <div className="w-14 h-14 bg-indigo-100 rounded-full flex items-center justify-center text-indigo-600 mb-3 shadow-inner">
                <Upload className="w-7 h-7" />
              </div>
              <h3 className="text-base font-semibold text-slate-800">
                Click or drag & drop OMR answer sheets
              </h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm">
                Supports JPG, JPEG, PNG, TIFF, BMP, WEBP, and multi-page PDF documents.
              </p>
              <input
                id="file-upload-input"
                type="file"
                multiple
                accept=".jpg,.jpeg,.png,.tiff,.bmp,.webp,.pdf"
                className="hidden"
                onChange={e => handleFileUpload(e.target.files)}
              />
            </div>

            <div className="flex items-center justify-between text-xs text-slate-500 px-2">
              <span>Need to upload an entire directory of scans?</span>
              <button
                onClick={() => document.getElementById('folder-upload-input')?.click()}
                className="text-indigo-600 hover:text-indigo-700 font-semibold flex items-center gap-1"
              >
                <FolderUp className="w-4 h-4" /> Select Directory
              </button>
              <input
                id="folder-upload-input"
                type="file"
                multiple
                // @ts-ignore
                webkitdirectory="true"
                className="hidden"
                onChange={e => handleFileUpload(e.target.files)}
              />
            </div>
          </div>
        )}

        {activeTab === 'camera' && (
          <div className="py-4">
            <CameraCapture onCapture={handleCameraCapture} disabled={isProcessing} />
          </div>
        )}

        {activeTab === 'scanner' && (
          <div className="p-8 text-center max-w-lg mx-auto">
            <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center text-slate-700 mx-auto mb-4">
              <FolderUp className="w-8 h-8" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">Watched Scanner Folder</h3>
            <p className="text-sm text-slate-500 mt-2 mb-6">
              Place newly scanned OMR files into <code className="bg-slate-100 px-2 py-0.5 rounded text-slate-800 font-mono">./scans_input</code>.
              Click below to automatically import and evaluate all pending sheets.
            </p>
            <button
              onClick={handleScanFolder}
              disabled={isProcessing}
              className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold rounded-xl shadow flex items-center gap-2 mx-auto"
            >
              <RefreshCw className={`w-4 h-4 ${isProcessing ? 'animate-spin' : ''}`} />
              Scan & Ingest Pending Files
            </button>
          </div>
        )}
      </div>

      {/* Processing Loader */}
      {isProcessing && (
        <div className="p-8 bg-indigo-50 border border-indigo-200 rounded-2xl flex items-center justify-center gap-4 text-indigo-900">
          <RefreshCw className="w-6 h-6 animate-spin text-indigo-600" />
          <div>
            <p className="font-bold">Evaluating Sheets in Batch...</p>
            <p className="text-xs text-indigo-700 mt-0.5">
              Normalizing perspective, decoding bubbles, running OCR verification, and scoring against answer keys.
            </p>
          </div>
        </div>
      )}

      {/* Batch Results & Progress Report */}
      {batchResults && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-100 pb-4">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Batch Processing Results</h2>
              <p className="text-xs text-slate-500 mt-0.5">Batch ID: {batchResults.batch_id}</p>
            </div>
            <div className="flex gap-3">
              <div className="px-4 py-2 bg-emerald-50 border border-emerald-200 rounded-xl text-center">
                <span className="text-xs font-semibold text-emerald-700 block">Auto Accepted</span>
                <span className="text-lg font-bold text-emerald-800">{batchResults.auto_accepted_count}</span>
              </div>
              <div className="px-4 py-2 bg-amber-50 border border-amber-200 rounded-xl text-center">
                <span className="text-xs font-semibold text-amber-700 block">Needs Review</span>
                <span className="text-lg font-bold text-amber-800">{batchResults.needs_review_count}</span>
              </div>
              <div className="px-4 py-2 bg-rose-50 border border-rose-200 rounded-xl text-center">
                <span className="text-xs font-semibold text-rose-700 block">Failed</span>
                <span className="text-lg font-bold text-rose-800">{batchResults.failed_count}</span>
              </div>
            </div>
          </div>

          {/* Per-File Status Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                <tr>
                  <th className="py-3 px-4">File / Page</th>
                  <th className="py-3 px-4">Student Roll</th>
                  <th className="py-3 px-4">Name</th>
                  <th className="py-3 px-4">Set</th>
                  <th className="py-3 px-4">Score</th>
                  <th className="py-3 px-4">Confidence</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {batchResults.results.map((item: any, idx: number) => (
                  <tr key={idx} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-3 px-4 font-medium text-slate-800">
                      {item.filename} {item.page_number > 1 && `(Page ${item.page_number})`}
                    </td>
                    <td className="py-3 px-4 font-mono font-medium text-slate-900">{item.roll_no || '—'}</td>
                    <td className="py-3 px-4 text-slate-800">{item.name || '—'}</td>
                    <td className="py-3 px-4">
                      {item.set_code ? (
                        <span className="px-2 py-0.5 bg-slate-100 rounded text-xs font-bold text-slate-700">
                          {item.set_code}
                        </span>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td className="py-3 px-4 font-semibold text-slate-900">
                      {item.total_score !== null && item.total_score !== undefined ? `${item.total_score} pts` : '—'}
                    </td>
                    <td className="py-3 px-4">
                      {item.confidence_score ? `${Math.round(item.confidence_score * 100)}%` : '—'}
                    </td>
                    <td className="py-3 px-4">
                      {item.status === 'done' && (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-emerald-100 text-emerald-800 rounded-full text-xs font-semibold">
                          <CheckCircle className="w-3.5 h-3.5" /> Auto Accepted
                        </span>
                      )}
                      {item.status === 'needs_review' && (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-amber-100 text-amber-800 rounded-full text-xs font-semibold">
                          <AlertTriangle className="w-3.5 h-3.5" /> Needs Review
                        </span>
                      )}
                      {item.status === 'failed' && (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-rose-100 text-rose-800 rounded-full text-xs font-semibold">
                          <XCircle className="w-3.5 h-3.5" /> Failed
                        </span>
                      )}
                      {item.review_reasons && item.review_reasons.length > 0 && (
                        <p className="text-xs text-amber-700 mt-1 max-w-xs truncate">
                          {item.review_reasons.join(', ')}
                        </p>
                      )}
                      {item.error_message && (
                        <p className="text-xs text-rose-700 mt-1 max-w-xs">{item.error_message}</p>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      {item.result_id && (
                        <button
                          onClick={() => onNavigateToVerify(item.result_id)}
                          className="px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded-lg text-xs font-semibold inline-flex items-center gap-1 transition-colors"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          {item.status === 'needs_review' ? 'Verify & Save' : 'View Record'}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
