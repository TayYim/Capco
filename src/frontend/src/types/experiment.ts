// Experiment-related TypeScript types
// These should match the backend Pydantic models

export type ExperimentStatus = 'created' | 'running' | 'completed' | 'failed' | 'stopped'

export type SearchMethod = 'random' | 'pso' | 'ga'

export type RewardFunction = 'collision' | 'distance' | 'safety_margin' | 'ttc' | 'ttc_div_dist' | 'weighted_multi'

export interface ExperimentConfig {
  name: string
  route_id: string
  route_file: string
  search_method: SearchMethod
  num_iterations: number
  timeout_seconds: number
  headless: boolean
  random_seed: number
  reward_function: RewardFunction
  parameter_overrides?: Record<string, [number, number]>
  
  // Search method specific parameters
  pso_pop_size?: number
  pso_w?: number
  pso_c1?: number
  pso_c2?: number
  ga_pop_size?: number
  ga_prob_mut?: number
}

export interface ProgressInfo {
  // Optimization-level tracking (PSO/GA iterations)
  current_iteration: number
  total_iterations: number
  
  // Scenario-level tracking (actual CARLA simulations)
  scenarios_executed: number
  total_scenarios: number
  scenarios_this_iteration: number
  
  // Results tracking
  best_reward?: number
  collision_found: boolean
  elapsed_time?: number
  estimated_remaining?: number
  recent_rewards: number[]
  
  // Method-specific information
  search_method: string
  population_size?: number
  
  // Computed progress percentages (from backend properties)
  iteration_progress_percentage?: number
  scenario_progress_percentage?: number
}

export interface ExperimentData {
  id: string
  name: string
  status: ExperimentStatus
  config: ExperimentConfig
  progress?: ProgressInfo
  created_at: string
  started_at?: string
  completed_at?: string
  error_message?: string
  output_directory?: string
}

export interface CollisionInfo {
  ego_x: number
  ego_y: number
  ego_velocity: number
  ego_yaw: number
  npc_x: number
  npc_y: number
  npc_velocity: number
  npc_yaw: number
}

export interface ExperimentResult {
  experiment_id: string
  final_status: ExperimentStatus
  total_iterations: number
  best_reward?: number
  best_parameters?: Record<string, number>
  collision_found: boolean
  collision_details?: CollisionInfo
  total_duration?: number
  average_iteration_time?: number
  min_reward?: number
  max_reward?: number
  mean_reward?: number
  std_reward?: number
  result_files: string[]
  output_directory?: string
}

export interface ExperimentListItem {
  id: string
  name: string
  route_id: string
  route_file: string
  search_method: string
  status: ExperimentStatus
  created_at: string
  completed_at?: string
  collision_found?: boolean
  best_reward?: number
  total_iterations?: number
}

export interface ExperimentCreate {
  config: ExperimentConfig
  start_immediately: boolean
}

export interface ExperimentUpdate {
  notes?: string
  tags?: string[]
}

// WebSocket message types for real-time updates
export interface LogMessage {
  type: 'log'
  experiment_id: string
  level: string
  message: string
  timestamp: number
}

export interface ProgressMessage {
  type: 'progress'
  experiment_id: string
  data: ProgressInfo
  timestamp: number
}

export interface ConnectionMessage {
  type: 'connection'
  status: 'connected' | 'disconnected'
  experiment_id: string
  message: string
}

export type WebSocketMessage = LogMessage | ProgressMessage | ConnectionMessage 