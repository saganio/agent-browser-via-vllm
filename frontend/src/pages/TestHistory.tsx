import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiClient } from '@/api/client';
import { TestRun, PaginatedResponse, TestStatus } from '@/types';
import { TkButton, TkCard } from '@takeoff-ui/react';
import { format } from 'date-fns';

export function TestHistory() {
  const [testRuns, setTestRuns] = useState<TestRun[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<TestStatus | ''>('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadTestRuns();
  }, [page, statusFilter]);

  const loadTestRuns = async () => {
    setIsLoading(true);
    try {
      const data = await apiClient.getTestRuns({
        page,
        page_size: 20,
        status: statusFilter || undefined,
      }) as PaginatedResponse<TestRun>;
      setTestRuns(data.items);
      setTotal(data.total);
    } catch (error) {
      console.error('Failed to load test runs:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'completed': return 'status-completed';
      case 'failed': return 'status-failed';
      case 'running': return 'status-running';
      case 'pending': return 'status-pending';
      default: return 'status-cancelled';
    }
  };

  const formatDuration = (ms: number | null) => {
    if (!ms) return '-';
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  const totalPages = Math.ceil(total / 20);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Test History</h1>
          <p className="text-slate-500 mt-1">View all past test executions</p>
        </div>
        <Link to="/tests/run">
          <TkButton variant="primary" label="Run New Test" />
        </Link>
      </div>

      {/* Filters */}
      <div className="flex gap-2">
        {(['', 'completed', 'failed', 'running', 'pending', 'cancelled'] as const).map((status) => (
          <button
            key={status}
            onClick={() => {
              setStatusFilter(status);
              setPage(1);
            }}
            className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
              statusFilter === status
                ? 'bg-blue-500 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            {status || 'All'}
          </button>
        ))}
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : testRuns.length > 0 ? (
        <>
          <TkCard>
            <div className="overflow-x-auto bg-white rounded-lg border border-slate-200">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50">
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-600">ID</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-600">Command</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-600">Project</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-600">Status</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-600">Duration</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-600">Triggered</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-600">Date</th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-slate-600">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {testRuns.map((run) => (
                    <tr key={run.id} className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="py-3 px-4">
                        <span className="text-sm font-mono text-slate-600">#{run.id}</span>
                      </td>
                      <td className="py-3 px-4">
                        <p className="text-sm text-slate-700 truncate max-w-xs" title={run.command}>
                          {run.command.slice(0, 50)}{run.command.length > 50 ? '...' : ''}
                        </p>
                      </td>
                      <td className="py-3 px-4">
                        <span className="text-sm text-slate-500">
                          {run.project_name || `Project #${run.project_id}`}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-0.5 text-xs font-medium rounded ${getStatusBadgeClass(run.status)}`}>
                          {run.status}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span className="text-sm text-slate-500">{formatDuration(run.duration_ms)}</span>
                      </td>
                      <td className="py-3 px-4">
                        <span className="text-sm text-slate-500">{run.trigger_type}</span>
                      </td>
                      <td className="py-3 px-4">
                        <span className="text-sm text-slate-500">
                          {format(new Date(run.created_at), 'MMM d, HH:mm')}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Link
                          to={`/tests/${run.id}`}
                          className="text-sm text-blue-600 hover:text-blue-700"
                        >
                          View
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </TkCard>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <TkButton
                variant="secondary"
                label="Previous"
                disabled={page === 1}
                onClick={() => setPage(p => p - 1)}
              />
              <span className="px-4 text-slate-600">
                Page {page} of {totalPages}
              </span>
              <TkButton
                variant="secondary"
                label="Next"
                disabled={page === totalPages}
                onClick={() => setPage(p => p + 1)}
              />
            </div>
          )}
        </>
      ) : (
        <TkCard>
          <div className="p-12 text-center bg-white rounded-lg border border-slate-200">
            <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-slate-800 mb-2">No test runs yet</h3>
            <p className="text-slate-500 mb-6">Run your first test to see the history here</p>
            <Link to="/tests/run">
              <TkButton variant="primary" label="Run Test" />
            </Link>
          </div>
        </TkCard>
      )}
    </div>
  );
}
