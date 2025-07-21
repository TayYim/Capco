import type { ExperimentData } from '../types'

export interface PrimaryProgress {
  current: number
  total: number
  percentage: number
  label: string
  subtitle: string
}

export interface SecondaryProgress {
  optimization_progress: string
  current_iteration_progress: string
}

/**
 * Get the primary progress display based on search method
 */
export function getPrimaryProgress(experiment: ExperimentData): PrimaryProgress {
  const { progress, config } = experiment
  
  if (!progress) {
    return {
      current: 0,
      total: 100,
      percentage: 0,
      label: 'Progress',
      subtitle: 'No progress data available'
    }
  }
  
  if (config.search_method === 'random') {
    // For random: show iterations (1:1 with scenarios)
    const percentage = progress.total_iterations > 0 
      ? (progress.current_iteration / progress.total_iterations) * 100 
      : 0
    
    return {
      current: progress.current_iteration,
      total: progress.total_iterations,
      percentage,
      label: 'Iterations',
      subtitle: `${progress.scenarios_executed} scenarios executed`
    }
  } else {
    // For PSO/GA: show scenarios (actual work done)
    const percentage = progress.total_scenarios > 0 
      ? (progress.scenarios_executed / progress.total_scenarios) * 100 
      : 0
    
    return {
      current: progress.scenarios_executed,
      total: progress.total_scenarios,
      percentage,
      label: 'Scenarios',
      subtitle: `Iteration ${progress.current_iteration}/${progress.total_iterations}`
    }
  }
}

/**
 * Get secondary progress information for PSO/GA methods
 */
export function getSecondaryProgress(experiment: ExperimentData): SecondaryProgress | null {
  const { progress, config } = experiment
  
  if (!progress || config.search_method === 'random') {
    return null
  }
  
  return {
    optimization_progress: `${progress.current_iteration} / ${progress.total_iterations} iterations`,
    current_iteration_progress: `${progress.scenarios_this_iteration} / ${progress.population_size || 0} scenarios`
  }
}

/**
 * Format progress percentage for display
 */
export function formatProgressPercentage(percentage: number): string {
  return `${Math.round(percentage)}%`
}

/**
 * Check if progress should show fast polling (running experiments)
 */
export function shouldUseFastPolling(experiment: ExperimentData): boolean {
  return experiment.status === 'running'
}

/**
 * Get polling interval based on experiment status
 */
export function getPollingInterval(experiment: ExperimentData): number {
  if (experiment.status === 'running') {
    return 2000 // 2 seconds for running experiments
  }
  return 10000 // 10 seconds for other statuses
} 