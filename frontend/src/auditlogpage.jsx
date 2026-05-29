import React, { useState, useEffect } from 'react';
import axios from 'axios';

export default function AuditLogPage() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [recordIdFilter, setRecordIdFilter] = useState('');

  useEffect(() => {
    fetchLogs();
  }, [recordIdFilter]);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (recordIdFilter) {
        params.append('emission_record_id', recordIdFilter);
      }

      const response = await axios.get(
        `${import.meta.env.VITE_API_URL}/api/audit-logs/logs/?${params}`
      );

      setLogs(response.data);
    } catch (error) {
      console.error('Failed to fetch logs:', error);
    } finally {
      setLoading(false);
    }
  };

  const getActionBadge = (action) => {
    const styles = {
      created: 'bg-blue-100 text-blue-800',
      edited: 'bg-yellow-100 text-yellow-800',
      approved: 'bg-green-100 text-green-800',
      rejected: 'bg-red-100 text-red-800',
      validation_updated: 'bg-purple-100 text-purple-800',
      locked: 'bg-slate-100 text-slate-800',
    };

    return (
      <span className={`px-3 py-1 text-xs font-semibold rounded-full ${styles[action] || 'bg-slate-100 text-slate-800'}`}>
        {action.replace('_', ' ').toUpperCase()}
      </span>
    );
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold text-slate-900">Audit Logs</h2>
        <p className="text-slate-600 mt-1">
          Complete history of all changes to emission records
        </p>
      </div>

      {/* Filter */}
      <div className="bg-white rounded-lg shadow p-6">
        <label className="block text-sm font-semibold text-slate-900 mb-2">
          Filter by Record ID (optional)
        </label>
        <input
          type="number"
          value={recordIdFilter}
          onChange={(e) => setRecordIdFilter(e.target.value)}
          placeholder="Enter emission record ID..."
          className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
        />
      </div>

      {/* Logs Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-slate-600">Loading audit logs...</div>
        ) : logs.length === 0 ? (
          <div className="p-8 text-center text-slate-600">
            No audit logs found.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3 text-left font-semibold text-slate-900">Action</th>
                  <th className="px-6 py-3 text-left font-semibold text-slate-900">Field</th>
                  <th className="px-6 py-3 text-left font-semibold text-slate-900">Old Value</th>
                  <th className="px-6 py-3 text-left font-semibold text-slate-900">New Value</th>
                  <th className="px-6 py-3 text-left font-semibold text-slate-900">Changed By</th>
                  <th className="px-6 py-3 text-left font-semibold text-slate-900">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50">
                    <td className="px-6 py-4">
                      {getActionBadge(log.action)}
                    </td>
                    <td className="px-6 py-4 text-slate-700 font-mono text-xs">
                      {log.field_name || '-'}
                    </td>
                    <td className="px-6 py-4 text-slate-600 font-mono text-xs max-w-xs truncate">
                      {log.old_value || '-'}
                    </td>
                    <td className="px-6 py-4 text-slate-600 font-mono text-xs max-w-xs truncate">
                      {log.new_value || '-'}
                    </td>
                    <td className="px-6 py-4 text-slate-700">
                      {log.changed_by || 'System'}
                    </td>
                    <td className="px-6 py-4 text-slate-600 text-xs">
                      {formatDate(log.changed_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}