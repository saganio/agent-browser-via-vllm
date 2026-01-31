// User and Auth types
export interface User {
  id: number;
  email: string;
  name: string | null;
  role: 'admin' | 'developer' | 'viewer';
  organization_id: number;
  organization_name: string | null;
  avatar_url: string | null;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

// Organization types
export interface Organization {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  max_concurrent_tests: number;
  max_projects: number;
  is_active: boolean;
  created_at: string;
}

// Project types
export interface VLLMConfig {
  api_url: string;
  model_name: string;
  api_key?: string;
  temperature: number;
  max_tokens: number;
  top_p: number;
}

export interface BrowserConfig {
  headless: boolean;
  timeout: number;
  viewport?: { width: number; height: number };
  user_agent?: string;
}

export interface Project {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  organization_id: number;
  created_by: number;
  created_by_name: string | null;
  vllm_config: VLLMConfig;
  browser_config: BrowserConfig;
  default_commands: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
  test_run_count?: number;
  last_test_run?: string;
}

export interface ProjectStats {
  total_runs: number;
  successful_runs: number;
  failed_runs: number;
  success_rate: number;
  last_run_at: string | null;
  last_run_status: TestStatus | null;
}

// Test types
export type TestStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface TestRun {
  id: number;
  project_id: number;
  project_name: string | null;
  command: string;
  status: TestStatus;
  triggered_by: number | null;
  triggered_by_name: string | null;
  trigger_type: string;
  worker_id: string | null;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  error_message: string | null;
  created_at: string;
}

export interface TestResult {
  id: number;
  test_run_id: number;
  sequence: number;
  step_type: string;
  tool_name: string | null;
  content: string | null;
  data: Record<string, unknown>;
  success: boolean;
  error_message: string | null;
  screenshot_path: string | null;
  duration_ms: number | null;
  created_at: string;
}

export interface TestRunDetail extends TestRun {
  results: TestResult[];
}

// Schedule types
export interface Schedule {
  id: number;
  project_id: number;
  project_name: string | null;
  name: string;
  command: string;
  cron_expression: string;
  timezone: string;
  enabled: boolean;
  last_run_at: string | null;
  last_run_status: TestStatus | null;
  next_run_at: string | null;
  run_count: number;
  created_at: string;
  updated_at: string | null;
}

// Notification types
export type ChannelType = 'email' | 'slack' | 'webhook' | 'discord';

export interface NotificationChannel {
  id: number;
  organization_id: number;
  name: string;
  channel_type: ChannelType;
  config: Record<string, unknown>;
  notify_on: string[];
  enabled: boolean;
  created_at: string;
  updated_at: string | null;
}

// API response types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface DashboardStats {
  organizations: number;
  projects: number;
  total_tests: number;
  successful_tests: number;
  failed_tests: number;
  running_tests: number;
  success_rate: number;
}

// WebSocket message types
export interface WSMessage {
  type: 'status' | 'tool_call' | 'tool_result' | 'llm_response' | 'error' | 'complete' | 'ping' | 'cancelled' | 'viewport_update';
  test_run_id: number;
  sequence?: number;
  data: Record<string, unknown>;
  timestamp?: string;
}

// ==================== Xray Types ====================

export type XrayInstanceType = 'cloud' | 'server';
export type XrayTestType = 'manual' | 'gherkin';
export type XraySyncStatus = 'pending' | 'syncing' | 'synced' | 'failed';
export type XrayExportStatus = 'pending' | 'exporting' | 'exported' | 'failed' | 'skipped';
export type XrayStepStatus = 'pending' | 'passed' | 'failed' | 'skipped' | 'blocked';

export interface XrayConfig {
  id: number;
  project_id: number;
  instance_type: XrayInstanceType;
  base_url: string;
  jira_project_key: string;
  has_cloud_credentials: boolean;
  has_server_credentials: boolean;
  auto_sync: boolean;
  auto_export: boolean;
  sync_interval_minutes: number;
  last_sync_at: string | null;
  last_sync_status: XraySyncStatus | null;
  last_sync_error: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface XrayConfigCreate {
  project_id: number;
  instance_type: XrayInstanceType;
  base_url: string;
  client_id?: string;
  client_secret?: string;
  username?: string;
  api_token?: string;
  jira_project_key: string;
  auto_sync?: boolean;
  auto_export?: boolean;
  sync_interval_minutes?: number;
}

export interface XrayConfigUpdate {
  instance_type?: XrayInstanceType;
  base_url?: string;
  client_id?: string;
  client_secret?: string;
  username?: string;
  api_token?: string;
  jira_project_key?: string;
  auto_sync?: boolean;
  auto_export?: boolean;
  sync_interval_minutes?: number;
  is_active?: boolean;
}

export interface XrayTestSet {
  id: number;
  xray_config_id: number;
  xray_issue_key: string;
  xray_issue_id: string | null;
  name: string;
  description: string | null;
  sync_status: XraySyncStatus;
  last_synced_at: string | null;
  labels: string[];
  components: string[];
  fix_versions: string[];
  test_count: number;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface ManualStep {
  index: number;
  action: string;
  data?: string;
  expected?: string;
}

export interface XrayTest {
  id: number;
  test_set_id: number;
  xray_issue_key: string;
  xray_issue_id: string | null;
  name: string;
  description: string | null;
  test_type: XrayTestType;
  manual_steps: ManualStep[];
  gherkin_scenario: string | null;
  preconditions: string | null;
  priority: string | null;
  labels: string[];
  rank: number;
  step_count: number;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface XrayStepResult {
  id: number;
  xray_test_id: number;
  test_run_id: number;
  step_index: number;
  step_action: string | null;
  step_expected: string | null;
  status: XrayStepStatus;
  actual_result: string | null;
  screenshot_path: string | null;
  comment: string | null;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  export_status: XrayExportStatus;
  xray_execution_id: string | null;
  exported_at: string | null;
  export_error: string | null;
  created_at: string;
}

export interface SyncTestSetsRequest {
  test_set_keys?: string[];
  force?: boolean;
}

export interface SyncTestSetsResponse {
  success: boolean;
  message: string;
  synced_count: number;
  failed_count: number;
  errors: string[];
  debug_info?: {
    project_key: string;
    instance_type: string;
    test_sets_found: number;
  };
}

export interface XrayDebugInfo {
  project_key: string;
  instance_type: string;
  base_url: string;
  auth_status?: 'success' | 'failed';
  auth_error?: string;
  all_issue_types?: string[];
  xray_related_types?: string[];
  issue_types_error?: string;
  search_results?: Record<string, { count?: number; sample?: { key: string; summary: string }[]; error?: string }>;
}

export interface ExecuteTestSetRequest {
  test_set_id: number;
  test_ids?: number[];
  auto_export?: boolean;
}

export interface ExecuteTestRequest {
  xray_test_id: number;
  auto_export?: boolean;
}

export interface ExportResultsResponse {
  success: boolean;
  xray_execution_key: string | null;
  message: string;
  exported_count: number;
  failed_count: number;
}

export interface TestConnectionRequest {
  instance_type: XrayInstanceType;
  base_url: string;
  client_id?: string;
  client_secret?: string;
  username?: string;
  api_token?: string;
  jira_project_key: string;
}

export interface TestConnectionResponse {
  success: boolean;
  message: string;
  xray_version?: string;
  project_name?: string;
}

export interface ExecuteTestSetResponse {
  message: string;
  test_set_key: string;
  test_runs: {
    test_run_id: number;
    xray_test_id: number;
    xray_test_key: string;
    test_name: string;
  }[];
  auto_export: boolean;
}

export interface ExecuteTestResponse {
  test_run_id: number;
  xray_test_id: number;
  xray_test_key: string;
  command: string;
  auto_export: boolean;
}
