// API Client for OMR Web Application

const API_BASE = '/api/v1';

export function getAuthToken(): string | null {
  return localStorage.getItem('omr_token');
}

export function setAuthToken(token: string): void {
  localStorage.setItem('omr_token', token);
}

export function clearAuthToken(): void {
  localStorage.removeItem('omr_token');
  localStorage.removeItem('omr_user');
}

export function getStoredUser(): any | null {
  const data = localStorage.getItem('omr_user');
  return data ? JSON.parse(data) : null;
}

export function setStoredUser(user: any): void {
  localStorage.setItem('omr_user', JSON.stringify(user));
}

async function request(endpoint: string, options: RequestInit = {}) {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Do not set Content-Type for FormData (browser sets boundary automatically)
  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    clearAuthToken();
    window.dispatchEvent(new Event('auth:unauthorized'));
    throw new Error('Session expired or unauthorized');
  }

  if (!res.ok) {
    let errDetail = 'Request failed';
    try {
      const errJson = await res.json();
      errDetail = errJson.detail || JSON.stringify(errJson);
    } catch {
      errDetail = await res.text();
    }
    throw new Error(errDetail);
  }

  // Handle binary/file downloads
  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('application/pdf') || contentType.includes('spreadsheet') || contentType.includes('text/csv')) {
    return res.blob();
  }

  return res.json();
}

export const api = {
  // Auth
  login: async (username: string, password: string) => {
    const data = await request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    setAuthToken(data.access_token);
    setStoredUser({ id: data.user_id, username: data.username, role: data.role });
    return data;
  },
  getMe: () => request('/auth/me'),

  // Exams
  listExams: (activeOnly = false) => request(`/exams?active_only=${activeOnly}`),
  getExam: (id: number) => request(`/exams/${id}`),
  createExam: (data: any) => request('/exams', { method: 'POST', body: JSON.stringify(data) }),
  updateExam: (id: number, data: any) => request(`/exams/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteExam: (id: number) => request(`/exams/${id}`, { method: 'DELETE' }),
  getAnswerKeys: (examId: number, setCode?: string) =>
    request(`/exams/${examId}/answer-keys${setCode ? `?set_code=${setCode}` : ''}`),
  saveAnswerKeys: (examId: number, data: any) =>
    request(`/exams/${examId}/answer-keys`, { method: 'POST', body: JSON.stringify(data) }),
  uploadAnswerKeysCsv: (examId: number, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return request(`/exams/${examId}/answer-keys/csv`, { method: 'POST', body: form });
  },

  // Scan & Ingest
  scanSingleSheet: (examId: number, file: File, setCode?: string) => {
    const form = new FormData();
    form.append('exam_id', examId.toString());
    if (setCode) form.append('set_code', setCode);
    form.append('file', file);
    return request('/scan', { method: 'POST', body: form });
  },
  scanBatchSheets: (examId: number, files: File[], setCode?: string) => {
    const form = new FormData();
    form.append('exam_id', examId.toString());
    if (setCode) form.append('set_code', setCode);
    files.forEach(f => form.append('files', f));
    return request('/scan/batch', { method: 'POST', body: form });
  },
  processScannerFolder: (examId: number) =>
    request(`/scan/scanner-folder?exam_id=${examId}`, { method: 'POST' }),

  // Results & Verification
  listResults: (examId?: number, status?: string) =>
    request(`/results?${examId ? `exam_id=${examId}&` : ''}${status ? `status=${status}` : ''}`),
  getResult: (id: number) => request(`/results/${id}`),
  confirmReview: (data: any) => request('/results/confirm', { method: 'POST', body: JSON.stringify(data) }),
  recheckResult: (id: number, stricterThreshold = true) =>
    request(`/results/${id}/recheck`, { method: 'POST', body: JSON.stringify({ stricter_threshold: stricterThreshold }) }),

  // Reports
  downloadExamPdf: (examId: number) => request(`/reports/exam/${examId}/pdf`),
  downloadExamExcel: (examId: number) => request(`/reports/exam/${examId}/excel`),
  downloadResultPdf: (resultId: number) => request(`/reports/result/${resultId}/pdf`),

  // Students
  searchStudents: (q?: string) => request(`/students${q ? `?q=${encodeURIComponent(q)}` : ''}`),
  getStudentProfile: (id: number) => request(`/students/${id}`),

  // Users & Admin
  listUsers: () => request('/users'),
  createUser: (data: any) => request('/users', { method: 'POST', body: JSON.stringify(data) }),
  updateUser: (id: number, data: any) => request(`/users/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  getAuditLogs: (limit = 50, offset = 0, action?: string) =>
    request(`/admin/audit-logs?limit=${limit}&offset=${offset}${action ? `&action=${action}` : ''}`),
  getSettings: () => request('/admin/settings'),
  updateSettings: (data: any) => request('/admin/settings', { method: 'PUT', body: JSON.stringify(data) }),
};
