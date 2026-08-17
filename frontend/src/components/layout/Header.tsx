import { useState, useRef, useEffect } from 'react';
import { useAuth } from '@/auth/AuthProvider';
import { useTheme } from '@/context/ThemeProvider';
import { useNavigate } from 'react-router-dom';

export function Header() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'admin':
        return 'bg-purple-500/15 text-purple-400 border-purple-500/30';
      case 'developer':
        return 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30';
      default:
        return 'bg-slate-500/15 text-slate-400 border-slate-500/30';
    }
  };

  return (
    <header className="h-16 glass-nav flex items-center justify-between px-6 z-10 sticky top-0">
      {/* Search Bar */}
      <div className="flex-1 max-w-md">
        <div className="relative">
          <svg
            className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <input
            type="text"
            placeholder="Search test runs, projects, suites..."
            className="w-full pl-10 pr-12 py-2 bg-slate-900/90 dark:bg-slate-900/90 light:bg-white border border-slate-800 dark:border-slate-800 light:border-slate-200 rounded-xl text-sm text-slate-200 light:text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 transition-all font-mono"
          />
          <kbd className="absolute right-3 top-1/2 -translate-y-1/2 px-1.5 py-0.5 bg-slate-800 dark:bg-slate-800 light:bg-slate-100 border border-slate-700 dark:border-slate-700 light:border-slate-200 rounded text-[10px] font-mono text-slate-400 light:text-slate-600">
            ⌘K
          </kbd>
        </div>
      </div>

      {/* Right Action Bar */}
      <div className="flex items-center gap-3">
        {/* Theme Toggle Button (Sun / Moon) */}
        <button
          onClick={toggleTheme}
          className="p-2.5 rounded-xl bg-slate-900/60 light:bg-slate-100 hover:bg-slate-800 light:hover:bg-slate-200 border border-slate-800/80 light:border-slate-300 text-slate-300 light:text-slate-700 transition-all flex items-center justify-center"
          title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
        >
          {theme === 'dark' ? (
            /* Sun Icon for Light Mode Switch */
            <svg className="w-4 h-4 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          ) : (
            /* Moon Icon for Dark Mode Switch */
            <svg className="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
            </svg>
          )}
        </button>

        {/* System Health Pulse */}
        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900/60 light:bg-slate-100 border border-slate-800/80 light:border-slate-200 text-xs font-mono">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span className="text-slate-400 light:text-slate-600">Worker Status:</span>
          <span className="text-emerald-500 font-semibold">Ready</span>
        </div>

        {/* Quick Launch Test Button */}
        <button
          onClick={() => navigate('/tests/run')}
          className="hidden sm:flex items-center gap-2 px-3.5 py-1.5 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white text-xs font-medium rounded-xl shadow-lg shadow-blue-500/20 transition-all duration-200 font-mono"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
          </svg>
          New Run
        </button>

        {/* User Account Menu */}
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setShowDropdown(!showDropdown)}
            className="flex items-center gap-3 p-1 rounded-xl hover:bg-slate-900/80 light:hover:bg-slate-100 border border-transparent hover:border-slate-800 light:hover:border-slate-300 transition-all"
          >
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 via-cyan-500 to-emerald-500 rounded-lg flex items-center justify-center text-white font-mono font-bold text-sm shadow-md">
              {user?.name?.charAt(0).toUpperCase() || user?.email?.charAt(0).toUpperCase() || 'U'}
            </div>
            <div className="text-left hidden sm:block">
              <p className="text-xs font-semibold text-slate-200 light:text-slate-800">{user?.name || 'User'}</p>
              <p className="text-[11px] text-slate-400 light:text-slate-500 font-mono">{user?.email}</p>
            </div>
            <svg
              className={`w-4 h-4 text-slate-400 transition-transform ${showDropdown ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {showDropdown && (
            <div className="absolute right-0 mt-2 w-64 bg-slate-900 light:bg-white border border-slate-800 light:border-slate-200 rounded-2xl shadow-2xl z-50 overflow-hidden animate-fade-in">
              <div className="p-4 border-b border-slate-800/80 light:border-slate-200 bg-slate-950/60 light:bg-slate-50">
                <p className="text-sm font-semibold text-white light:text-slate-900">{user?.name}</p>
                <p className="text-xs text-slate-400 light:text-slate-500 font-mono mt-0.5">{user?.email}</p>
                <span
                  className={`inline-block mt-2.5 px-2.5 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wider rounded-full border ${getRoleBadgeColor(
                    user?.role || 'viewer'
                  )}`}
                >
                  {user?.role}
                </span>
              </div>
              <div className="p-2 space-y-1">
                <button
                  onClick={() => {
                    setShowDropdown(false);
                    navigate('/settings');
                  }}
                  className="w-full flex items-center gap-3 px-3 py-2 text-xs font-medium text-slate-300 light:text-slate-700 hover:bg-slate-800/80 light:hover:bg-slate-100 rounded-xl transition-colors"
                >
                  <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                    />
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                    />
                  </svg>
                  Account Settings
                </button>
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-3 px-3 py-2 text-xs font-medium text-red-400 light:text-red-600 hover:bg-red-500/10 light:hover:bg-red-50 rounded-xl transition-colors"
                >
                  <svg className="w-4 h-4 text-red-400 light:text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                    />
                  </svg>
                  Sign out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
