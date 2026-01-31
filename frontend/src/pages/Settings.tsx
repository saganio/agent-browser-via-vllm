import { useState, useEffect } from 'react';
import { apiClient } from '@/api/client';
import { useAuth } from '@/auth/AuthProvider';
import { NotificationChannel, ChannelType } from '@/types';
import { TkButton, TkCard } from '@takeoff-ui/react';

export function Settings() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('profile');
  const [channels, setChannels] = useState<NotificationChannel[]>([]);
  const [, setIsLoading] = useState(false);
  
  // Profile form
  const [profileForm, setProfileForm] = useState({
    name: user?.name || '',
    email: user?.email || '',
  });

  // OIDC config
  const [oidcConfig, setOidcConfig] = useState({
    configured: false,
    provider: null as string | null,
  });

  // New notification channel form
  const [showAddChannel, setShowAddChannel] = useState(false);
  const [newChannel, setNewChannel] = useState({
    name: '',
    channel_type: 'slack' as ChannelType,
    config: {} as Record<string, string>,
    notify_on: ['test_completed', 'test_failed'],
  });

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    setIsLoading(true);
    try {
      const [oidc, channelsData] = await Promise.all([
        apiClient.getOIDCConfig(),
        apiClient.getNotificationChannels(),
      ]);
      
      setOidcConfig(oidc);
      setChannels((channelsData as { items: NotificationChannel[] }).items);
    } catch (error) {
      console.error('Failed to load settings:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveProfile = async () => {
    // TODO: Implement profile update
    alert('Profile update coming soon!');
  };

  const handleAddChannel = async () => {
    try {
      await apiClient.createNotificationChannel({
        name: newChannel.name,
        channel_type: newChannel.channel_type,
        config: newChannel.config,
        notify_on: newChannel.notify_on,
      });
      
      setShowAddChannel(false);
      setNewChannel({
        name: '',
        channel_type: 'slack',
        config: {},
        notify_on: ['test_completed', 'test_failed'],
      });
      loadSettings();
    } catch (error) {
      console.error('Failed to add channel:', error);
    }
  };

  const handleDeleteChannel = async (id: number) => {
    if (!confirm('Are you sure you want to delete this notification channel?')) return;
    
    try {
      await apiClient.deleteNotificationChannel(id);
      loadSettings();
    } catch (error) {
      console.error('Failed to delete channel:', error);
    }
  };

  const handleTestChannel = async (id: number) => {
    try {
      await apiClient.testNotificationChannel(id);
      alert('Test notification sent!');
    } catch (error) {
      alert('Failed to send test notification');
    }
  };

  const getChannelConfigFields = (type: ChannelType) => {
    switch (type) {
      case 'slack':
        return [
          { key: 'webhook_url', label: 'Webhook URL', placeholder: 'https://hooks.slack.com/...' },
          { key: 'channel', label: 'Channel (optional)', placeholder: '#alerts' },
        ];
      case 'email':
        return [
          { key: 'smtp_host', label: 'SMTP Host', placeholder: 'smtp.gmail.com' },
          { key: 'smtp_port', label: 'SMTP Port', placeholder: '587' },
          { key: 'username', label: 'Username', placeholder: 'user@example.com' },
          { key: 'password', label: 'Password', placeholder: '••••••••', type: 'password' },
          { key: 'from_email', label: 'From Email', placeholder: 'noreply@example.com' },
          { key: 'to_emails', label: 'To Emails (comma-separated)', placeholder: 'team@example.com' },
        ];
      case 'webhook':
        return [
          { key: 'url', label: 'Webhook URL', placeholder: 'https://api.example.com/webhook' },
          { key: 'auth_token', label: 'Auth Token (optional)', placeholder: 'Bearer token' },
        ];
      case 'discord':
        return [
          { key: 'webhook_url', label: 'Discord Webhook URL', placeholder: 'https://discord.com/api/webhooks/...' },
        ];
      default:
        return [];
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Settings</h1>
        <p className="text-slate-500 mt-1">Manage your account and organization settings</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-200 pb-2">
        {['profile', 'notifications', 'organization', 'security'].map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              activeTab === tab
                ? 'bg-blue-500/20 text-blue-600'
                : 'text-slate-500 hover:text-slate-700 hover:bg-slate-100'
            }`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Profile tab */}
      {activeTab === 'profile' && (
        <TkCard>
          <div className="p-6 space-y-6">
            <h3 className="text-lg font-semibold text-slate-800">Profile Settings</h3>
            
            <div className="flex items-center gap-6">
              <div className="w-20 h-20 bg-gradient-to-br from-primary-500 to-accent-500 rounded-full flex items-center justify-center text-slate-800 text-2xl font-bold">
                {user?.name?.charAt(0).toUpperCase() || 'U'}
              </div>
              <div>
                <TkButton variant="secondary" label="Change Avatar" />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-600 mb-2">Name</label>
                <input
                  type="text"
                  value={profileForm.name}
                  onChange={(e) => setProfileForm(p => ({ ...p, name: e.target.value }))}
                  className="w-full px-3 py-2 bg-slate-100 border border-slate-300 rounded-lg text-slate-700 focus:outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-600 mb-2">Email</label>
                <input
                  type="email"
                  value={profileForm.email}
                  onChange={(e) => setProfileForm(p => ({ ...p, email: e.target.value }))}
                  disabled
                  className="w-full px-3 py-2 bg-slate-100 border border-slate-300 rounded-lg text-slate-500 cursor-not-allowed"
                />
              </div>
            </div>

            <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
              <div>
                <p className="text-sm font-medium text-slate-700">Role</p>
                <p className="text-xs text-slate-500">{user?.role?.toUpperCase()}</p>
              </div>
              <span className={`px-3 py-1 text-sm font-medium rounded ${
                user?.role === 'admin' ? 'bg-red-500/20 text-red-400' :
                user?.role === 'developer' ? 'bg-blue-500/20 text-blue-400' :
                'bg-slate-500/20 text-slate-500'
              }`}>
                {user?.role}
              </span>
            </div>

            <TkButton variant="primary" label="Save Changes" onClick={handleSaveProfile} />
          </div>
        </TkCard>
      )}

      {/* Notifications tab */}
      {activeTab === 'notifications' && (
        <div className="space-y-6">
          <TkCard>
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold text-slate-800">Notification Channels</h3>
                <TkButton
                  variant="primary"
                  label="Add Channel"
                  onClick={() => setShowAddChannel(true)}
                />
              </div>

              {channels.length > 0 ? (
                <div className="space-y-4">
                  {channels.map((channel) => (
                    <div
                      key={channel.id}
                      className="flex items-center justify-between p-4 bg-slate-50 rounded-lg"
                    >
                      <div className="flex items-center gap-4">
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                          channel.channel_type === 'slack' ? 'bg-purple-500/20' :
                          channel.channel_type === 'email' ? 'bg-blue-500/20' :
                          channel.channel_type === 'discord' ? 'bg-indigo-500/20' :
                          'bg-slate-500/20'
                        }`}>
                          {channel.channel_type === 'slack' && (
                            <svg className="w-5 h-5 text-purple-400" viewBox="0 0 24 24" fill="currentColor">
                              <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zM18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zM15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z"/>
                            </svg>
                          )}
                          {channel.channel_type === 'email' && (
                            <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                            </svg>
                          )}
                          {channel.channel_type === 'webhook' && (
                            <svg className="w-5 h-5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                            </svg>
                          )}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-slate-700">{channel.name}</p>
                          <p className="text-xs text-slate-500">{channel.channel_type}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className={`px-2 py-0.5 text-xs rounded ${
                          channel.enabled ? 'bg-green-500/20 text-green-400' : 'bg-slate-500/20 text-slate-500'
                        }`}>
                          {channel.enabled ? 'Active' : 'Disabled'}
                        </span>
                        <TkButton
                          variant="secondary"
                          label="Test"
                          onClick={() => handleTestChannel(channel.id)}
                        />
                        <button
                          onClick={() => handleDeleteChannel(channel.id)}
                          className="p-2 text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-slate-500">
                  No notification channels configured
                </div>
              )}
            </div>
          </TkCard>

          {/* Add Channel Modal */}
          {showAddChannel && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
              <div className="bg-white rounded-xl border border-slate-200 w-full max-w-lg animate-slide-up">
                <div className="p-6 border-b border-slate-200">
                  <h2 className="text-xl font-semibold text-slate-800">Add Notification Channel</h2>
                </div>
                
                <div className="p-6 space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-600 mb-2">Channel Name</label>
                    <input
                      type="text"
                      value={newChannel.name}
                      onChange={(e) => setNewChannel(c => ({ ...c, name: e.target.value }))}
                      placeholder="My Slack Channel"
                      className="w-full px-3 py-2 bg-slate-100 border border-slate-300 rounded-lg text-slate-700 placeholder-slate-400 focus:outline-none focus:border-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-600 mb-2">Channel Type</label>
                    <select
                      value={newChannel.channel_type}
                      onChange={(e) => setNewChannel(c => ({ ...c, channel_type: e.target.value as ChannelType, config: {} }))}
                      className="w-full px-3 py-2 bg-slate-100 border border-slate-300 rounded-lg text-slate-700"
                    >
                      <option value="slack">Slack</option>
                      <option value="email">Email</option>
                      <option value="webhook">Webhook</option>
                      <option value="discord">Discord</option>
                    </select>
                  </div>

                  {getChannelConfigFields(newChannel.channel_type).map((field) => (
                    <div key={field.key}>
                      <label className="block text-sm font-medium text-slate-600 mb-2">{field.label}</label>
                      <input
                        type={field.type || 'text'}
                        value={newChannel.config[field.key] || ''}
                        onChange={(e) => setNewChannel(c => ({
                          ...c,
                          config: { ...c.config, [field.key]: e.target.value }
                        }))}
                        placeholder={field.placeholder}
                        className="w-full px-3 py-2 bg-slate-100 border border-slate-300 rounded-lg text-slate-700 placeholder-slate-400 focus:outline-none focus:border-blue-500"
                      />
                    </div>
                  ))}
                </div>

                <div className="p-6 border-t border-slate-200 flex justify-end gap-3">
                  <TkButton
                    variant="secondary"
                    label="Cancel"
                    onClick={() => setShowAddChannel(false)}
                  />
                  <TkButton
                    variant="primary"
                    label="Add Channel"
                    onClick={handleAddChannel}
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Organization tab */}
      {activeTab === 'organization' && (
        <TkCard>
          <div className="p-6 space-y-6">
            <h3 className="text-lg font-semibold text-slate-800">Organization Settings</h3>
            
            <div className="p-4 bg-slate-50 rounded-lg">
              <p className="text-sm font-medium text-slate-700">{user?.organization_name}</p>
              <p className="text-xs text-slate-500 mt-1">Organization ID: {user?.organization_id}</p>
            </div>

            <div className="space-y-4">
              <h4 className="text-sm font-medium text-slate-600">Team Members</h4>
              <p className="text-sm text-slate-500">Team management coming soon...</p>
            </div>
          </div>
        </TkCard>
      )}

      {/* Security tab */}
      {activeTab === 'security' && (
        <div className="space-y-6">
          <TkCard>
            <div className="p-6 space-y-6">
              <h3 className="text-lg font-semibold text-slate-800">Authentication</h3>
              
              <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
                <div>
                  <p className="text-sm font-medium text-slate-700">OIDC Single Sign-On</p>
                  <p className="text-xs text-slate-500">
                    {oidcConfig.configured ? `Connected to ${oidcConfig.provider}` : 'Not configured'}
                  </p>
                </div>
                <span className={`px-3 py-1 text-sm rounded ${
                  oidcConfig.configured ? 'bg-green-500/20 text-green-400' : 'bg-slate-500/20 text-slate-500'
                }`}>
                  {oidcConfig.configured ? 'Connected' : 'Not Connected'}
                </span>
              </div>

              <div>
                <h4 className="text-sm font-medium text-slate-600 mb-3">Change Password</h4>
                <div className="space-y-3">
                  <input type="password" placeholder="Current password" className="w-full px-3 py-2 bg-slate-100 border border-slate-300 rounded-lg text-slate-700 placeholder-slate-400 focus:outline-none focus:border-blue-500" />
                  <input type="password" placeholder="New password" className="w-full px-3 py-2 bg-slate-100 border border-slate-300 rounded-lg text-slate-700 placeholder-slate-400 focus:outline-none focus:border-blue-500" />
                  <input type="password" placeholder="Confirm new password" className="w-full px-3 py-2 bg-slate-100 border border-slate-300 rounded-lg text-slate-700 placeholder-slate-400 focus:outline-none focus:border-blue-500" />
                </div>
                <TkButton variant="primary" label="Update Password" style={{ marginTop: '1rem' }} />
              </div>
            </div>
          </TkCard>

          <TkCard>
            <div className="p-6">
              <h3 className="text-lg font-semibold text-red-400 mb-4">Danger Zone</h3>
              <div className="flex items-center justify-between p-4 border border-red-500/30 rounded-lg">
                <div>
                  <p className="text-sm font-medium text-slate-700">Delete Account</p>
                  <p className="text-xs text-slate-500">Permanently delete your account and all data</p>
                </div>
                <TkButton variant="secondary" label="Delete Account" />
              </div>
            </div>
          </TkCard>
        </div>
      )}
    </div>
  );
}
