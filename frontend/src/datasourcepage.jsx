import React, { useState, useEffect } from 'react';
import axios from 'axios';

export default function DataSourcesPage() {
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSources();
  }, []);

  const fetchSources = async () => {
    setLoading(true);
    try {
      const response = await axios.get(
        `${import.meta.env.VITE_API_URL}/api/sources/`
      );
      setSources(response.data);
    } catch (error) {
      console.error('Failed to fetch sources:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const styles = {
      pending: 'bg-yellow-100 text-yellow-800',
      completed: 'bg-green-100 text-green-800',
      failed: 'bg-red-100 text-red-800',
    };
    const labels = {
      pending: 'Processing',
      completed: 'Complete',
      failed: 'Failed',
    };
    return (
      <span className={`px-3 py-1 text-xs font-semibold rounded-full ${styles[status]}`}>
        {labels[status]}
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
        <h2 className="text-3xl font-bold text-slate-900">Data Sources</h2>
        <p className="text-slate-600 mt-1">
          History of all uploaded files and ingestion status
        </p>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-slate-600">Loading sources...</div>
        ) : sources.length === 0 ? (
          <div className="p-8 text-center text-slate-600">
            No data sources yet. Start by uploading a file.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3 text-left font-semibold text-slate-900">File Name</th>
                  <th className="px-6 py-3 text-left font-semibold text-slate-900">Type</th>
                  <th className="px-6 py-3 text-left font-semibold text-slate-900">Status</th>
                  <th className="px-6 py-3 text-center font-semibold text-slate-900">Raw Records</th>
                  <th className="px-6 py-3 text-center font-semibold text-slate-900">Emission Records</th>
                  <th className="px-6 py-3 text-left font-semibold text-slate-900">Uploaded</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {sources.map((source) => (
                  <tr key={source.id} className="hover:bg-slate-50">
                    <td className="px-6 py-4 font-medium text-slate-900">
                      {source.file_name}
                    </td>
                    <td className="px-6 py-4">
                      <span className="inline-block px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-semibold">
                        {source.source_type.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {getStatusBadge(source.ingestion_status)}
                    </td>
                    <td className="px-6 py-4 text-center text-slate-900 font-medium">
                      {source.raw_record_count}
                    </td>
                    <td className="px-6 py-4 text-center text-slate-900 font-medium">
                      {source.emission_record_count}
                    </td>
                    <td className="px-6 py-4 text-slate-600 text-xs">
                      {formatDate(source.uploaded_at)}
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