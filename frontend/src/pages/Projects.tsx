import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiClient } from '@/api/client';
import { Project, PaginatedResponse } from '@/types';
import { TkButton, TkCard } from '@takeoff-ui/react';
import { format } from 'date-fns';

export function Projects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  
  // Create form state
  const [newProject, setNewProject] = useState({
    name: '',
    description: '',
    vllm_config: {
      api_url: 'http://localhost:8000',
      model_name: '',
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
          model_name: '',
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
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Projects</h1>
          <p className="text-slate-500 mt-1">Manage your browser testing projects</p>
        </div>
        <TkButton
          variant="primary"
          label="New Project"
          onClick={() => setShowCreateModal(true)}
        />
      </div>

      {/* Search */}
      <div className="max-w-md">
        <input
          type="text"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          placeholder="Search projects..."
          className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-slate-700 placeholder-slate-400 focus:outline-none focus:border-blue-500"
        />
      </div>

      {/* Projects grid */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : projects.length > 0 ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map((project) => (
              <TkCard key={project.id}>
                <div className="p-6 bg-white rounded-lg border border-slate-200 hover:shadow-md transition-shadow">
                  <div className="flex items-start justify-between mb-3">
                    <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-lg flex items-center justify-center">
                      <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                      </svg>
                    </div>
                    <div className="flex items-center gap-2">
                      {project.is_active ? (
                        <span className="px-2 py-0.5 text-xs font-medium rounded status-completed">Active</span>
                      ) : (
                        <span className="px-2 py-0.5 text-xs font-medium rounded status-cancelled">Inactive</span>
                      )}
                      <Link 
                        to={`/projects/${project.id}/settings`}
                        className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded transition-colors"
                        title="Project Settings"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                      </Link>
                    </div>
                  </div>
                  
                  <h3 className="text-lg font-semibold text-slate-800 mb-2">{project.name}</h3>
                  <p className="text-sm text-slate-500 line-clamp-2 mb-4">
                    {project.description || 'No description provided'}
                  </p>

                  <div className="pt-4 border-t border-slate-200 flex items-center justify-between text-sm">
                    <span className="text-slate-500">
                      {format(new Date(project.created_at), 'MMM d, yyyy')}
                    </span>
                    <span className="text-slate-500">
                      {project.vllm_config?.model_name || 'No model'}
                    </span>
                  </div>
                </div>
              </TkCard>
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
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-slate-800 mb-2">No projects yet</h3>
            <p className="text-slate-500 mb-6">Create your first project to start automating browser tests</p>
            <TkButton
              variant="primary"
              label="Create Project"
              onClick={() => setShowCreateModal(true)}
            />
          </div>
        </TkCard>
      )}

      {/* Create Project Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl border border-slate-200 shadow-xl w-full max-w-lg animate-slide-up">
            <div className="p-6 border-b border-slate-200">
              <h2 className="text-xl font-semibold text-slate-800">Create New Project</h2>
            </div>
            
            <div className="p-6 space-y-4">
              {createError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
                  {createError}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Project Name *</label>
                <input
                  type="text"
                  value={newProject.name}
                  onChange={(e) => setNewProject(p => ({ ...p, name: e.target.value }))}
                  placeholder="My Browser Tests"
                  className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-slate-700 placeholder-slate-400 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Description</label>
                <textarea
                  value={newProject.description}
                  onChange={(e) => setNewProject(p => ({ ...p, description: e.target.value }))}
                  placeholder="Describe what this project tests..."
                  rows={3}
                  className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-slate-700 placeholder-slate-400 focus:outline-none focus:border-blue-500 resize-none"
                />
              </div>

              <div className="pt-4 border-t border-slate-200">
                <h3 className="text-sm font-medium text-slate-700 mb-3">vLLM Configuration</h3>
                
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">API URL</label>
                    <input
                      type="text"
                      value={newProject.vllm_config.api_url}
                      onChange={(e) => setNewProject(p => ({
                        ...p,
                        vllm_config: { ...p.vllm_config, api_url: e.target.value }
                      }))}
                      placeholder="http://localhost:8000"
                      className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-slate-700 placeholder-slate-400 focus:outline-none focus:border-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs text-slate-500 mb-1">Model Name</label>
                    <input
                      type="text"
                      value={newProject.vllm_config.model_name}
                      onChange={(e) => setNewProject(p => ({
                        ...p,
                        vllm_config: { ...p.vllm_config, model_name: e.target.value }
                      }))}
                      placeholder="llama-3.1-8b"
                      className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-slate-700 placeholder-slate-400 focus:outline-none focus:border-blue-500"
                    />
                  </div>
                </div>
              </div>
            </div>

            <div className="p-6 border-t border-slate-200 flex justify-end gap-3">
              <TkButton
                variant="secondary"
                label="Cancel"
                onClick={() => setShowCreateModal(false)}
              />
              <TkButton
                variant="primary"
                label={isCreating ? 'Creating...' : 'Create Project'}
                disabled={isCreating}
                onClick={handleCreate}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
