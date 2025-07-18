// Scenario-related TypeScript types

export interface ParameterInfo {
  name: string
  value: number
  scenario: string
  scenario_instance: string
  min_range?: number
  max_range?: number
  description?: string
  unit?: string
}

export interface ScenarioInfo {
  name: string
  type: string
  parameters: Record<string, any>
  fuzzable_parameters: ParameterInfo[]
  description?: string
}

export interface RouteInfo {
  route_id: string
  route_file: string
  town?: string
  scenarios: ScenarioInfo[]
  total_fuzzable_parameters: number
  waypoints?: Array<{ x: number; y: number; z: number }>
  distance?: number
  weather?: Record<string, any>
  time_of_day?: string
}

export interface RouteListItem {
  route_id: string
  route_file: string
  town?: string
  scenario_count: number
  fuzzable_parameter_count: number
  primary_scenario_type?: string
}

export interface RouteFileInfo {
  filename: string
  routes: RouteListItem[]
  total_routes: number
  file_path: string
  last_modified?: string
}

export interface ParameterValidation {
  parameter_name: string
  is_valid: boolean
  error_message?: string
  suggested_value?: number
}

export interface ScenarioValidation {
  is_valid: boolean
  parameter_validations: ParameterValidation[]
  missing_parameters: string[]
  warnings: string[]
  errors: string[]
}

export interface ScenarioSearch {
  scenario_type?: string
  town?: string
  min_parameters?: number
  parameter_names?: string[]
  route_file?: string
}

export interface ParameterStatistics {
  parameter_name: string
  usage_count: number
  min_value: number
  max_value: number
  mean_value: number
  scenarios: string[]
}

export interface ScenarioStatistics {
  total_routes: number
  total_scenarios: number
  scenario_types: Record<string, number>
  parameter_statistics: ParameterStatistics[]
  towns: string[]
  route_files: string[]
} 