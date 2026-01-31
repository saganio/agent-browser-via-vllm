import { useEffect, useState } from 'react';
import { apiClient } from '@/api/client';
import { Schedule, Project, PaginatedResponse } from '@/types';
import { TkButton, TkCard } from '@takeoff-ui/react';
import { format } from 'date-fns';

export function Schedules() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  
  const [newSchedule, setNewSchedule] = useState({
    name: '',
    project_id: 0,
    command: '',
    cron_expression: '0 9 * * *',
    timezone: 'UTC',
    enabled: true,
  });
  const [createError, setCreateError] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    loadData();
  }, [page]);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [schedulesData, projectsData] = await Promise.all([
        apiClient.getSchedules({ page, page_size: 20 }),
        apiClient.getProjects({ page_size: 100 }),
      ]);
      
      setSchedules((schedulesData as PaginatedResponse<Schedule>).items);
      setTotal((schedulesData as PaginatedResponse<Schedule>).total);
      setProjects((projectsData as { items: Project[] }).items);
      
      if ((projectsData as { items: Project[] }).items.length > 0 && !newSchedule.project_id) {
        setNewSchedule(s => ({ ...s, project_id: (projectsData as { items: Project[] }).items[0].id }));
      }
    } catch (error) {
      console.error('Failed to load schedules:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!newSchedule.name.trim() || !newSchedule.command.trim() || !newSchedule.project_id) {
      setCreateError('Please fill all required fields');
      return;
    }

    setIsCreating(true);
    setCreateError('');

    try {
      await apiClient.createSchedule(newSchedule);
      setShowCreateModal(false);
      setNewSchedule({
        name: '',
        project_id: projects[0]?.id || 0,
        command: '',
        cron_expression: '0 9 * * *',
        timezone: 'UTC',
        enabled: true,
      });
      loadData();
    } catch (error) {
      setCreateError(error instanceof Error ? error.message : 'Failed to create schedule');
    } finally {
      setIsCreating(false);
    }
  };

  const handleToggle = async (schedule: Schedule) => {
    try {
      await apiClient.updateSchedule(schedule.id, { enabled: !schedule.enabled });
      loadData();
    } catch (error) {
      console.error('Failed to update schedule:', error);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this schedule?')) return;
    
    try {
      await apiClient.deleteSchedule(id);
      loadData();
    } catch (error) {
      console.error('Failed to delete schedule:', error);
    }
  };

  const totalPages = Math.ceil(total / 20);

  const cronPresets = [
    { label: 'Every hour', value: '0 * * * *' },
    { label: 'Daily at 9am', value: '0 9 * * *' },
    { label: 'Daily at midnight', value: '0 0 * * *' },
    { label: 'Weekly (Monday 9am)', value: '0 9 * * 1' },
    { label: 'Monthly (1st at 9am)', value: '0 9 1 * *' },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Scheduled Tests</h1>
          <p className="text-slate-500 mt-1">Automate test execution with cron schedules</p>
        </div>
        <TkButton
          variant="primary"
          label="New Schedule"
          onClick={() => setShowCreateModal(true)}
        />
      </div>

      {/* Schedules list */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : schedules.length > 0 ? (
        <>
          <div className="grid gap-4">
            {schedules.map((schedule) => (
              <TkCard key={schedule.id}>
                <div className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3">
                        <h3 className="text-lg font-semibold text-slate-800">{schedule.name}</h3>
                        <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                          schedule.enabled ? 'status-completed' : 'status-cancelled'
                        }`}>
                          {schedule.enabled ? 'Active' : 'Disabled'}
                        </span>
                      </div>
                      <p className="text-sm text-slate-500 mt-1">
                        {schedule.project_name || `Project #${schedule.project_id}`}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => handleToggle(schedule)}
                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                          schedule.enabled ? 'bg-blue-500' : 'bg-slate-600'
                        }`}
                      >
                        <span
                          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                            schedule.enabled ? 'translate-x-6' : 'translate-x-1'
                          }`}
                        />
                      </button>
                      <button
                        onClick={() => handleDelete(schedule.id)}
                        className="p-2 text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </div>

                  <div className="mt-4 p-3 bg-slate-50 rounded-lg">
                    <p className="text-sm text-slate-600 font-mono">{schedule.command}</p>
                  </div>

                  <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <p className="text-slate-500">Schedule</p>
                      <p className="text-slate-700 font-mono">{schedule.cron_expression}</p>
                    </div>
                    <div>
                      <p className="text-slate-500">Timezone</p>
                      <p className="text-slate-700">{schedule.timezone}</p>
                    </div>
                    <div>
                      <p className="text-slate-500">Last Run</p>
                      <p className="text-slate-700">
                        {schedule.last_run_at 
                          ? format(new Date(schedule.last_run_at), 'MMM d, HH:mm')
                          : 'Never'}
                      </p>
                    </div>
                    <div>
                      <p className="text-slate-500">Next Run</p>
                      <p className="text-slate-700">
                        {schedule.next_run_at 
                          ? format(new Date(schedule.next_run_at), 'MMM d, HH:mm')
                          : '-'}
                      </p>
                    </div>
                  </div>

                  <div className="mt-4 pt-4 border-t border-slate-200 flex items-center justify-between text-sm">
                    <span className="text-slate-500">
                      Run count: {schedule.run_count}
                    </span>
                    {schedule.last_run_status && (
                      <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                        schedule.last_run_status === 'completed' ? 'status-completed' :
                        schedule.last_run_status === 'failed' ? 'status-failed' :
                        'status-pending'
                      }`}>
                        Last: {schedule.last_run_status}
                      </span>
                    )}
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
          <div className="p-12 text-center">
            <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-slate-800 mb-2">No schedules yet</h3>
            <p className="text-slate-500 mb-6">Create a schedule to automate your browser tests</p>
            <TkButton
              variant="primary"
              label="Create Schedule"
              onClick={() => setShowCreateModal(true)}
            />
          </div>
        </TkCard>
      )}

      {/* Create Schedule Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl border border-slate-200 w-full max-w-lg animate-slide-up">
            <div className="p-6 border-b border-slate-200">
              <h2 className="text-xl font-semibold text-slate-800">Create Schedule</h2>
            </div>
            
            <div className="p-6 space-y-4">
              {createError && (
                <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
                  {createError}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-slate-600 mb-2">Schedule Name *</label>
                <input
                  type="text"
                  value={newSchedule.name}
                  onChange={(e) => setNewSchedule(s => ({ ...s, name: e.target.value }))}
                  placeholder="Daily smoke test"
                  className="w-full px-3 py-2 bg-slate-100 border border-slate-300 rounded-lg text-slate-700 placeholder-slate-400 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-600 mb-2">Project *</label>
                <select
                  value={newSchedule.project_id}
                  onChange={(e) => setNewSchedule(s => ({ ...s, project_id: Number(e.target.value) }))}
                  className="w-full px-3 py-2 bg-slate-100 border border-slate-300 rounded-lg text-slate-700"
                >
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-600 mb-2">Command *</label>
                <textarea
                  value={newSchedule.command}
                  onChange={(e) => setNewSchedule(s => ({ ...s, command: e.target.value }))}
                  placeholder="Navigate to example.com and verify the homepage loads"
                  rows={3}
                  className="w-full px-3 py-2 bg-slate-100 border border-slate-300 rounded-lg text-slate-700 placeholder-slate-400 focus:outline-none focus:border-blue-500 resize-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-600 mb-2">Cron Expression *</label>
                <input
                  type="text"
                  value={newSchedule.cron_expression}
                  onChange={(e) => setNewSchedule(s => ({ ...s, cron_expression: e.target.value }))}
                  placeholder="0 9 * * *"
                  className="w-full px-3 py-2 bg-slate-100 border border-slate-300 rounded-lg text-slate-700 placeholder-slate-400 focus:outline-none focus:border-blue-500"
                />
                <div className="flex flex-wrap gap-2 mt-2">
                  {cronPresets.map((preset) => (
                    <button
                      key={preset.value}
                      onClick={() => setNewSchedule(s => ({ ...s, cron_expression: preset.value }))}
                      className="px-2 py-1 text-xs bg-slate-100 hover:bg-slate-100 text-slate-600 rounded transition-colors"
                    >
                      {preset.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-600 mb-2">Timezone</label>
                <select
                  value={newSchedule.timezone}
                  onChange={(e) => setNewSchedule(s => ({ ...s, timezone: e.target.value }))}
                  className="w-full px-3 py-2 bg-slate-100 border border-slate-300 rounded-lg text-slate-700"
                >
                  <option value="UTC">UTC</option>
                  <option value="America/New_York">America/New_York</option>
                  <option value="America/Los_Angeles">America/Los_Angeles</option>
                  <option value="Europe/London">Europe/London</option>
                  <option value="Europe/Istanbul">Europe/Istanbul</option>
                  <option value="Asia/Tokyo">Asia/Tokyo</option>
                </select>
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
                label={isCreating ? 'Creating...' : 'Create Schedule'}
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
