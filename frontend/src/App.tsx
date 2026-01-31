import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '@/auth/AuthProvider';
import { ProtectedRoute } from '@/auth/ProtectedRoute';
import { MainLayout } from '@/components/layout/MainLayout';

// Pages
import { Login } from '@/pages/Login';
import { Register } from '@/pages/Register';
import { Dashboard } from '@/pages/Dashboard';
import { Projects } from '@/pages/Projects';
import { TestRunner } from '@/pages/TestRunner';
import { TestHistory } from '@/pages/TestHistory';
import { TestDetails } from '@/pages/TestDetails';
import { TestSets } from '@/pages/TestSets';
import { TestSetDetail } from '@/pages/TestSetDetail';
import { ProjectSettings } from '@/pages/ProjectSettings';
import { Schedules } from '@/pages/Schedules';
import { Reports } from '@/pages/Reports';
import { Settings } from '@/pages/Settings';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            {/* Public routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

            {/* Auth callback for OIDC */}
            <Route path="/auth/callback" element={<OIDCCallback />} />

            {/* Protected routes */}
            <Route
              element={
                <ProtectedRoute>
                  <MainLayout />
                </ProtectedRoute>
              }
            >
              <Route path="/" element={<Dashboard />} />
              <Route path="/projects" element={<Projects />} />
              <Route path="/projects/:id/settings" element={<ProjectSettings />} />
              <Route
                path="/tests/run"
                element={
                  <ProtectedRoute requiredRole="developer">
                    <TestRunner />
                  </ProtectedRoute>
                }
              />
              <Route path="/tests" element={<TestHistory />} />
              <Route path="/tests/:id" element={<TestDetails />} />
              <Route path="/test-sets" element={<TestSets />} />
              <Route path="/test-sets/:id" element={<TestSetDetail />} />
              <Route
                path="/schedules"
                element={
                  <ProtectedRoute requiredRole="developer">
                    <Schedules />
                  </ProtectedRoute>
                }
              />
              <Route path="/reports" element={<Reports />} />
              <Route
                path="/settings"
                element={
                  <ProtectedRoute requiredRole="admin">
                    <Settings />
                  </ProtectedRoute>
                }
              />
            </Route>

            {/* Unauthorized page */}
            <Route path="/unauthorized" element={<Unauthorized />} />

            {/* Catch all */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

// OIDC callback handler
function OIDCCallback() {
  const params = new URLSearchParams(window.location.search);
  const accessToken = params.get('access_token');
  const refreshToken = params.get('refresh_token');

  if (accessToken && refreshToken) {
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
    window.location.href = '/';
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900">
      <div className="text-center">
        <div className="w-16 h-16 border-4 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        <p className="text-slate-400">Completing authentication...</p>
      </div>
    </div>
  );
}

// Unauthorized page
function Unauthorized() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900 px-4">
      <div className="text-center">
        <div className="w-20 h-20 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
          <svg className="w-10 h-10 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <h1 className="text-2xl font-bold text-white mb-2">Access Denied</h1>
        <p className="text-slate-400 mb-6">You don't have permission to access this page.</p>
        <a
          href="/"
          className="inline-flex items-center gap-2 px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg font-medium transition-colors"
        >
          Go to Dashboard
        </a>
      </div>
    </div>
  );
}

export default App;
