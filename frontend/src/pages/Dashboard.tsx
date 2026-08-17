import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiClient } from '@/api/client';
import { DashboardStats, TestRun, Project } from '@/types';
import { Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { format } from 'date-fns';

const COLORS = ['#10b981', '#ef4444', '#f59e0b', '#3b82f6'];

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
      <div className="flex flex-col items-center justify-center h-80 space-y-4">
        <div className="w-10 h-10 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-xs font-mono text-slate-400">Loading Telemetry & Stats...</p>
      </div>
    );
  }

  const pieData = stats ? [
    { name: 'Passed', value: stats.successful_tests },
    { name: 'Failed', value: stats.failed_tests },
    { name: 'Running', value: stats.running_tests },
  ].filter(d => d.value > 0) : [];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Top Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 glass-card rounded-2xl border border-slate-800 relative overflow-hidden">
        <div className="absolute right-0 top-0 w-64 h-full bg-gradient-to-l from-blue-600/10 via-cyan-500/5 to-transparent pointer-events-none"></div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-black tracking-tight text-white">Operations Dashboard</h1>
            <span className="px-2 py-0.5 text-[10px] font-mono font-bold bg-cyan-500/15 text-cyan-400 border border-cyan-500/30 rounded-full uppercase tracking-wider">Live Telemetry</span>
          </div>
          <p className="text-slate-400 text-xs mt-1 font-mono">Real-time status overview of AI browser test runs and worker nodes</p>
        </div>
        <Link
          to="/tests/run"
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white rounded-xl font-semibold text-xs shadow-lg shadow-cyan-500/20 transition-all duration-200"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
          </svg>
          Execute New Test
        </Link>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1 */}
        <div className="glass-card glass-card-hover p-5 rounded-2xl border border-slate-800/80">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-mono uppercase tracking-wider text-slate-400">Total Projects</p>
              <p className="text-3xl font-black text-white mt-1 font-mono tracking-tight">{stats?.projects || 0}</p>
            </div>
            <div className="w-11 h-11 bg-blue-500/10 border border-blue-500/20 rounded-xl flex items-center justify-center text-blue-400">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
              </svg>
            </div>
          </div>
        </div>

        {/* Metric 2 */}
        <div className="glass-card glass-card-hover p-5 rounded-2xl border border-slate-800/80">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-mono uppercase tracking-wider text-slate-400">Total Executions</p>
              <p className="text-3xl font-black text-white mt-1 font-mono tracking-tight">{stats?.total_tests || 0}</p>
            </div>
            <div className="w-11 h-11 bg-indigo-500/10 border border-indigo-500/20 rounded-xl flex items-center justify-center text-indigo-400">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 02-2 2h2a2 2 0 02-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
          </div>
        </div>

        {/* Metric 3 */}
        <div className="glass-card glass-card-hover p-5 rounded-2xl border border-slate-800/80">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-mono uppercase tracking-wider text-slate-400">Pass Rate Velocity</p>
              <p className="text-3xl font-black text-emerald-400 mt-1 font-mono tracking-tight">{stats?.success_rate?.toFixed(1) || 0}%</p>
            </div>
            <div className="w-11 h-11 bg-emerald-500/10 border border-emerald-500/20 rounded-xl flex items-center justify-center text-emerald-400">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
        </div>

        {/* Metric 4 */}
        <div className="glass-card glass-card-hover p-5 rounded-2xl border border-slate-800/80">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-mono uppercase tracking-wider text-slate-400">Active Workers</p>
              <p className="text-3xl font-black text-amber-400 mt-1 font-mono tracking-tight">{stats?.running_tests || 0}</p>
            </div>
            <div className="w-11 h-11 bg-amber-500/10 border border-amber-500/20 rounded-xl flex items-center justify-center text-amber-400">
              {(stats?.running_tests || 0) > 0 ? (
                <div className="w-5 h-5 border-2 border-amber-400 border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Analytics & Recent Activity Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pie Chart Card */}
        <div className="glass-card p-6 rounded-2xl border border-slate-800">
          <h3 className="text-sm font-mono uppercase tracking-wider text-slate-300 font-semibold mb-4 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
            Test Outcome Breakdown
          </h3>
          {pieData.length > 0 ? (
            <div className="h-64 w-full" style={{ minHeight: '256px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={65}
                    outerRadius={85}
                    paddingAngle={6}
                    dataKey="value"
                  >
                    {pieData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} stroke="#020617" strokeWidth={3} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: '#090d16', borderColor: '#1e293b', borderRadius: '12px', color: '#fff', fontSize: '12px', fontFamily: 'Fira Code' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-64 flex items-center justify-center text-xs font-mono text-slate-500">
              No execution telemetry recorded yet
            </div>
          )}
          <div className="flex justify-center gap-6 mt-4 pt-4 border-t border-slate-800/80 text-xs font-mono">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
              <span className="text-slate-300">Passed</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500"></span>
              <span className="text-slate-300">Failed</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
              <span className="text-slate-300">Running</span>
            </div>
          </div>
        </div>

        {/* Live Execution Stream Feed */}
        <div className="glass-card p-6 rounded-2xl border border-slate-800 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-mono uppercase tracking-wider text-slate-300 font-semibold flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                Recent Test Runs
              </h3>
              <Link to="/tests" className="text-xs font-mono text-cyan-400 hover:text-cyan-300 font-medium">
                View All →
              </Link>
            </div>
            <div className="space-y-2.5">
              {recentTests.length > 0 ? (
                recentTests.map((test) => (
                  <Link
                    key={test.id}
                    to={`/tests/${test.id}`}
                    className="flex items-center justify-between p-3.5 bg-slate-900/60 hover:bg-slate-900 border border-slate-800/80 hover:border-slate-700 rounded-xl transition-all"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <span className={`w-2 h-2 rounded-full ${test.status === 'completed' ? 'bg-emerald-500' : test.status === 'failed' ? 'bg-red-500' : 'bg-amber-500'}`}></span>
                      <div className="min-w-0">
                        <p className="text-xs font-mono text-slate-200 truncate">{test.command}</p>
                        <p className="text-[11px] font-mono text-slate-500 mt-0.5">Run #{test.id} • {test.project_name || `Project #${test.project_id}`}</p>
                      </div>
                    </div>
                    <span className={`px-2.5 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wider rounded-full ${getStatusBadgeClass(test.status)}`}>
                      {test.status}
                    </span>
                  </Link>
                ))
              ) : (
                <div className="text-center py-12 text-xs font-mono text-slate-500">
                  No tests executed yet. Launch your first test!
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Projects Grid Container */}
      <div className="glass-card p-6 rounded-2xl border border-slate-800">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-mono uppercase tracking-wider text-slate-300 font-semibold flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-blue-400"></span>
            Active Workspaces
          </h3>
          <Link to="/projects" className="text-xs font-mono text-cyan-400 hover:text-cyan-300 font-medium">
            Manage Projects →
          </Link>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.length > 0 ? (
            projects.map((project) => (
              <Link
                key={project.id}
                to={`/projects/${project.id}`}
                className="p-4 bg-slate-900/60 hover:bg-slate-900 border border-slate-800/80 hover:border-blue-500/30 rounded-xl transition-all"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="font-semibold text-slate-200 text-sm">{project.name}</h4>
                    <p className="text-xs text-slate-400 mt-1 line-clamp-2">
                      {project.description || 'No description provided'}
                    </p>
                  </div>
                  <span className={`px-2 py-0.5 text-[10px] font-mono font-semibold rounded-full ${project.is_active ? 'status-completed' : 'status-cancelled'}`}>
                    {project.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
                <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] font-mono text-slate-500">
                  <span>{format(new Date(project.created_at), 'MMM d, yyyy')}</span>
                  <span className="text-cyan-400">{project.test_run_count || 0} runs</span>
                </div>
              </Link>
            ))
          ) : (
            <div className="col-span-full text-center py-8 text-xs font-mono text-slate-500">
              No projects created yet. Click "Manage Projects" to create one!
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
