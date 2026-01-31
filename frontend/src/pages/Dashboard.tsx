import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiClient } from '@/api/client';
import { DashboardStats, TestRun, Project } from '@/types';
import { TkCard } from '@takeoff-ui/react';
import { Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { format } from 'date-fns';

const COLORS = ['#22c55e', '#ef4444', '#f59e0b', '#3b82f6'];

export function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentTests, setRecentTests] = useState<TestRun[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      const [statsData, testsData, projectsData] = await Promise.all([
        apiClient.getDashboardStats(),
        apiClient.getTestRuns({ page_size: 5 }),
        apiClient.getProjects({ page_size: 5 }),
      ]);

      setStats(statsData as DashboardStats);
      setRecentTests((testsData as { items: TestRun[] }).items);
      setProjects((projectsData as { items: Project[] }).items);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-600';
      case 'failed': return 'text-red-600';
      case 'running': return 'text-blue-600';
      case 'pending': return 'text-yellow-600';
      default: return 'text-slate-500';
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

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  const pieData = stats ? [
    { name: 'Successful', value: stats.successful_tests },
    { name: 'Failed', value: stats.failed_tests },
    { name: 'Running', value: stats.running_tests },
  ].filter(d => d.value > 0) : [];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Dashboard</h1>
          <p className="text-slate-500 mt-1">Overview of your browser testing platform</p>
        </div>
        <Link
          to="/tests/run"
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-medium transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Run Test
        </Link>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <TkCard>
          <div className="p-6 bg-white rounded-lg border border-slate-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-500 text-sm">Total Projects</p>
                <p className="text-3xl font-bold text-slate-800 mt-1">{stats?.projects || 0}</p>
              </div>
              <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                </svg>
              </div>
            </div>
          </div>
        </TkCard>

        <TkCard>
          <div className="p-6 bg-white rounded-lg border border-slate-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-500 text-sm">Total Tests</p>
                <p className="text-3xl font-bold text-slate-800 mt-1">{stats?.total_tests || 0}</p>
              </div>
              <div className="w-12 h-12 bg-indigo-100 rounded-xl flex items-center justify-center">
                <svg className="w-6 h-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              </div>
            </div>
          </div>
        </TkCard>

        <TkCard>
          <div className="p-6 bg-white rounded-lg border border-slate-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-500 text-sm">Success Rate</p>
                <p className="text-3xl font-bold text-slate-800 mt-1">{stats?.success_rate?.toFixed(1) || 0}%</p>
              </div>
              <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center">
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
          </div>
        </TkCard>

        <TkCard>
          <div className="p-6 bg-white rounded-lg border border-slate-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-500 text-sm">Running Now</p>
                <p className="text-3xl font-bold text-slate-800 mt-1">{stats?.running_tests || 0}</p>
              </div>
              <div className="w-12 h-12 bg-yellow-100 rounded-xl flex items-center justify-center">
                {(stats?.running_tests || 0) > 0 ? (
                  <div className="w-6 h-6 border-2 border-yellow-600 border-t-transparent rounded-full animate-spin"></div>
                ) : (
                  <svg className="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                )}
              </div>
            </div>
          </div>
        </TkCard>
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Test results pie chart */}
        <TkCard>
          <div className="p-6 bg-white rounded-lg border border-slate-200">
            <h3 className="text-lg font-semibold text-slate-800 mb-4">Test Results Distribution</h3>
            {pieData.length > 0 ? (
              <div className="h-64 w-full" style={{ minHeight: '256px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={80}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      {pieData.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ backgroundColor: '#fff', border: '1px solid #e2e8f0', borderRadius: '8px' }}
                      labelStyle={{ color: '#1e293b' }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="h-64 flex items-center justify-center text-slate-500">
                No test data available
              </div>
            )}
            <div className="flex justify-center gap-6 mt-4">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-green-500"></div>
                <span className="text-sm text-slate-600">Successful</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-red-500"></div>
                <span className="text-sm text-slate-600">Failed</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                <span className="text-sm text-slate-600">Running</span>
              </div>
            </div>
          </div>
        </TkCard>

        {/* Recent activity */}
        <TkCard>
          <div className="p-6 bg-white rounded-lg border border-slate-200">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-slate-800">Recent Tests</h3>
              <Link to="/tests" className="text-sm text-blue-600 hover:text-blue-700">
                View all
              </Link>
            </div>
            <div className="space-y-3">
              {recentTests.length > 0 ? (
                recentTests.map((test) => (
                  <Link
                    key={test.id}
                    to={`/tests/${test.id}`}
                    className="flex items-center justify-between p-3 bg-slate-50 hover:bg-slate-100 rounded-lg transition-colors"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className={`w-2 h-2 rounded-full ${getStatusColor(test.status).replace('text-', 'bg-')}`}></div>
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-slate-700 truncate">{test.command.slice(0, 50)}...</p>
                        <p className="text-xs text-slate-500">{test.project_name || `Project #${test.project_id}`}</p>
                      </div>
                    </div>
                    <span className={`px-2 py-0.5 text-xs font-medium rounded ${getStatusBadgeClass(test.status)}`}>
                      {test.status}
                    </span>
                  </Link>
                ))
              ) : (
                <div className="text-center py-8 text-slate-500">
                  No tests yet. Run your first test!
                </div>
              )}
            </div>
          </div>
        </TkCard>
      </div>

      {/* Projects list */}
      <TkCard>
        <div className="p-6 bg-white rounded-lg border border-slate-200">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-slate-800">Projects</h3>
            <Link to="/projects" className="text-sm text-blue-600 hover:text-blue-700">
              View all
            </Link>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.length > 0 ? (
              projects.map((project) => (
                <Link
                  key={project.id}
                  to={`/projects/${project.id}`}
                  className="p-4 bg-slate-50 hover:bg-slate-100 rounded-lg transition-colors border border-slate-200"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="font-medium text-slate-700">{project.name}</h4>
                      <p className="text-sm text-slate-500 mt-1 line-clamp-2">
                        {project.description || 'No description'}
                      </p>
                    </div>
                    {project.is_active ? (
                      <span className="px-2 py-0.5 text-xs font-medium rounded status-completed">Active</span>
                    ) : (
                      <span className="px-2 py-0.5 text-xs font-medium rounded status-cancelled">Inactive</span>
                    )}
                  </div>
                  <div className="mt-3 pt-3 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
                    <span>Created {format(new Date(project.created_at), 'MMM d, yyyy')}</span>
                    <span>{project.test_run_count || 0} tests</span>
                  </div>
                </Link>
              ))
            ) : (
              <div className="col-span-full text-center py-8 text-slate-500">
                No projects yet. Create your first project!
              </div>
            )}
          </div>
        </div>
      </TkCard>
    </div>
  );
}
