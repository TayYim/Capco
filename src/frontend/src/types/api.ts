// API-related TypeScript types

export interface ApiError {
  detail: string
  status_code?: number
}

export interface ApiResponse<T = any> {
  data?: T
  message?: string
  errors?: ApiError[]
}

// Configuration types
export interface ParameterRange {
  parameter_name: string
  min_value: number
  max_value: number
  default_value?: number
  description?: string
  unit?: string
  scenario_type?: string
}

export interface SystemConfiguration {
  carla_path: string
  default_timeout: number
  restart_gap: number
  max_concurrent_experiments: number
  default_iterations: number
  default_search_method: string
  default_reward_function: string
  output_directory: string
  max_file_size: number
  cleanup_after_days: number
  enable_headless: boolean
  log_level: string
  enable_authentication: boolean
  session_timeout: number
}

export interface ConfigurationUpdate {
  carla_path?: string
  default_timeout?: number
  max_concurrent_experiments?: number
  default_iterations?: number
  default_search_method?: string
  default_reward_function?: string
  log_level?: string
  cleanup_after_days?: number
}

export interface ConfigurationStatus {
  is_valid: boolean
  carla_available: boolean
  parameter_ranges_loaded: boolean
  output_directory_writable: boolean
  errors: string[]
  warnings: string[]
}

export interface ParameterRangeUpdate {
  ranges: Record<string, [number, number]>
  scenario_type?: string
  apply_globally: boolean
}

export interface RewardFunctionConfig {
  name: string
  description: string
  parameters: Record<string, any>
  is_default: boolean
  is_active: boolean
}

export interface SearchMethodConfig {
  name: string
  description: string
  default_parameters: Record<string, any>
  parameter_ranges: Record<string, [number, number]>
  is_available: boolean
  requires_library?: string
}

export interface SystemInfo {
  version: string
  carla_version?: string
  python_version: string
  available_search_methods: SearchMethodConfig[]
  available_reward_functions: RewardFunctionConfig[]
  system_status: ConfigurationStatus
  uptime: number
  active_experiments: number
}

// File-related types
export interface FileInfo {
  name: string
  size: number
  modified: string
  type: string
}

export interface FilePreview {
  filename: string
  content: string
  is_truncated: boolean
  total_lines: number
  displayed_lines: number
}

export interface ExperimentAnalysis {
  experiment_id: string
  summary: {
    total_iterations: number
    collision_rate: number
    average_reward: number
    best_reward: number
    total_duration: number
  }
  trends: {
    reward_over_time: Array<{ iteration: number; reward: number }>
    collision_distribution: Record<string, number>
  }
  parameters: {
    best_parameters: Record<string, number>
    parameter_correlations: Record<string, number>
  }
} 