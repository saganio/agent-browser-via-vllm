import { useState, useEffect } from 'react';
import { apiClient } from '@/api/client';
import { XrayConfig, XrayConfigCreate, XrayInstanceType, TestConnectionResponse, XrayDebugInfo } from '@/types';
import { TkButton, TkCard } from '@takeoff-ui/react';

interface XrayConfigProps {
  projectId: number;
  onConfigChange?: () => void;
}

export function XrayConfigComponent({ projectId, onConfigChange }: XrayConfigProps) {
  const [config, setConfig] = useState<XrayConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [isDebugging, setIsDebugging] = useState(false);
  const [testResult, setTestResult] = useState<TestConnectionResponse | null>(null);
  const [debugInfo, setDebugInfo] = useState<XrayDebugInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [instanceType, setInstanceType] = useState<XrayInstanceType>('cloud');
  const [baseUrl, setBaseUrl] = useState('https://xray.cloud.getxray.app');
  const [clientId, setClientId] = useState('');
  const [clientSecret, setClientSecret] = useState('');
  const [username, setUsername] = useState('');
  const [apiToken, setApiToken] = useState('');
  const [jiraProjectKey, setJiraProjectKey] = useState('');
  const [autoSync, setAutoSync] = useState(false);
  const [autoExport, setAutoExport] = useState(true);
  const [syncInterval, setSyncInterval] = useState(60);

  useEffect(() => {
    loadConfig();
  }, [projectId]);

  const loadConfig = async () => {
    setIsLoading(true);
    try {
      const data = await apiClient.getXrayConfig(projectId);
      setConfig(data);
      populateForm(data);
    } catch {
      setConfig(null);
      resetForm();
    } finally {
      setIsLoading(false);
    }
  };

  const populateForm = (data: XrayConfig) => {
    setInstanceType(data.instance_type);
    setBaseUrl(data.base_url);
    setJiraProjectKey(data.jira_project_key);
    setAutoSync(data.auto_sync);
    setAutoExport(data.auto_export);
    setSyncInterval(data.sync_interval_minutes);
    // Don't populate credentials for security
  };

  const resetForm = () => {
    setInstanceType('cloud');
    setBaseUrl('https://xray.cloud.getxray.app');
    setClientId('');
    setClientSecret('');
    setUsername('');
    setApiToken('');
    setJiraProjectKey('');
    setAutoSync(false);
    setAutoExport(true);
    setSyncInterval(60);
  };

  const handleTestConnection = async () => {
    setIsTesting(true);
    setTestResult(null);
    setError(null);

    try {
      const result = await apiClient.testXrayConnection({
        instance_type: instanceType,
        base_url: baseUrl,
        client_id: instanceType === 'cloud' ? clientId : undefined,
        client_secret: instanceType === 'cloud' ? clientSecret : undefined,
        username: instanceType === 'server' ? username : undefined,
        api_token: instanceType === 'server' ? apiToken : undefined,
        jira_project_key: jiraProjectKey,
      });
      setTestResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Connection test failed');
    } finally {
      setIsTesting(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    setError(null);

    try {
      if (config) {
        // Update existing config
        await apiClient.updateXrayConfig(projectId, {
          instance_type: instanceType,
          base_url: baseUrl,
          client_id: instanceType === 'cloud' && clientId ? clientId : undefined,
          client_secret: instanceType === 'cloud' && clientSecret ? clientSecret : undefined,
          username: instanceType === 'server' && username ? username : undefined,
          api_token: instanceType === 'server' && apiToken ? apiToken : undefined,
          jira_project_key: jiraProjectKey,
          auto_sync: autoSync,
          auto_export: autoExport,
          sync_interval_minutes: syncInterval,
        });
      } else {
        // Create new config
        const createData: XrayConfigCreate = {
          project_id: projectId,
          instance_type: instanceType,
          base_url: baseUrl,
          jira_project_key: jiraProjectKey,
          auto_sync: autoSync,
          auto_export: autoExport,
          sync_interval_minutes: syncInterval,
        };

        if (instanceType === 'cloud') {
          createData.client_id = clientId;
          createData.client_secret = clientSecret;
        } else {
          createData.username = username;
          createData.api_token = apiToken;
        }

        await apiClient.createXrayConfig(createData);
      }

      await loadConfig();
      setIsEditing(false);
      onConfigChange?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save configuration');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete the Xray configuration?')) return;

    try {
      await apiClient.deleteXrayConfig(projectId);
      setConfig(null);
      resetForm();
      onConfigChange?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete configuration');
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-32">
        <div className="w-6 h-6 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <TkCard>
      <div className="p-6 bg-white border border-slate-200 rounded-lg shadow-sm">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-semibold text-slate-800">Jira Xray Integration</h3>
            <p className="text-sm text-slate-500 mt-1">
              Connect to Xray to import and execute test sets
            </p>
          </div>
          {config && !isEditing && (
            <div className="flex items-center gap-2">
              <TkButton
                variant="secondary"
                label="Edit"
                onClick={() => setIsEditing(true)}
              />
              <button
                onClick={handleDelete}
                className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                title="Delete configuration"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          )}
        </div>

        {error && (
          <div className="p-3 mb-4 bg-red-100 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        {testResult && (
          <div className={`p-3 mb-4 rounded-lg border text-sm ${
            testResult.success 
              ? 'bg-green-100 border-green-200 text-green-700' 
              : 'bg-red-100 border-red-200 text-red-700'
          }`}>
            {testResult.message}
            {testResult.xray_version && (
              <span className="ml-2">({testResult.xray_version})</span>
            )}
          </div>
        )}

        {config && !isEditing ? (
          // Display mode
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-slate-500">Instance Type</p>
                <p className="text-slate-800 font-medium capitalize">{config.instance_type}</p>
              </div>
              <div>
                <p className="text-sm text-slate-500">Jira Project Key</p>
                <p className="text-slate-800 font-medium">{config.jira_project_key}</p>
              </div>
              <div>
                <p className="text-sm text-slate-500">Base URL</p>
                <p className="text-slate-800 font-medium truncate">{config.base_url}</p>
              </div>
              <div>
                <p className="text-sm text-slate-500">Credentials</p>
                <p className="text-slate-800 font-medium">
                  {config.has_cloud_credentials || config.has_server_credentials ? '✓ Configured' : '✗ Not set'}
                </p>
              </div>
            </div>

            <div className="pt-4 border-t border-slate-200">
              <div className="grid grid-cols-3 gap-4">
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${config.auto_sync ? 'bg-green-500' : 'bg-slate-300'}`}></span>
                  <span className="text-sm text-slate-600">Auto Sync</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${config.auto_export ? 'bg-green-500' : 'bg-slate-300'}`}></span>
                  <span className="text-sm text-slate-600">Auto Export</span>
                </div>
                <div>
                  <span className="text-sm text-slate-600">Sync: every {config.sync_interval_minutes}m</span>
                </div>
              </div>
            </div>

            {config.last_sync_at && (
              <div className="pt-4 border-t border-slate-200">
                <p className="text-sm text-slate-500">
                  Last sync: {new Date(config.last_sync_at).toLocaleString()}
                  {config.last_sync_status && (
                    <span className={`ml-2 px-2 py-0.5 text-xs rounded ${
                      config.last_sync_status === 'synced' 
                        ? 'bg-green-100 text-green-700' 
                        : config.last_sync_status === 'failed'
                        ? 'bg-red-100 text-red-700'
                        : 'bg-slate-100 text-slate-700'
                    }`}>
                      {config.last_sync_status}
                    </span>
                  )}
                </p>
              </div>
            )}

            {/* Debug button */}
            <div className="pt-4 border-t border-slate-200">
              <TkButton
                variant="secondary"
                label={isDebugging ? 'Debugging...' : 'Debug Connection'}
                disabled={isDebugging}
                onClick={async () => {
                  setIsDebugging(true);
                  setDebugInfo(null);
                  try {
                    const info = await apiClient.debugXrayConnection(projectId);
                    setDebugInfo(info);
                  } catch (err) {
                    setError(err instanceof Error ? err.message : 'Debug failed');
                  } finally {
                    setIsDebugging(false);
                  }
                }}
              />
              {debugInfo && (
                <div className="mt-4 p-4 bg-slate-100 rounded-lg text-sm font-mono overflow-auto max-h-64">
                  <pre className="text-slate-700 whitespace-pre-wrap">
                    {JSON.stringify(debugInfo, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        ) : (
          // Edit/Create mode
          <div className="space-y-4">
            {/* Instance Type */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Instance Type</label>
              <div className="flex gap-4">
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="instanceType"
                    value="cloud"
                    checked={instanceType === 'cloud'}
                    onChange={() => {
                      setInstanceType('cloud');
                      setBaseUrl('https://xray.cloud.getxray.app');
                    }}
                    className="text-blue-500"
                  />
                  <span className="text-slate-700">Xray Cloud</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="instanceType"
                    value="server"
                    checked={instanceType === 'server'}
                    onChange={() => {
                      setInstanceType('server');
                      setBaseUrl('');
                    }}
                    className="text-blue-500"
                  />
                  <span className="text-slate-700">Xray Server/DC</span>
                </label>
              </div>
            </div>

            {/* Base URL */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">
                {instanceType === 'cloud' ? 'Xray Cloud URL' : 'Jira Server URL'}
              </label>
              <input
                type="text"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder={instanceType === 'cloud' ? 'https://xray.cloud.getxray.app' : 'https://jira.your-company.com'}
                className="w-full px-3 py-2 bg-slate-100 border border-slate-200 rounded-lg text-slate-800 placeholder-slate-500 focus:outline-none focus:border-blue-500"
              />
            </div>

            {/* Jira Project Key */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Jira Project Key</label>
              <input
                type="text"
                value={jiraProjectKey}
                onChange={(e) => setJiraProjectKey(e.target.value.toUpperCase())}
                placeholder="PROJ"
                className="w-full px-3 py-2 bg-slate-100 border border-slate-200 rounded-lg text-slate-800 placeholder-slate-500 focus:outline-none focus:border-blue-500"
              />
            </div>

            {/* Cloud credentials */}
            {instanceType === 'cloud' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">Client ID</label>
                  <input
                    type="text"
                    value={clientId}
                    onChange={(e) => setClientId(e.target.value)}
                    placeholder="Your Xray Cloud Client ID"
                    className="w-full px-3 py-2 bg-slate-100 border border-slate-200 rounded-lg text-slate-800 placeholder-slate-500 focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">Client Secret</label>
                  <input
                    type="password"
                    value={clientSecret}
                    onChange={(e) => setClientSecret(e.target.value)}
                    placeholder="Your Xray Cloud Client Secret"
                    className="w-full px-3 py-2 bg-slate-100 border border-slate-200 rounded-lg text-slate-800 placeholder-slate-500 focus:outline-none focus:border-blue-500"
                  />
                </div>
              </>
            )}

            {/* Server credentials */}
            {instanceType === 'server' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">Username</label>
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="Your Jira username"
                    className="w-full px-3 py-2 bg-slate-100 border border-slate-200 rounded-lg text-slate-800 placeholder-slate-500 focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">API Token / PAT</label>
                  <input
                    type="password"
                    value={apiToken}
                    onChange={(e) => setApiToken(e.target.value)}
                    placeholder="Personal Access Token"
                    className="w-full px-3 py-2 bg-slate-100 border border-slate-200 rounded-lg text-slate-800 placeholder-slate-500 focus:outline-none focus:border-blue-500"
                  />
                </div>
              </>
            )}

            {/* Options */}
            <div className="pt-4 border-t border-slate-200">
              <div className="space-y-3">
                <label className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={autoSync}
                    onChange={(e) => setAutoSync(e.target.checked)}
                    className="w-4 h-4 rounded border-slate-300 text-blue-500 focus:ring-blue-500"
                  />
                  <span className="text-sm text-slate-700">Auto-sync test sets periodically</span>
                </label>
                
                <label className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={autoExport}
                    onChange={(e) => setAutoExport(e.target.checked)}
                    className="w-4 h-4 rounded border-slate-300 text-blue-500 focus:ring-blue-500"
                  />
                  <span className="text-sm text-slate-700">Auto-export results to Xray after execution</span>
                </label>

                {autoSync && (
                  <div className="ml-7">
                    <label className="block text-xs text-slate-500 mb-1">Sync interval (minutes)</label>
                    <input
                      type="number"
                      value={syncInterval}
                      onChange={(e) => setSyncInterval(Math.max(5, Math.min(1440, Number(e.target.value))))}
                      min={5}
                      max={1440}
                      className="w-24 px-2 py-1 bg-slate-100 border border-slate-200 rounded text-slate-800 text-sm focus:outline-none focus:border-blue-500"
                    />
                  </div>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="pt-4 border-t border-slate-200 flex items-center justify-between">
              <TkButton
                variant="secondary"
                label={isTesting ? 'Testing...' : 'Test Connection'}
                disabled={isTesting || !jiraProjectKey || !baseUrl}
                onClick={handleTestConnection}
              />
              
              <div className="flex gap-2">
                {(config || isEditing) && (
                  <TkButton
                    variant="secondary"
                    label="Cancel"
                    onClick={() => {
                      if (config) {
                        populateForm(config);
                      } else {
                        resetForm();
                      }
                      setIsEditing(false);
                      setError(null);
                      setTestResult(null);
                    }}
                  />
                )}
                <TkButton
                  variant="primary"
                  label={isSaving ? 'Saving...' : (config ? 'Update' : 'Save')}
                  disabled={isSaving || !jiraProjectKey || !baseUrl}
                  onClick={handleSave}
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </TkCard>
  );
}
