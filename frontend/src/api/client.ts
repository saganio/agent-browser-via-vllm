import {
  AuthTokens,
  User,
  XrayConfig,
  XrayConfigCreate,
  XrayConfigUpdate,
  XrayTestSet,
  XrayTest,
  XrayStepResult,
  PaginatedResponse,
  SyncTestSetsRequest,
  SyncTestSetsResponse,
  ExecuteTestSetRequest,
  ExecuteTestSetResponse,
  ExecuteTestRequest,
  ExecuteTestResponse,
  ExportResultsResponse,
  TestConnectionRequest,
  TestConnectionResponse,
  XrayDebugInfo,
} from '@/types';

const API_BASE = '/api';

class ApiClient {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;

  constructor() {
    // Load tokens from localStorage on init
    this.accessToken = localStorage.getItem('access_token');
    this.refreshToken = localStorage.getItem('refresh_token');
  }

  setTokens(tokens: AuthTokens) {
    this.accessToken = tokens.access_token;
    this.refreshToken = tokens.refresh_token;
    localStorage.setItem('access_token', tokens.access_token);
    localStorage.setItem('refresh_token', tokens.refresh_token);
  }

  clearTokens() {
    this.accessToken = null;
    this.refreshToken = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }

  getAccessToken(): string | null {
    return this.accessToken;
  }

  isAuthenticated(): boolean {
    return !!this.accessToken;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.accessToken) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${this.accessToken}`;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    // Handle 401 - try to refresh token
    if (response.status === 401 && this.refreshToken) {
      const refreshed = await this.refreshTokens();
      if (refreshed) {
        // Retry the request with new token
        (headers as Record<string, string>)['Authorization'] = `Bearer ${this.accessToken}`;
        const retryResponse = await fetch(`${API_BASE}${endpoint}`, {
          ...options,
          headers,
        });

        if (!retryResponse.ok) {
          throw new ApiError(retryResponse.status, await retryResponse.text());
        }

        return retryResponse.json();
      } else {
        this.clearTokens();
        window.location.href = '/login';
        throw new ApiError(401, 'Session expired');
      }
    }

    if (!response.ok) {
      const errorText = await response.text();
      let errorMessage = errorText;
      try {
        const errorJson = JSON.parse(errorText);
        errorMessage = errorJson.detail || errorJson.message || errorText;
      } catch {
        // Keep original error text
      }
      throw new ApiError(response.status, errorMessage);
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return null as T;
    }

    return response.json();
  }

  private async refreshTokens(): Promise<boolean> {
    if (!this.refreshToken) return false;

    try {
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: this.refreshToken }),
      });

      if (response.ok) {
        const tokens: AuthTokens = await response.json();
        this.setTokens(tokens);
        return true;
      }
    } catch {
      // Refresh failed
    }

    return false;
  }

  // Auth endpoints
  async login(email: string, password: string): Promise<AuthTokens> {
    const tokens = await this.request<AuthTokens>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    this.setTokens(tokens);
    return tokens;
  }

  async register(email: string, password: string, name: string, organizationName?: string): Promise<AuthTokens> {
    const tokens = await this.request<AuthTokens>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, name, organization_name: organizationName }),
    });
    this.setTokens(tokens);
    return tokens;
  }

  async logout(): Promise<void> {
    try {
      await this.request('/auth/logout', { method: 'POST' });
    } finally {
      this.clearTokens();
    }
  }

  async getMe(): Promise<User> {
    return this.request<User>('/auth/me');
  }

  async getOIDCConfig(): Promise<{ configured: boolean; provider: string | null }> {
    return this.request('/auth/oidc/config');
  }

  // Project endpoints
  async getProjects(params?: { page?: number; page_size?: number; search?: string; is_active?: boolean }) {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set('page', params.page.toString());
    if (params?.page_size) searchParams.set('page_size', params.page_size.toString());
    if (params?.search) searchParams.set('search', params.search);
    if (params?.is_active !== undefined) searchParams.set('is_active', params.is_active.toString());

    const query = searchParams.toString();
    return this.request(`/projects${query ? `?${query}` : ''}`);
  }

  async getProject(id: number) {
    return this.request(`/projects/${id}`);
  }

  async getProjectStats(id: number) {
    return this.request(`/projects/${id}/stats`);
  }

  async createProject(data: {
    name: string;
    description?: string;
    vllm_config?: Record<string, unknown>;
    browser_config?: Record<string, unknown>;
  }) {
    return this.request('/projects', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateProject(id: number, data: Record<string, unknown>) {
    return this.request(`/projects/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteProject(id: number, permanent = false) {
    return this.request(`/projects/${id}?permanent=${permanent}`, {
      method: 'DELETE',
    });
  }

  async testVLLMConnection(data: {
    api_url: string;
    model_name: string;
    api_key?: string;
  }) {
    return this.request<{ success: boolean; message: string; model_name?: string }>('/projects/test-vllm-connection', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Test endpoints
  async getTestRuns(params?: { project_id?: number; status?: string; page?: number; page_size?: number }) {
    const searchParams = new URLSearchParams();
    if (params?.project_id) searchParams.set('project_id', params.project_id.toString());
    if (params?.status) searchParams.set('status', params.status);
    if (params?.page) searchParams.set('page', params.page.toString());
    if (params?.page_size) searchParams.set('page_size', params.page_size.toString());

    const query = searchParams.toString();
    return this.request(`/tests${query ? `?${query}` : ''}`);
  }

  async getTestRun(id: number) {
    return this.request(`/tests/${id}`);
  }

  async executeTest(projectId: number, command: string) {
    return this.request('/tests/execute', {
      method: 'POST',
      body: JSON.stringify({ project_id: projectId, command }),
    });
  }

  async cancelTest(id: number) {
    return this.request(`/tests/${id}/cancel`, { method: 'POST' });
  }

  // Schedule endpoints
  async getSchedules(params?: { project_id?: number; enabled?: boolean; page?: number; page_size?: number }) {
    const searchParams = new URLSearchParams();
    if (params?.project_id) searchParams.set('project_id', params.project_id.toString());
    if (params?.enabled !== undefined) searchParams.set('enabled', params.enabled.toString());
    if (params?.page) searchParams.set('page', params.page.toString());
    if (params?.page_size) searchParams.set('page_size', params.page_size.toString());

    const query = searchParams.toString();
    return this.request(`/tests/schedules${query ? `?${query}` : ''}`);
  }

  async createSchedule(data: {
    name: string;
    project_id: number;
    command: string;
    cron_expression: string;
    timezone?: string;
    enabled?: boolean;
  }) {
    return this.request('/tests/schedules', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateSchedule(id: number, data: Record<string, unknown>) {
    return this.request(`/tests/schedules/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteSchedule(id: number) {
    return this.request(`/tests/schedules/${id}`, { method: 'DELETE' });
  }

  // Notification endpoints
  async getNotificationChannels(params?: { enabled?: boolean; page?: number; page_size?: number }) {
    const searchParams = new URLSearchParams();
    if (params?.enabled !== undefined) searchParams.set('enabled', params.enabled.toString());
    if (params?.page) searchParams.set('page', params.page.toString());
    if (params?.page_size) searchParams.set('page_size', params.page_size.toString());

    const query = searchParams.toString();
    return this.request(`/notifications/channels${query ? `?${query}` : ''}`);
  }

  async createNotificationChannel(data: {
    name: string;
    channel_type: string;
    config: Record<string, unknown>;
    notify_on?: string[];
    enabled?: boolean;
  }) {
    return this.request('/notifications/channels', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateNotificationChannel(id: number, data: Record<string, unknown>) {
    return this.request(`/notifications/channels/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteNotificationChannel(id: number) {
    return this.request(`/notifications/channels/${id}`, { method: 'DELETE' });
  }

  async testNotificationChannel(id: number, message?: string, title?: string) {
    return this.request(`/notifications/channels/${id}/test`, {
      method: 'POST',
      body: JSON.stringify({ message, title }),
    });
  }

  async getNotificationEvents() {
    return this.request('/notifications/events');
  }

  // Dashboard
  async getDashboardStats() {
    return this.request('/dashboard/stats');
  }

  // Health
  async healthCheck() {
    return this.request('/health');
  }

  // ==================== Xray endpoints ====================

  // Xray Config
  async getXrayConfig(projectId: number): Promise<XrayConfig> {
    return this.request<XrayConfig>(`/xray/config/${projectId}`);
  }

  async createXrayConfig(data: XrayConfigCreate): Promise<XrayConfig> {
    return this.request<XrayConfig>('/xray/config', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateXrayConfig(projectId: number, data: XrayConfigUpdate): Promise<XrayConfig> {
    return this.request<XrayConfig>(`/xray/config/${projectId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteXrayConfig(projectId: number): Promise<void> {
    return this.request(`/xray/config/${projectId}`, { method: 'DELETE' });
  }

  async testXrayConnection(data: TestConnectionRequest): Promise<TestConnectionResponse> {
    return this.request<TestConnectionResponse>('/xray/config/test-connection', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Xray Sync
  async syncTestSets(projectId: number, data?: SyncTestSetsRequest): Promise<SyncTestSetsResponse> {
    return this.request<SyncTestSetsResponse>(`/xray/sync/${projectId}`, {
      method: 'POST',
      body: JSON.stringify(data || {}),
    });
  }

  async debugXrayConnection(projectId: number): Promise<XrayDebugInfo> {
    return this.request<XrayDebugInfo>(`/xray/debug/${projectId}`);
  }

  // Xray Test Sets
  async getXrayTestSets(params: {
    project_id: number;
    page?: number;
    page_size?: number;
    search?: string;
  }): Promise<PaginatedResponse<XrayTestSet>> {
    const searchParams = new URLSearchParams();
    searchParams.set('project_id', params.project_id.toString());
    if (params.page) searchParams.set('page', params.page.toString());
    if (params.page_size) searchParams.set('page_size', params.page_size.toString());
    if (params.search) searchParams.set('search', params.search);

    return this.request<PaginatedResponse<XrayTestSet>>(`/xray/test-sets?${searchParams.toString()}`);
  }

  async getXrayTestSet(testSetId: number): Promise<XrayTestSet> {
    return this.request<XrayTestSet>(`/xray/test-sets/${testSetId}`);
  }

  async getXrayTestsInTestSet(testSetId: number, params?: {
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<XrayTest>> {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set('page', params.page.toString());
    if (params?.page_size) searchParams.set('page_size', params.page_size.toString());

    const query = searchParams.toString();
    return this.request<PaginatedResponse<XrayTest>>(`/xray/test-sets/${testSetId}/tests${query ? `?${query}` : ''}`);
  }

  // Xray Tests
  async getXrayTest(testId: number): Promise<XrayTest> {
    return this.request<XrayTest>(`/xray/tests/${testId}`);
  }

  async getXrayTestCommand(testId: number): Promise<{ command: string }> {
    return this.request<{ command: string }>(`/xray/tests/${testId}/command`);
  }

  // Xray Execution
  async executeXrayTestSet(data: ExecuteTestSetRequest): Promise<ExecuteTestSetResponse> {
    return this.request<ExecuteTestSetResponse>('/xray/execute/test-set', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async executeXrayTest(data: ExecuteTestRequest): Promise<ExecuteTestResponse> {
    return this.request<ExecuteTestResponse>('/xray/execute/test', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Xray Export
  async exportXrayResults(testRunId: number, comment?: string): Promise<ExportResultsResponse> {
    return this.request<ExportResultsResponse>(`/xray/export/${testRunId}`, {
      method: 'POST',
      body: JSON.stringify({ test_run_id: testRunId, comment }),
    });
  }

  async getXrayStepResults(testRunId: number): Promise<{ test_run_id: number; step_results: XrayStepResult[] }> {
    return this.request(`/xray/step-results/${testRunId}`);
  }
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

export const apiClient = new ApiClient();
