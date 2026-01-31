import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { apiClient } from '@/api/client';
import { Project } from '@/types';
import { TkButton, TkCard } from '@takeoff-ui/react';
import { XrayConfigComponent } from '@/components/xray/XrayConfig';

export function ProjectSettings() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [project, setProject] = useState<Project | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'general' | 'xray' | 'vllm'>('xray');

  // Edit state
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState('');
  const [editDescription, setEditDescription] = useState('');

  // vLLM Edit state
  const [isEditingVllm, setIsEditingVllm] = useState(false);
  const [editVllmApiUrl, setEditVllmApiUrl] = useState('');
  const [editVllmModelName, setEditVllmModelName] = useState('');
  const [editVllmApiKey, setEditVllmApiKey] = useState('');
  const [editVllmTemperature, setEditVllmTemperature] = useState(0.7);
  const [editVllmMaxTokens, setEditVllmMaxTokens] = useState(2048);

  const [isSaving, setIsSaving] = useState(false);
  const [isTestingConnection, setIsTestingConnection] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<{ success: boolean; message: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (id) {
      loadProject();
    }
  }, [id]);

  const loadProject = async () => {
    setIsLoading(true);
    try {
      const data = await apiClient.getProject(Number(id)) as Project;
      setProject(data);
      setEditName(data.name);
      setEditDescription(data.description || '');

      // Initialize vLLM state
      const vllmConfig = data.vllm_config || {};
      setEditVllmApiUrl((vllmConfig.api_url as string) || '');
      setEditVllmModelName((vllmConfig.model_name as string) || '');
      setEditVllmApiKey((vllmConfig.api_key as string) || '');
      setEditVllmTemperature((vllmConfig.temperature as number) ?? 0.7);
      setEditVllmMaxTokens((vllmConfig.max_tokens as number) ?? 2048);
    } catch (error) {
      console.error('Failed to load project:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    if (!project) return;

    setIsSaving(true);
    setError(null);

    try {
      await apiClient.updateProject(project.id, {
        name: editName,
        description: editDescription,
      });
      await loadProject();
      setIsEditing(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save');
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveVllm = async () => {
    if (!project) return;

    setIsSaving(true);
    setError(null);

    try {
      await apiClient.updateProject(project.id, {
        vllm_config: {
          api_url: editVllmApiUrl,
          model_name: editVllmModelName,
          api_key: editVllmApiKey || null,
          temperature: editVllmTemperature,
          max_tokens: editVllmMaxTokens,
        }
      });
      await loadProject();
      setIsEditingVllm(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save vLLM config');
    } finally {
      setIsSaving(false);
    }
  };

  const testConnection = async () => {
    setIsTestingConnection(true);
    setConnectionStatus(null);
    try {
      const result = await apiClient.testVLLMConnection({
        api_url: isEditingVllm ? editVllmApiUrl : (project?.vllm_config?.api_url as string),
        model_name: isEditingVllm ? editVllmModelName : (project?.vllm_config?.model_name as string),
        api_key: isEditingVllm ? editVllmApiKey : (project?.vllm_config?.api_key as string),
      });

      setConnectionStatus({
        success: result.success,
        message: result.message
      });
    } catch (err) {
      setConnectionStatus({
        success: false,
        message: err instanceof Error ? err.message : 'Connection failed'
      });
    } finally {
      setIsTestingConnection(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-slate-800 mb-2">Project Not Found</h2>
          <Link to="/projects">
            <TkButton variant="primary" label="Back to Projects" />
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/projects')}
            className="p-2 text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <div>
            <h1 className="text-2xl font-bold text-slate-800">{project.name}</h1>
            <p className="text-slate-500">Project Settings</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200">
        <nav className="flex gap-4">
          {[
            { id: 'general', label: 'General' },
            { id: 'xray', label: 'Xray Integration' },
            { id: 'vllm', label: 'vLLM Configuration' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${activeTab === tab.id
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-slate-600 hover:text-slate-800'
                }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      <div className="space-y-6">
        {/* General Tab */}
        {activeTab === 'general' && (
          <TkCard>
            <div className="p-6 bg-white border border-slate-200 rounded-lg shadow-sm">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold text-slate-800">General Settings</h3>
                {!isEditing && (
                  <TkButton
                    variant="secondary"
                    label="Edit"
                    onClick={() => setIsEditing(true)}
                  />
                )}
              </div>

              {error && (
                <div className="p-3 mb-4 bg-red-100 border border-red-200 rounded-lg text-red-700 text-sm">
                  {error}
                </div>
              )}

              {isEditing ? (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">Project Name</label>
                    <input
                      type="text"
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-100 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">Description</label>
                    <textarea
                      value={editDescription}
                      onChange={(e) => setEditDescription(e.target.value)}
                      rows={3}
                      className="w-full px-3 py-2 bg-slate-100 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-blue-500 resize-none"
                    />
                  </div>
                  <div className="flex justify-end gap-2">
                    <TkButton
                      variant="secondary"
                      label="Cancel"
                      onClick={() => {
                        setIsEditing(false);
                        setEditName(project.name);
                        setEditDescription(project.description || '');
                        setError(null);
                      }}
                    />
                    <TkButton
                      variant="primary"
                      label={isSaving ? 'Saving...' : 'Save'}
                      disabled={isSaving}
                      onClick={handleSave}
                    />
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <div>
                    <p className="text-sm text-slate-500">Project Name</p>
                    <p className="text-slate-800 font-medium">{project.name}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Description</p>
                    <p className="text-slate-800">{project.description || 'No description'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Created</p>
                    <p className="text-slate-800">{new Date(project.created_at).toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500">Status</p>
                    <span className={`inline-block px-2 py-0.5 text-xs font-medium rounded ${project.is_active
                      ? 'bg-green-100 text-green-700'
                      : 'bg-slate-100 text-slate-700'
                      }`}>
                      {project.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                </div>
              )}
            </div>
          </TkCard>
        )}

        {/* Xray Tab */}
        {activeTab === 'xray' && (
          <XrayConfigComponent
            projectId={project.id}
            onConfigChange={loadProject}
          />
        )}

        {/* vLLM Tab */}
        {activeTab === 'vllm' && (
          <TkCard>
            <div className="p-6 bg-white border border-slate-200 rounded-lg shadow-sm">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold text-slate-800">vLLM Configuration</h3>
                {!isEditingVllm && (
                  <TkButton
                    variant="secondary"
                    label="Edit"
                    onClick={() => setIsEditingVllm(true)}
                  />
                )}
              </div>

              {error && activeTab === 'vllm' && (
                <div className="p-3 mb-4 bg-red-100 border border-red-200 rounded-lg text-red-700 text-sm">
                  {error}
                </div>
              )}

              {connectionStatus && (
                <div className={`p-3 mb-4 border rounded-lg text-sm ${connectionStatus.success
                    ? 'bg-green-50 border-green-200 text-green-700'
                    : 'bg-red-50 border-red-200 text-red-700'
                  }`}>
                  <div className="flex items-center gap-2">
                    {connectionStatus.success ? (
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    ) : (
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    )}
                    {connectionStatus.message}
                  </div>
                </div>
              )}

              {isEditingVllm ? (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">API URL</label>
                    <input
                      type="text"
                      value={editVllmApiUrl}
                      onChange={(e) => setEditVllmApiUrl(e.target.value)}
                      placeholder="http://localhost:8000/v1"
                      className="w-full px-3 py-2 bg-slate-100 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">Model Name</label>
                    <input
                      type="text"
                      value={editVllmModelName}
                      onChange={(e) => setEditVllmModelName(e.target.value)}
                      placeholder="meta-llama/Llama-2-7b-chat-hf"
                      className="w-full px-3 py-2 bg-slate-100 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">API Key (Optional)</label>
                    <input
                      type="password"
                      value={editVllmApiKey}
                      onChange={(e) => setEditVllmApiKey(e.target.value)}
                      placeholder="sk-..."
                      className="w-full px-3 py-2 bg-slate-100 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-blue-500"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-2">Temperature</label>
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        max="2"
                        value={editVllmTemperature}
                        onChange={(e) => setEditVllmTemperature(parseFloat(e.target.value))}
                        className="w-full px-3 py-2 bg-slate-100 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-2">Max Tokens</label>
                      <input
                        type="number"
                        step="128"
                        min="128"
                        max="8192"
                        value={editVllmMaxTokens}
                        onChange={(e) => setEditVllmMaxTokens(parseInt(e.target.value))}
                        className="w-full px-3 py-2 bg-slate-100 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-blue-500"
                      />
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-4">
                    <TkButton
                      variant="secondary"
                      label={isTestingConnection ? "Testing..." : "Test Connection"}
                      disabled={isTestingConnection}
                      onClick={testConnection}
                    />

                    <div className="flex gap-2">
                      <TkButton
                        variant="secondary"
                        label="Cancel"
                        onClick={() => {
                          setIsEditingVllm(false);
                          setConnectionStatus(null);
                          // Reset fields
                          const config = project.vllm_config || {};
                          setEditVllmApiUrl((config.api_url as string) || '');
                          setEditVllmModelName((config.model_name as string) || '');
                          setEditVllmApiKey((config.api_key as string) || '');
                          setEditVllmTemperature((config.temperature as number) ?? 0.7);
                          setEditVllmMaxTokens((config.max_tokens as number) ?? 2048);
                          setError(null);
                        }}
                      />
                      <TkButton
                        variant="primary"
                        label={isSaving ? 'Saving...' : 'Save'}
                        disabled={isSaving}
                        onClick={handleSaveVllm}
                      />
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-slate-500">API URL</p>
                      <p className="text-slate-800 font-mono text-sm break-all">
                        {project.vllm_config?.api_url || 'Not configured'}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-slate-500">Model Name</p>
                      <p className="text-slate-800 font-mono text-sm break-all">
                        {project.vllm_config?.model_name || 'Not configured'}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-slate-500">Temperature</p>
                      <p className="text-slate-800">
                        {project.vllm_config?.temperature ?? 0.7}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-slate-500">Max Tokens</p>
                      <p className="text-slate-800">
                        {project.vllm_config?.max_tokens ?? 2048}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-slate-500">API Key</p>
                      <p className="text-slate-800 font-mono text-sm">
                        {project.vllm_config?.api_key ? '••••••••' : 'Not configured'}
                      </p>
                    </div>
                  </div>

                  <div className="pt-4 border-t border-slate-200">
                    <div className="flex items-center justify-between">
                      <p className="text-sm text-slate-500">
                        vLLM configuration is used for AI-powered test command generation.
                      </p>
                      <TkButton
                        variant="secondary"
                        label={isTestingConnection ? "Testing..." : "Test Connection"}
                        disabled={isTestingConnection}
                        onClick={testConnection}
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>
          </TkCard>
        )}
      </div>
    </div>
  );
}
