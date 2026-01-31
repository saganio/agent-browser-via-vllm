import { useEffect, useState } from 'react';
import { apiClient } from '@/api/client';
import { DashboardStats, TestRun, Project } from '@/types';
import { TkCard, TkButton } from '@takeoff-ui/react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, 
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend,
  AreaChart, Area
} from 'recharts';
import { format, subDays, startOfDay, endOfDay } from 'date-fns';

export function Reports() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentTests, setRecentTests] = useState<TestRun[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [dateRange, setDateRange] = useState<'7d' | '30d' | '90d'>('7d');

  useEffect(() => {
    loadReportData();
  }, [dateRange]);

  const loadReportData = async () => {
    setIsLoading(true);
    try {
      const [statsData, testsData, projectsData] = await Promise.all([
        apiClient.getDashboardStats(),
        apiClient.getTestRuns({ page_size: 100 }),
        apiClient.getProjects({ page_size: 100 }),
      ]);
      
      setStats(statsData as DashboardStats);
      setRecentTests((testsData as { items: TestRun[] }).items);
      setProjects((projectsData as { items: Project[] }).items);
    } catch (error) {
      console.error('Failed to load report data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Generate time series data for charts
  const generateTimeSeriesData = () => {
    const days = dateRange === '7d' ? 7 : dateRange === '30d' ? 30 : 90;
    const data = [];
    
    for (let i = days - 1; i >= 0; i--) {
      const date = subDays(new Date(), i);
      const dayStart = startOfDay(date);
      const dayEnd = endOfDay(date);
      
      const dayTests = recentTests.filter(t => {
        const testDate = new Date(t.created_at);
        return testDate >= dayStart && testDate <= dayEnd;
      });
      
      data.push({
        date: format(date, 'MMM d'),
        total: dayTests.length,
        successful: dayTests.filter(t => t.status === 'completed').length,
        failed: dayTests.filter(t => t.status === 'failed').length,
      });
    }
    
    return data;
  };

  // Generate project performance data
  const generateProjectData = () => {
    return projects.slice(0, 5).map(project => {
      const projectTests = recentTests.filter(t => t.project_id === project.id);
      const successful = projectTests.filter(t => t.status === 'completed').length;
      const total = projectTests.length;
      
      return {
        name: project.name.slice(0, 15),
        tests: total,
        successRate: total > 0 ? Math.round((successful / total) * 100) : 0,
      };
    });
  };

  const pieData = stats ? [
    { name: 'Successful', value: stats.successful_tests, color: '#22c55e' },
    { name: 'Failed', value: stats.failed_tests, color: '#ef4444' },
    { name: 'Running', value: stats.running_tests, color: '#3b82f6' },
  ].filter(d => d.value > 0) : [];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  const timeSeriesData = generateTimeSeriesData();
  const projectData = generateProjectData();

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Reports & Analytics</h1>
          <p className="text-slate-500 mt-1">Insights into your browser testing performance</p>
        </div>
        <div className="flex gap-2">
          {(['7d', '30d', '90d'] as const).map((range) => (
            <button
              key={range}
              onClick={() => setDateRange(range)}
              className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                dateRange === range
                  ? 'bg-blue-500 text-slate-800'
                  : 'bg-slate-100 text-slate-500 hover:bg-slate-100'
              }`}
            >
              {range === '7d' ? '7 Days' : range === '30d' ? '30 Days' : '90 Days'}
            </button>
          ))}
        </div>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <TkCard>
          <div className="p-6 text-center">
            <p className="text-3xl font-bold text-slate-800">{stats?.total_tests || 0}</p>
            <p className="text-sm text-slate-500 mt-1">Total Tests</p>
          </div>
        </TkCard>
        <TkCard>
          <div className="p-6 text-center">
            <p className="text-3xl font-bold text-green-400">{stats?.successful_tests || 0}</p>
            <p className="text-sm text-slate-500 mt-1">Successful</p>
          </div>
        </TkCard>
        <TkCard>
          <div className="p-6 text-center">
            <p className="text-3xl font-bold text-red-400">{stats?.failed_tests || 0}</p>
            <p className="text-sm text-slate-500 mt-1">Failed</p>
          </div>
        </TkCard>
        <TkCard>
          <div className="p-6 text-center">
            <p className="text-3xl font-bold text-blue-600">{stats?.success_rate?.toFixed(1) || 0}%</p>
            <p className="text-sm text-slate-500 mt-1">Success Rate</p>
          </div>
        </TkCard>
      </div>

      {/* Charts row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Test trend */}
        <TkCard>
          <div className="p-6">
            <h3 className="text-lg font-semibold text-slate-800 mb-4">Test Execution Trend</h3>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={timeSeriesData}>
                  <defs>
                    <linearGradient id="colorSuccessful" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#22c55e" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorFailed" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="date" stroke="#64748b" fontSize={12} />
                  <YAxis stroke="#64748b" fontSize={12} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                    labelStyle={{ color: '#f8fafc' }}
                  />
                  <Area type="monotone" dataKey="successful" stroke="#22c55e" fillOpacity={1} fill="url(#colorSuccessful)" />
                  <Area type="monotone" dataKey="failed" stroke="#ef4444" fillOpacity={1} fill="url(#colorFailed)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </TkCard>

        {/* Results distribution */}
        <TkCard>
          <div className="p-6">
            <h3 className="text-lg font-semibold text-slate-800 mb-4">Results Distribution</h3>
            <div className="h-72">
              {pieData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      {pieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                    />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-slate-500">
                  No data available
                </div>
              )}
            </div>
          </div>
        </TkCard>
      </div>

      {/* Charts row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Project performance */}
        <TkCard>
          <div className="p-6">
            <h3 className="text-lg font-semibold text-slate-800 mb-4">Project Performance</h3>
            <div className="h-72">
              {projectData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={projectData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis type="number" stroke="#64748b" fontSize={12} />
                    <YAxis dataKey="name" type="category" stroke="#64748b" fontSize={12} width={100} />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                    />
                    <Bar dataKey="tests" fill="#0ea5e9" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-slate-500">
                  No project data available
                </div>
              )}
            </div>
          </div>
        </TkCard>

        {/* Success rate by project */}
        <TkCard>
          <div className="p-6">
            <h3 className="text-lg font-semibold text-slate-800 mb-4">Success Rate by Project</h3>
            <div className="h-72">
              {projectData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={projectData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis type="number" domain={[0, 100]} stroke="#64748b" fontSize={12} />
                    <YAxis dataKey="name" type="category" stroke="#64748b" fontSize={12} width={100} />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                      formatter={(value: number) => [`${value}%`, 'Success Rate']}
                    />
                    <Bar dataKey="successRate" fill="#22c55e" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-slate-500">
                  No project data available
                </div>
              )}
            </div>
          </div>
        </TkCard>
      </div>

      {/* Export options */}
      <TkCard>
        <div className="p-6">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">Export Reports</h3>
          <div className="flex gap-4">
            <TkButton
              variant="secondary"
              label="Export as CSV"
              onClick={() => {
                // TODO: Implement CSV export
                alert('CSV export coming soon!');
              }}
            />
            <TkButton
              variant="secondary"
              label="Export as PDF"
              onClick={() => {
                // TODO: Implement PDF export
                alert('PDF export coming soon!');
              }}
            />
          </div>
        </div>
      </TkCard>
    </div>
  );
}
