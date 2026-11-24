import React, { useState, useEffect } from 'react';
import { 
  Users, 
  Search, 
  CheckCircle, 
  AlertCircle, 
  FileText, 
  ExternalLink, 
  UserCheck 
} from 'lucide-react';
import { api } from '../api/client';

interface StudentsPageProps {
  onNavigateToResult: (resultId: number) => void;
  onNavigateToVerify: (resultId: number) => void;
}

export const StudentsPage: React.FC<StudentsPageProps> = ({ onNavigateToResult, onNavigateToVerify }) => {
  const [students, setStudents] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [selectedStudent, setSelectedStudent] = useState<any | null>(null);

  useEffect(() => {
    loadStudents();
  }, []);

  const loadStudents = async (query = '') => {
    setIsLoading(true);
    try {
      const data = await api.searchStudents(query);
      setStudents(data);
    } catch {
      setStudents([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    loadStudents(searchQuery);
  };

  const openStudentDetail = async (studentId: number) => {
    try {
      const data = await api.getStudentProfile(studentId);
      setSelectedStudent(data);
    } catch {
      // Ignore
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2.5">
            <Users className="w-6 h-6 text-indigo-600" />
            Student Master Database
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Search candidates by roll number, name, or phone number. Inspect dual-channel Bubble vs OCR values.
          </p>
        </div>

        {/* Live Search Form */}
        <form onSubmit={handleSearch} className="flex items-center gap-2 max-w-md w-full">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by Roll No, Name, or Mobile..."
              className="w-full pl-10 pr-4 py-2 text-xs font-medium rounded-xl border border-slate-200 bg-slate-50 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 bg-indigo-600 text-white rounded-xl text-xs font-semibold hover:bg-indigo-700 shadow-sm"
          >
            Search
          </button>
        </form>
      </div>

      {/* Students Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center p-16">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
          </div>
        ) : students.length === 0 ? (
          <div className="p-16 text-center">
            <Users className="w-10 h-10 text-slate-300 mx-auto mb-3" />
            <h4 className="text-sm font-bold text-slate-700">No Students Found</h4>
            <p className="text-xs text-slate-400 mt-1">
              Try searching with another keyword or scan new OMR answer sheets.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-50 border-b border-slate-200 uppercase font-bold text-slate-500">
                <tr>
                  <th className="px-5 py-3">Roll No</th>
                  <th className="px-5 py-3">Candidate Name</th>
                  <th className="px-5 py-3">Father's Name</th>
                  <th className="px-4 py-3">Mobile</th>
                  <th className="px-4 py-3">Class / DOB</th>
                  <th className="px-4 py-3 text-center">Verified</th>
                  <th className="px-5 py-3 text-right">Profile</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {students.map(s => (
                  <tr key={s.id} className="hover:bg-slate-50/75 transition-colors">
                    <td className="px-5 py-3 font-mono font-bold text-slate-900">
                      {s.roll_no || '-'}
                    </td>
                    <td className="px-5 py-3 font-semibold text-slate-800">
                      {s.name_final || s.name_bubble || '-'}
                    </td>
                    <td className="px-5 py-3 text-slate-600">
                      {s.father_name_final || s.father_name_bubble || '-'}
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-600">
                      {s.mobile_final || s.mobile_bubble || '-'}
                    </td>
                    <td className="px-4 py-3 text-slate-500">
                      {s.class_name_final || '-'} {s.dob_final ? `(${s.dob_final})` : ''}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {s.verified_flag ? (
                        <span className="inline-flex items-center gap-1 text-emerald-600 font-bold text-[11px]">
                          <CheckCircle className="w-3.5 h-3.5" /> Verified
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-amber-600 font-medium text-[11px]">
                          <AlertCircle className="w-3.5 h-3.5" /> Auto Decoded
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <button
                        onClick={() => openStudentDetail(s.id)}
                        className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-semibold"
                      >
                        View Profile
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Student Profile & Dual-Channel Comparison Modal */}
      {selectedStudent && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto border border-slate-200 shadow-2xl p-6 space-y-6 animate-in fade-in zoom-in-95 duration-150">
            
            {/* Header */}
            <div className="flex items-start justify-between border-b border-slate-100 pb-4">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-2xl bg-indigo-50 text-indigo-700 flex items-center justify-center font-bold text-lg">
                  {selectedStudent.name_final ? selectedStudent.name_final[0] : 'S'}
                </div>
                <div>
                  <h3 className="text-xl font-bold text-slate-900">
                    {selectedStudent.name_final || 'Candidate Profile'}
                  </h3>
                  <div className="flex items-center gap-3 text-xs text-slate-500 mt-0.5">
                    <span>Roll: <b className="text-slate-800">{selectedStudent.roll_no}</b></span>
                    <span>&bull;</span>
                    <span>Verified: <b className={selectedStudent.verified_flag ? 'text-emerald-600' : 'text-amber-600'}>
                      {selectedStudent.verified_flag ? 'YES' : 'PENDING'}
                    </b></span>
                  </div>
                </div>
              </div>

              <button
                onClick={() => setSelectedStudent(null)}
                className="w-8 h-8 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-600 flex items-center justify-center font-bold text-sm"
              >
                &times;
              </button>
            </div>

            {/* Bubble vs OCR Dual-Channel Audit */}
            <div className="space-y-3">
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
                <UserCheck className="w-4 h-4 text-indigo-600" />
                Dual-Channel Field Verification (Bubble vs Handwriting OCR)
              </h4>

              <div className="border border-slate-200 rounded-xl overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200 font-bold text-slate-600 uppercase">
                    <tr>
                      <th className="px-4 py-2.5">Field Name</th>
                      <th className="px-4 py-2.5 text-indigo-600">Bubble Value (Truth)</th>
                      <th className="px-4 py-2.5 text-purple-600">Handwriting OCR (Cross-Check)</th>
                      <th className="px-4 py-2.5 text-emerald-600">Final Decided</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {[
                      { name: 'Roll Number', b: selectedStudent.roll_no_bubble, o: selectedStudent.roll_no_ocr, f: selectedStudent.roll_no },
                      { name: 'Candidate Name', b: selectedStudent.name_bubble, o: selectedStudent.name_ocr, f: selectedStudent.name_final },
                      { name: "Father's Name", b: selectedStudent.father_name_bubble, o: selectedStudent.father_name_ocr, f: selectedStudent.father_name_final },
                      { name: 'Mobile', b: selectedStudent.mobile_bubble, o: selectedStudent.mobile_ocr, f: selectedStudent.mobile_final },
                      { name: 'Date of Birth', b: selectedStudent.dob_bubble, o: selectedStudent.dob_ocr, f: selectedStudent.dob_final },
                      { name: 'Class', b: selectedStudent.class_name_bubble, o: selectedStudent.class_name_ocr, f: selectedStudent.class_name_final },
                    ].map((row, idx) => (
                      <tr key={idx} className="hover:bg-slate-50/50">
                        <td className="px-4 py-2.5 font-semibold text-slate-700">{row.name}</td>
                        <td className="px-4 py-2.5 font-mono text-indigo-700 font-semibold">{row.b || '-'}</td>
                        <td className="px-4 py-2.5 font-mono text-purple-700 font-semibold">{row.o || '-'}</td>
                        <td className="px-4 py-2.5 font-mono text-emerald-700 font-bold">{row.f || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Exam Attempts & Score History */}
            <div className="space-y-3">
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
                <FileText className="w-4 h-4 text-indigo-600" />
                Exam Attempts & Results
              </h4>

              {(selectedStudent.results || []).length === 0 ? (
                <div className="p-4 bg-slate-50 rounded-xl text-center text-xs text-slate-400">
                  No exam results registered for this student yet.
                </div>
              ) : (
                <div className="space-y-2">
                  {selectedStudent.results.map((res: any) => (
                    <div
                      key={res.id}
                      className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 flex items-center justify-between"
                    >
                      <div>
                        <span className="font-bold text-sm text-slate-900 block">
                          {res.exam_name || 'Standard Exam'}
                        </span>
                        <div className="flex items-center gap-2 text-xs text-slate-500 mt-0.5">
                          <span>Set: <b>{res.set_code}</b></span>
                          <span>&bull;</span>
                          <span>Score: <b className="text-indigo-600 font-bold">{res.total_score}</b></span>
                          <span>&bull;</span>
                          <span>Status: <b>{res.status}</b></span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        {res.status === 'NEEDS_REVIEW' && (
                          <button
                            onClick={() => {
                              setSelectedStudent(null);
                              onNavigateToVerify(res.id);
                            }}
                            className="px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white rounded-lg text-xs font-semibold"
                          >
                            Verify
                          </button>
                        )}
                        <button
                          onClick={() => {
                            setSelectedStudent(null);
                            onNavigateToResult(res.id);
                          }}
                          className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold flex items-center gap-1"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                          View Result
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="flex justify-end border-t border-slate-100 pt-4">
              <button
                onClick={() => setSelectedStudent(null)}
                className="px-4 py-2 bg-slate-100 text-slate-700 rounded-xl text-xs font-semibold hover:bg-slate-200"
              >
                Close
              </button>
            </div>

          </div>
        </div>
      )}
    </div>
  );
};

export default StudentsPage;
