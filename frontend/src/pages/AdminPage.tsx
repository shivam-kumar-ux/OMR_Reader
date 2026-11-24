import React, { useState, useEffect } from 'react';
import { 
  ShieldAlert, 
  Users, 
  Sliders, 
  History, 
  Plus, 
  Check, 
  Save, 
  RefreshCw
} from 'lucide-react';
import { api } from '../api/client';

export const AdminPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'users' | 'audit' | 'settings'>('users');
  
  // Users state
  const [users, setUsers] = useState<any[]>([]);
  const [newUsername, setNewUsername] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newRole, setNewRole] = useState('Operator');
  const [userMsg, setUserMsg] = useState<string | null>(null);

  // Audit state
  const [logs, setLogs] = useState<any[]>([]);
  const [logsTotal, setLogsTotal] = useState(0);

  // Settings state
  const [fillThreshold, setFillThreshold] = useState<number>(0.45);
  const [uncertainLow, setUncertainLow] = useState<number>(0.30);
  const [ocrSimilarity, setOcrSimilarity] = useState<number>(0.75);
  const [settingsSaved, setSettingsSaved] = useState(false);

  useEffect(() => {
    if (activeTab === 'users') loadUsers();
    if (activeTab === 'audit') loadAuditLogs();
    if (activeTab === 'settings') loadSettings();
  }, [activeTab]);

  const loadUsers = async () => {
    try {
      const data = await api.listUsers();
      setUsers(data);
    } catch {
      // Ignore
    }
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setUserMsg(null);
    try {
      await api.createUser({
        username: newUsername,
        email: newEmail,
        password: newPassword,
        role: newRole,
      });
      setUserMsg('User created successfully!');
      setNewUsername('');
      setNewEmail('');
      setNewPassword('');
      loadUsers();
    } catch (err: any) {
      setUserMsg(`Error: ${err.message}`);
    }
  };

  const loadAuditLogs = async () => {
    try {
      const data = await api.getAuditLogs(100, 0);
      setLogs(data.items || []);
      setLogsTotal(data.total || 0);
    } catch {
      // Ignore
    }
  };

  const loadSettings = async () => {
    try {
      const data = await api.getSettings();
      if (data.BUBBLE_FILL_THRESHOLD !== undefined) setFillThreshold(data.BUBBLE_FILL_THRESHOLD);
      if (data.BUBBLE_UNCERTAIN_LOW !== undefined) setUncertainLow(data.BUBBLE_UNCERTAIN_LOW);
      if (data.OCR_NAME_SIMILARITY_THRESHOLD !== undefined) setOcrSimilarity(data.OCR_NAME_SIMILARITY_THRESHOLD);
    } catch {
      // Ignore
    }
  };

  const handleSaveSettings = async () => {
    setSettingsSaved(false);
    try {
      await api.updateSettings({
        BUBBLE_FILL_THRESHOLD: Number(fillThreshold),
        BUBBLE_UNCERTAIN_LOW: Number(uncertainLow),
        OCR_NAME_SIMILARITY_THRESHOLD: Number(ocrSimilarity),
      });
      setSettingsSaved(true);
      setTimeout(() => setSettingsSaved(false), 3000);
    } catch (err: any) {
      alert(`Failed to save settings: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2.5">
            <ShieldAlert className="w-6 h-6 text-indigo-600" />
            Administration & System Auditing
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Manage user accounts, inspect immutable audit trails, and configure live OMR decision thresholds.
          </p>
        </div>

        {/* Tab Buttons */}
        <div className="flex bg-slate-100 p-1 rounded-xl">
          <button
            onClick={() => setActiveTab('users')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
              activeTab === 'users' ? 'bg-white text-indigo-700 shadow-xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Users className="w-3.5 h-3.5" />
            Users
          </button>
          <button
            onClick={() => setActiveTab('audit')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
              activeTab === 'audit' ? 'bg-white text-indigo-700 shadow-xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <History className="w-3.5 h-3.5" />
            Audit Logs
          </button>
          <button
            onClick={() => setActiveTab('settings')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
              activeTab === 'settings' ? 'bg-white text-indigo-700 shadow-xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Sliders className="w-3.5 h-3.5" />
            Thresholds
          </button>
        </div>
      </div>

      {/* Tab 1: Users */}
      {activeTab === 'users' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Create User Form */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Plus className="w-4 h-4 text-indigo-600" />
              Create New Account
            </h3>

            {userMsg && (
              <div className="p-3 bg-indigo-50 text-indigo-700 rounded-xl text-xs font-semibold">
                {userMsg}
              </div>
            )}

            <form onSubmit={handleCreateUser} className="space-y-3">
              <div>
                <label className="text-xs font-bold text-slate-600 uppercase block mb-1">Username</label>
                <input
                  type="text"
                  required
                  value={newUsername}
                  onChange={(e) => setNewUsername(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-xl border border-slate-200 bg-slate-50 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-600 uppercase block mb-1">Email</label>
                <input
                  type="email"
                  required
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-xl border border-slate-200 bg-slate-50 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-600 uppercase block mb-1">Password</label>
                <input
                  type="password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-xl border border-slate-200 bg-slate-50 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-600 uppercase block mb-1">Role</label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-xl border border-slate-200 bg-slate-50 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="Operator">Operator</option>
                  <option value="Admin">Admin</option>
                </select>
              </div>

              <button
                type="submit"
                className="w-full py-2.5 bg-indigo-600 text-white rounded-xl text-xs font-bold hover:bg-indigo-700 shadow-sm"
              >
                Create Account
              </button>
            </form>
          </div>

          {/* User List */}
          <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
              <span className="text-xs font-bold text-slate-700 uppercase">Registered System Users</span>
              <button onClick={loadUsers} className="text-slate-400 hover:text-slate-600">
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-600">
                <thead className="bg-slate-50/50 uppercase font-bold text-slate-500 border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-2.5">User</th>
                    <th className="px-4 py-2.5">Email</th>
                    <th className="px-4 py-2.5 text-center">Role</th>
                    <th className="px-4 py-2.5 text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {users.map(u => (
                    <tr key={u.id} className="hover:bg-slate-50">
                      <td className="px-4 py-3 font-bold text-slate-900">{u.username}</td>
                      <td className="px-4 py-3 text-slate-600">{u.email}</td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          u.role === 'Admin' ? 'bg-purple-100 text-purple-700' : 'bg-slate-100 text-slate-700'
                        }`}>
                          {u.role}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="text-emerald-600 font-semibold text-[11px]">Active</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Audit Logs */}
      {activeTab === 'audit' && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
            <span className="text-xs font-bold text-slate-700 uppercase">
              System Audit Trails ({logsTotal} Events Logged)
            </span>
            <button onClick={loadAuditLogs} className="text-slate-400 hover:text-slate-600">
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-50/50 uppercase font-bold text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-2.5">Timestamp</th>
                  <th className="px-4 py-2.5">Action</th>
                  <th className="px-4 py-2.5">Entity</th>
                  <th className="px-4 py-2.5">Changes / Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
                {logs.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="p-8 text-center text-slate-400 font-sans">
                      No audit events recorded yet.
                    </td>
                  </tr>
                ) : (
                  logs.map(log => (
                    <tr key={log.id} className="hover:bg-slate-50">
                      <td className="px-4 py-2.5 text-slate-500 whitespace-nowrap">
                        {log.timestamp ? new Date(log.timestamp).toLocaleString() : '-'}
                      </td>
                      <td className="px-4 py-2.5 font-bold text-indigo-700">
                        {log.action}
                      </td>
                      <td className="px-4 py-2.5 text-slate-700 font-semibold">
                        {log.entity_type} #{log.entity_id}
                      </td>
                      <td className="px-4 py-2.5 text-slate-600 truncate max-w-md font-mono text-[10px]">
                        {log.new_values || log.old_values || '-'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 3: System Thresholds */}
      {activeTab === 'settings' && (
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm max-w-2xl space-y-6">
          <div>
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Sliders className="w-5 h-5 text-indigo-600" />
              Runtime OMR Recognition Parameters
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              Adjust bubble shade decision thresholds and OCR cross-check tolerances without restarting the server.
            </p>
          </div>

          {settingsSaved && (
            <div className="p-3 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-xl text-xs font-semibold flex items-center gap-2">
              <Check className="w-4 h-4 text-emerald-600" />
              Thresholds successfully updated and applied in runtime memory.
            </div>
          )}

          <div className="space-y-5">
            <div>
              <div className="flex justify-between text-xs font-bold text-slate-700 mb-1.5">
                <span>Bubble Fill Ratio Threshold (FILLED vs EMPTY)</span>
                <span className="font-mono text-indigo-600">{(fillThreshold * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="0.30"
                max="0.70"
                step="0.01"
                value={fillThreshold}
                onChange={(e) => setFillThreshold(parseFloat(e.target.value))}
                className="w-full accent-indigo-600"
              />
              <span className="text-[11px] text-slate-400 block mt-1">
                Bubbles with fill ratio above this mark are classified as FILLED. Recommended: 45%.
              </span>
            </div>

            <div>
              <div className="flex justify-between text-xs font-bold text-slate-700 mb-1.5">
                <span>Bubble Uncertain Lower Bound</span>
                <span className="font-mono text-amber-600">{(uncertainLow * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="0.15"
                max="0.40"
                step="0.01"
                value={uncertainLow}
                onChange={(e) => setUncertainLow(parseFloat(e.target.value))}
                className="w-full accent-amber-500"
              />
              <span className="text-[11px] text-slate-400 block mt-1">
                Bubbles between this bound and the fill threshold are flagged UNCERTAIN and sent to Review. Recommended: 30%.
              </span>
            </div>

            <div>
              <div className="flex justify-between text-xs font-bold text-slate-700 mb-1.5">
                <span>Name OCR Similarity Acceptance Threshold</span>
                <span className="font-mono text-purple-600">{(ocrSimilarity * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="0.50"
                max="0.95"
                step="0.05"
                value={ocrSimilarity}
                onChange={(e) => setOcrSimilarity(parseFloat(e.target.value))}
                className="w-full accent-purple-600"
              />
              <span className="text-[11px] text-slate-400 block mt-1">
                Candidate names with OCR cross-check similarity below this ratio trigger NEEDS_REVIEW. Recommended: 75%.
              </span>
            </div>

            <div className="pt-4 border-t border-slate-100 flex justify-end">
              <button
                onClick={handleSaveSettings}
                className="px-5 py-2.5 bg-indigo-600 text-white rounded-xl text-xs font-bold hover:bg-indigo-700 flex items-center gap-2 shadow-sm"
              >
                <Save className="w-4 h-4" />
                Save Threshold Parameters
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminPage;
