import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { apiClient } from '@/api/client';
import { XrayTestSet, XrayConfig, Project, PaginatedResponse } from '@/types';
import { TkButton, TkCard } from '@takeoff-ui/react';
import { format } from 'date-fns';

export function TestSets() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(
    searchParams.get('project_id') ? Number(searchParams.get('project_id')) : null
  );
  const [xrayConfig, setXrayConfig] = useState<XrayConfig | null>(null);
  const [testSets, setTestSets] = useState<XrayTestSet[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [showSyncModal, setShowSyncModal] = useState(false);
  const [specificTestSetKeys, setSpecificTestSetKeys] = useState('');

  useEffect(() => {
    loadProjects();
  }, []);

  useEffect(() => {
    if (selectedProjectId) {
      loadXrayConfig();
      setSearchParams({ project_id: selectedProjectId.toString() });
    }
  }, [selectedProjectId, page, search]);

  const loadProjects = async () => {
    try {
      const data = await apiClient.getProjects({ page_size: 100 }) as PaginatedResponse<Project>;
      setProjects(data.items);

      // Auto-select first project if none selected
      if (!selectedProjectId && data.items.length > 0) {
        setSelectedProjectId(data.items[0].id);
      }
    } catch (error) {
      console.error('Failed to load projects:', error);
    }
  };

  const loadXrayConfig = async () => {
    if (!selectedProjectId) return;

    try {
      const config = await apiClient.getXrayConfig(selectedProjectId);
      setXrayConfig(config);
      // Only load test sets if config exists
      loadTestSets();
    } catch {
      setXrayConfig(null);
      setTestSets([]);
      setTotal(0);
    }
  };

  const loadTestSets = async () => {
    if (!selectedProjectId || !xrayConfig) return; // Ensure config exists before loading test sets

    setIsLoading(true);
    try {
      const data = await apiClient.getXrayTestSets({
        project_id: selectedProjectId,
        page,
        page_size: 12,
        search: search || undefined,
      });
      setTestSets(data.items);
      setTotal(data.total);
    } catch (error) {
      console.error('Failed to load test sets:', error);
      setTestSets([]);
      setTotal(0);
    } finally {
      setIsLoading(false);
    }
  };


  const handleSync = async (testSetKeys?: string[]) => {
    if (!selectedProjectId) return;

    setIsSyncing(true);
    setSyncMessage(null);
    setShowSyncModal(false);

    try {
      const result = await apiClient.syncTestSets(selectedProjectId, {
        force: true,
        test_set_keys: testSetKeys && testSetKeys.length > 0 ? testSetKeys : undefined,
      });

      // Show detailed message including debug info if no test sets found
      let message = result.message;
      if (result.debug_info && result.synced_count === 0) {
        message += ` (Found ${result.debug_info.test_sets_found} test sets in Xray)`;
      }
      if (result.errors && result.errors.length > 0) {
        message += ` Errors: ${result.errors.join(', ')}`;
      }

      setSyncMessage({
        type: result.success ? 'success' : 'error',
        text: message,
      });
      if (result.success || result.synced_count > 0) {
        await loadTestSets();
        await loadXrayConfig();
      }
    } catch (error) {
      setSyncMessage({
        type: 'error',
        text: error instanceof Error ? error.message : 'Sync failed',
      });
    } finally {
      setIsSyncing(false);
    }
  };

  const handleSyncSpecific = () => {
    const keys = specificTestSetKeys
      .split(/[,\s]+/)
      .map(k => k.trim())
      .filter(k => k.length > 0);

    if (keys.length > 0) {
      handleSync(keys);
      setSpecificTestSetKeys('');
    }
  };

  const getSyncStatusBadge = (status: string) => {
    switch (status) {
      case 'synced':
        return 'bg-green-100 text-green-700 border-green-200';
      case 'syncing':
        return 'bg-blue-100 text-blue-700 border-blue-200';
      case 'failed':
        return 'bg-red-100 text-red-700 border-red-200';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  const totalPages = Math.ceil(total / 12);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Test Sets</h1>
          <p className="text-slate-500 mt-1">Browse and execute Jira Xray test sets</p>
        </div>
        <div className="flex items-center gap-3">
          {xrayConfig && (
            <>
              <TkButton
                variant="secondary"
                label={isSyncing ? 'Syncing...' : 'Sync All'}
                disabled={isSyncing}
                onClick={() => handleSync()}
              />
              <TkButton
                variant="primary"
                label="Sync Specific Test Set"
                disabled={isSyncing}
                onClick={() => setShowSyncModal(true)}
              />
            </>
          )}
        </div>
      </div>

      {/* Project selector */}
      <div className="flex items-center gap-4">
        <div className="flex-1 max-w-xs">
          <label className="block text-sm font-medium text-slate-700 mb-2">Project</label>
          <select
            value={selectedProjectId || ''}
            onChange={(e) => {
              setSelectedProjectId(Number(e.target.value));
              setPage(1);
            }}
            className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-blue-500"
          >
            <option value="">Select a project</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
        </div>

        {selectedProjectId && (
          <div className="flex-1 max-w-md">
            <label className="block text-sm font-medium text-slate-700 mb-2">Search</label>
            <input
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder="Search test sets..."
              className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-slate-800 placeholder-slate-500 focus:outline-none focus:border-blue-500"
            />
          </div>
        )}
      </div>

      {/* Sync message */}
      {syncMessage && (
        <div className={`p-3 rounded-lg border ${syncMessage.type === 'success'
          ? 'bg-green-100 border-green-200 text-green-700'
          : 'bg-red-100 border-red-200 text-red-700'
          }`}>
          {syncMessage.text}
        </div>
      )}

      {/* Xray config status */}
      {selectedProjectId && !xrayConfig && !isLoading && (
        <TkCard>
          <div className="p-8 text-center bg-white border border-slate-200 rounded-lg">
            <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-slate-800 mb-2">Xray Not Configured</h3>
            <p className="text-slate-500 mb-6">Configure Xray integration to import test sets</p>
            <Link to={`/projects/${selectedProjectId}/settings`}>
              <TkButton variant="primary" label="Configure Xray" />
            </Link>
          </div>
        </TkCard>
      )}

      {/* Test sets grid */}
      {selectedProjectId && xrayConfig && (
        <>
          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
          ) : testSets.length > 0 ? (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {testSets.map((testSet) => (
                  <Link
                    key={testSet.id}
                    to={`/test-sets/${testSet.id}`}
                    className="block"
                  >
                    <TkCard>
                      <div className="p-6 card-hover rounded-lg bg-white border border-slate-200 shadow-sm">
                        <div className="flex items-start justify-between mb-3">
                          <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-indigo-500 rounded-lg flex items-center justify-center">
                            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                            </svg>
                          </div>
                          <span className={`px-2 py-0.5 text-xs font-medium rounded border ${getSyncStatusBadge(testSet.sync_status)}`}>
                            {testSet.sync_status}
                          </span>
                        </div>

                        <div className="mb-2">
                          <span className="text-xs font-mono text-slate-500">{testSet.xray_issue_key}</span>
                        </div>

                        <h3 className="text-lg font-semibold text-slate-800 mb-2 line-clamp-1">{testSet.name}</h3>
                        <p className="text-sm text-slate-500 line-clamp-2 mb-4">
                          {testSet.description || 'No description'}
                        </p>

                        {/* Labels */}
                        {testSet.labels.length > 0 && (
                          <div className="flex flex-wrap gap-1 mb-4">
                            {testSet.labels.slice(0, 3).map((label, i) => (
                              <span key={i} className="px-2 py-0.5 text-xs bg-slate-100 text-slate-600 rounded">
                                {label}
                              </span>
                            ))}
                            {testSet.labels.length > 3 && (
                              <span className="px-2 py-0.5 text-xs bg-slate-100 text-slate-600 rounded">
                                +{testSet.labels.length - 3}
                              </span>
                            )}
                          </div>
                        )}

                        <div className="pt-4 border-t border-slate-200 flex items-center justify-between text-sm">
                          <span className="text-slate-500">
                            {testSet.test_count} test{testSet.test_count !== 1 ? 's' : ''}
                          </span>
                          {testSet.last_synced_at && (
                            <span className="text-slate-500">
                              Synced {format(new Date(testSet.last_synced_at), 'MMM d')}
                            </span>
                          )}
                        </div>
                      </div>
                    </TkCard>
                  </Link>
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-center gap-2">
                  <TkButton
                    variant="secondary"
                    label="Previous"
                    disabled={page === 1}
                    onClick={() => setPage(p => p - 1)}
                  />
                  <span className="px-4 text-slate-500">
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
              <div className="p-12 text-center bg-white border border-slate-200 rounded-lg shadow-sm">
                <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-slate-800 mb-2">No Test Sets Found</h3>
                <p className="text-slate-500 mb-6">
                  {search
                    ? 'No test sets match your search'
                    : 'Sync test sets from Xray to get started'}
                </p>
                {!search && (
                  <div className="flex gap-2 justify-center">
                    <TkButton
                      variant="secondary"
                      label={isSyncing ? 'Syncing...' : 'Sync All'}
                      disabled={isSyncing}
                      onClick={() => handleSync()}
                    />
                    <TkButton
                      variant="primary"
                      label="Sync Specific Test Set"
                      disabled={isSyncing}
                      onClick={() => setShowSyncModal(true)}
                    />
                  </div>
                )}
              </div>
            </TkCard>
          )}
        </>
      )}

      {/* Sync Specific Test Set Modal */}
      {showSyncModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl border border-slate-200 p-6 w-full max-w-md shadow-xl animate-fade-in">
            <h3 className="text-lg font-semibold text-slate-800 mb-4">Sync Specific Test Sets</h3>
            <p className="text-sm text-slate-500 mb-4">
              Enter Jira issue keys for the test sets you want to sync (e.g., UOTP-1, UOTP-5).
              Separate multiple keys with commas or spaces.
            </p>
            <input
              type="text"
              value={specificTestSetKeys}
              onChange={(e) => setSpecificTestSetKeys(e.target.value)}
              placeholder="e.g., PROJ-1, PROJ-5, PROJ-10"
              className="w-full px-3 py-2 bg-slate-100 border border-slate-200 rounded-lg text-slate-800 placeholder-slate-500 focus:outline-none focus:border-blue-500 mb-4"
              autoFocus
            />
            <div className="flex justify-end gap-2">
              <TkButton
                variant="secondary"
                label="Cancel"
                onClick={() => {
                  setShowSyncModal(false);
                  setSpecificTestSetKeys('');
                }}
              />
              <TkButton
                variant="primary"
                label="Sync"
                disabled={!specificTestSetKeys.trim()}
                onClick={handleSyncSpecific}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
