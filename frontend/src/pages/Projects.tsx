import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiClient } from '@/api/client';
import { Project, PaginatedResponse } from '@/types';
import { format } from 'date-fns';

export function Projects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  
  const [newProject, setNewProject] = useState({
    name: '',
    description: '',
    vllm_config: {
      api_url: 'http://localhost:8000',
      model_name: 'Qwen2.5-7B-Instruct',
      temperature: 0.7,
      max_tokens: 2048,
    },
  });
  const [createError, setCreateError] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    loadProjects();
  }, [page, search]);

  const loadProjects = async () => {
    setIsLoading(true);
    try {
      const data = await apiClient.getProjects({ page, page_size: 12, search: search || undefined }) as PaginatedResponse<Project>;
      setProjects(data.items);
      setTotal(data.total);
    } catch (error) {
      console.error('Failed to load projects:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!newProject.name.trim()) {
      setCreateError('Project name is required');
      return;
    }

    setIsCreating(true);
    setCreateError('');

    try {
      await apiClient.createProject({
        name: newProject.name,
        description: newProject.description || undefined,
        vllm_config: newProject.vllm_config,
      });
      
      setShowCreateModal(false);
      setNewProject({
        name: '',
        description: '',
        vllm_config: {
          api_url: 'http://localhost:8000',
          model_name: 'Qwen2.5-7B-Instruct',
          temperature: 0.7,
          max_tokens: 2048,
        },
      });
      loadProjects();
    } catch (error) {
      setCreateError(error instanceof Error ? error.message : 'Failed to create project');
    } finally {
      setIsCreating(false);
    }
  };

  const totalPages = Math.ceil(total / 12);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Top Banner */}
      <div className="p-6 glass-card rounded-2xl border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight">Project Workspaces</h1>
          <p className="text-slate-400 text-xs font-mono mt-1">Configure vLLM model parameters & target web environments</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white rounded-xl font-semibold text-xs shadow-lg shadow-cyan-500/20 transition-all font-mono"
        >
          + New Workspace Project
        </button>
      </div>

      {/* Search Input */}
      <div className="max-w-md">
        <input
          type="text"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          placeholder="Filter projects by name or description..."
          className="w-full px-4 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500/50"
        />
      </div>

      {/* Projects Grid */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center h-64 space-y-3">
          <div className="w-8 h-8 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-xs font-mono text-slate-400">Loading workspaces...</p>
        </div>
      ) : projects.length > 0 ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map((project) => (
              <div key={project.id} className="glass-card glass-card-hover p-6 rounded-2xl border border-slate-800 flex flex-col justify-between">
                <div>
                  <div className="flex items-start justify-between mb-4">
                    <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-xl flex items-center justify-center shadow-lg shadow-cyan-500/20 text-white">
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                      </svg>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2.5 py-0.5 text-[10px] font-mono font-semibold rounded-full ${project.is_active ? 'status-completed' : 'status-cancelled'}`}>
                        {project.is_active ? 'ACTIVE' : 'INACTIVE'}
                      </span>
                      <Link 
                        to={`/projects/${project.id}/settings`}
                        className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-all"
                        title="Project Settings"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                      </Link>
                    </div>
                  </div>
                  
                  <h3 className="text-base font-bold text-slate-100 mb-1">{project.name}</h3>
                  <p className="text-xs text-slate-400 line-clamp-2 mb-4">
                    {project.description || 'No project description.'}
                  </p>
                </div>

                <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] font-mono text-slate-500">
                  <span>{format(new Date(project.created_at), 'MMM d, yyyy')}</span>
                  <span className="text-cyan-400">{project.vllm_config?.model_name || 'vLLM Default'}</span>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-3 pt-4">
              <button
                disabled={page === 1}
                onClick={() => setPage(p => p - 1)}
                className="px-4 py-2 bg-slate-900 hover:bg-slate-800 border border-slate-800 disabled:opacity-40 rounded-xl text-xs font-mono text-slate-300"
              >
                ← Prev
              </button>
              <span className="text-xs font-mono text-slate-400">
                Page {page} of {totalPages}
              </span>
              <button
                disabled={page === totalPages}
                onClick={() => setPage(p => p + 1)}
                className="px-4 py-2 bg-slate-900 hover:bg-slate-800 border border-slate-800 disabled:opacity-40 rounded-xl text-xs font-mono text-slate-300"
              >
                Next →
              </button>
            </div>
          )}
        </>
      ) : (
        <div className="glass-card p-12 text-center rounded-2xl border border-slate-800">
          <h3 className="text-base font-bold text-slate-200 mb-1">No Projects Found</h3>
          <p className="text-xs text-slate-400 mb-6 font-mono">Create your first test automation project workspace to get started</p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-5 py-2.5 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white rounded-xl font-semibold text-xs shadow-lg shadow-cyan-500/20 transition-all font-mono"
          >
            Create Project
          </button>
        </div>
      )}

      {/* Create Project Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-md flex items-center justify-center z-50 p-4">
          <div className="glass-card bg-slate-950 rounded-2xl border border-slate-800 shadow-2xl w-full max-w-lg overflow-hidden animate-slide-up">
            <div className="p-6 border-b border-slate-800">
              <h2 className="text-lg font-bold text-white">Create Workspace Project</h2>
            </div>
            
            <div className="p-6 space-y-4 font-mono text-xs">
              {createError && (
                <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400">
                  ⚠ {createError}
                </div>
              )}

              <div>
                <label className="block uppercase tracking-wider text-slate-400 mb-1.5">Project Name *</label>
                <input
                  type="text"
                  value={newProject.name}
                  onChange={(e) => setNewProject(p => ({ ...p, name: e.target.value }))}
                  placeholder="e.g. E-Commerce Checkout Suite"
                  className="w-full px-3.5 py-2 bg-slate-900 border border-slate-800 rounded-xl text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block uppercase tracking-wider text-slate-400 mb-1.5">Description</label>
                <textarea
                  value={newProject.description}
                  onChange={(e) => setNewProject(p => ({ ...p, description: e.target.value }))}
                  placeholder="Describe scope of tests in this project..."
                  rows={3}
                  className="w-full px-3.5 py-2 bg-slate-900 border border-slate-800 rounded-xl text-slate-200 focus:outline-none focus:border-cyan-500 resize-none"
                />
              </div>

              <div className="pt-3 border-t border-slate-800">
                <h3 className="uppercase tracking-wider text-cyan-400 font-semibold mb-3">vLLM Agent Settings</h3>
                
                <div className="space-y-3">
                  <div>
                    <label className="block text-slate-400 mb-1">API Endpoint URL</label>
                    <input
                      type="text"
                      value={newProject.vllm_config.api_url}
                      onChange={(e) => setNewProject(p => ({
                        ...p,
                        vllm_config: { ...p.vllm_config, api_url: e.target.value }
                      }))}
                      placeholder="http://localhost:8000"
                      className="w-full px-3.5 py-2 bg-slate-900 border border-slate-800 rounded-xl text-slate-200 focus:outline-none focus:border-cyan-500"
                    />
                  </div>

                  <div>
                    <label className="block text-slate-400 mb-1">Model ID Name</label>
                    <input
                      type="text"
                      value={newProject.vllm_config.model_name}
                      onChange={(e) => setNewProject(p => ({
                        ...p,
                        vllm_config: { ...p.vllm_config, model_name: e.target.value }
                      }))}
                      placeholder="Qwen2.5-7B-Instruct"
                      className="w-full px-3.5 py-2 bg-slate-900 border border-slate-800 rounded-xl text-slate-200 focus:outline-none focus:border-cyan-500"
                    />
                  </div>
                </div>
              </div>
            </div>

            <div className="p-6 border-t border-slate-800 flex justify-end gap-3 font-mono text-xs">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-xl text-slate-300"
              >
                Cancel
              </button>
              <button
                disabled={isCreating}
                onClick={handleCreate}
                className="px-5 py-2 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white rounded-xl font-semibold shadow-lg shadow-cyan-500/20"
              >
                {isCreating ? 'Creating...' : 'Create Project'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
