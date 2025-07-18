import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  CogIcon,
  WrenchIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  InformationCircleIcon,
  AdjustmentsHorizontalIcon
} from '@heroicons/react/24/outline'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { apiClient } from '../services/api'
import type { SystemConfiguration, ParameterRange } from '../types'
import clsx from 'clsx'

// Form validation schemas
const systemConfigSchema = z.object({
  carla_path: z.string().min(1, 'CARLA path is required'),
  default_timeout: z.number().min(30).max(3600),
  max_concurrent_experiments: z.number().min(1).max(10),
  default_iterations: z.number().min(10).max(10000),
  default_search_method: z.enum(['random', 'pso', 'ga']),
  default_reward_function: z.enum(['collision', 'distance', 'safety_margin', 'ttc', 'ttc_div_dist', 'weighted_multi']),
  log_level: z.enum(['DEBUG', 'INFO', 'WARNING', 'ERROR']),
  cleanup_after_days: z.number().min(1).max(365),
})

type SystemConfigFormData = z.infer<typeof systemConfigSchema>

export function ConfigurationPage() {
  const [activeTab, setActiveTab] = useState<'system' | 'parameters'>('system')
  const queryClient = useQueryClient()

  // Fetch system configuration
  const { data: systemConfig, isLoading: configLoading } = useQuery({
    queryKey: ['system-config'],
    queryFn: () => apiClient.getSystemConfiguration(),
  })

  // Fetch configuration status
  const { data: configStatus } = useQuery({
    queryKey: ['config-status'],
    queryFn: () => apiClient.getConfigurationStatus(),
    refetchInterval: 30000,
  })

  // Fetch parameter ranges
  const { data: parameterRanges, isLoading: paramsLoading } = useQuery({
    queryKey: ['parameter-ranges'],
    queryFn: () => apiClient.getParameterRanges(),
  })

  // System config form
  const {
    register: registerSystem,
    handleSubmit: handleSystemSubmit,
    formState: { errors: systemErrors, isSubmitting: systemSubmitting },
    reset: resetSystem
  } = useForm<SystemConfigFormData>({
    resolver: zodResolver(systemConfigSchema),
  })

  // Update system configuration when data loads
  React.useEffect(() => {
    if (systemConfig) {
      resetSystem({
        carla_path: systemConfig.carla_path,
        default_timeout: systemConfig.default_timeout,
        max_concurrent_experiments: systemConfig.max_concurrent_experiments,
        default_iterations: systemConfig.default_iterations,
        default_search_method: systemConfig.default_search_method as any,
        default_reward_function: systemConfig.default_reward_function as any,
        log_level: systemConfig.log_level as any,
        cleanup_after_days: systemConfig.cleanup_after_days,
      })
    }
  }, [systemConfig, resetSystem])

  // Update system config mutation
  const updateSystemMutation = useMutation({
    mutationFn: (data: Partial<SystemConfiguration>) =>
      apiClient.updateSystemConfiguration(data),
    onSuccess: () => {
      toast.success('System configuration updated successfully!')
      queryClient.invalidateQueries({ queryKey: ['system-config'] })
      queryClient.invalidateQueries({ queryKey: ['config-status'] })
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update configuration')
    }
  })

  const onSystemSubmit = (data: SystemConfigFormData) => {
    updateSystemMutation.mutate(data)
  }

  const tabs = [
    { id: 'system', name: 'System Settings', icon: CogIcon },
    { id: 'parameters', name: 'Parameter Ranges', icon: AdjustmentsHorizontalIcon },
  ]

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-6xl mx-auto space-y-6"
    >
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          Configuration
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Manage system settings and parameter ranges for the fuzzing framework
        </p>
      </div>

      {/* Configuration Status */}
      {configStatus && (
        <div className={clsx(
          'rounded-lg p-4 border',
          configStatus.is_valid
            ? 'bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800'
            : 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800'
        )}>
          <div className="flex">
            <div className="flex-shrink-0">
              {configStatus.is_valid ? (
                <CheckCircleIcon className="h-5 w-5 text-green-400" />
              ) : (
                <ExclamationTriangleIcon className="h-5 w-5 text-red-400" />
              )}
            </div>
            <div className="ml-3">
              <h3 className={clsx(
                'text-sm font-medium',
                configStatus.is_valid 
                  ? 'text-green-800 dark:text-green-400'
                  : 'text-red-800 dark:text-red-400'
              )}>
                {configStatus.is_valid 
                  ? 'Configuration is valid and ready'
                  : 'Configuration has issues'
                }
              </h3>
              {(configStatus.errors.length > 0 || configStatus.warnings.length > 0) && (
                <div className="mt-2 text-sm">
                  {configStatus.errors.map((error, index) => (
                    <div key={index} className="text-red-700 dark:text-red-400">
                      • {error}
                    </div>
                  ))}
                  {configStatus.warnings.map((warning, index) => (
                    <div key={index} className="text-yellow-700 dark:text-yellow-400">
                      • {warning}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={clsx(
                'group inline-flex items-center py-2 px-1 border-b-2 font-medium text-sm',
                activeTab === tab.id
                  ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
              )}
            >
              <tab.icon
                className={clsx(
                  'mr-2 h-5 w-5',
                  activeTab === tab.id
                    ? 'text-indigo-500 dark:text-indigo-400'
                    : 'text-gray-400 group-hover:text-gray-500'
                )}
              />
              {tab.name}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'system' && (
        <SystemConfigurationTab
          systemConfig={systemConfig}
          configLoading={configLoading}
          register={registerSystem}
          errors={systemErrors}
          onSubmit={handleSystemSubmit(onSystemSubmit)}
          isSubmitting={systemSubmitting || updateSystemMutation.isPending}
        />
      )}

      {activeTab === 'parameters' && (
        <ParameterRangesTab
          parameterRanges={parameterRanges}
          paramsLoading={paramsLoading}
        />
      )}
    </motion.div>
  )
}

function SystemConfigurationTab({
  systemConfig,
  configLoading,
  register,
  errors,
  onSubmit,
  isSubmitting
}: any) {
  if (configLoading) {
    return (
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
        <div className="animate-pulse space-y-4">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="space-y-2">
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/4"></div>
              <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded"></div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white dark:bg-gray-800 shadow rounded-lg">
      <div className="px-4 py-5 sm:p-6">
        <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white mb-4">
          System Configuration
        </h3>

        <form onSubmit={onSubmit} className="space-y-6">
          {/* CARLA Configuration */}
          <div className="grid grid-cols-1 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                CARLA Installation Path
              </label>
              <input
                type="text"
                {...register('carla_path')}
                className="mt-1 block w-full border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                placeholder="/path/to/CARLA_0.9.13"
              />
              {errors.carla_path && (
                <p className="mt-1 text-sm text-red-600">{errors.carla_path.message}</p>
              )}
            </div>
          </div>

          {/* Experiment Defaults */}
          <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
            <h4 className="text-base font-medium text-gray-900 dark:text-white mb-4">
              Experiment Defaults
            </h4>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Default Timeout (seconds)
                </label>
                <input
                  type="number"
                  {...register('default_timeout', { valueAsNumber: true })}
                  className="mt-1 block w-full border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                />
                {errors.default_timeout && (
                  <p className="mt-1 text-sm text-red-600">{errors.default_timeout.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Default Iterations
                </label>
                <input
                  type="number"
                  {...register('default_iterations', { valueAsNumber: true })}
                  className="mt-1 block w-full border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                />
                {errors.default_iterations && (
                  <p className="mt-1 text-sm text-red-600">{errors.default_iterations.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Max Concurrent Experiments
                </label>
                <input
                  type="number"
                  {...register('max_concurrent_experiments', { valueAsNumber: true })}
                  className="mt-1 block w-full border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                />
                {errors.max_concurrent_experiments && (
                  <p className="mt-1 text-sm text-red-600">{errors.max_concurrent_experiments.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Default Search Method
                </label>
                <select
                  {...register('default_search_method')}
                  className="mt-1 block w-full border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                >
                  <option value="random">Random</option>
                  <option value="pso">Particle Swarm Optimization</option>
                  <option value="ga">Genetic Algorithm</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Default Reward Function
                </label>
                <select
                  {...register('default_reward_function')}
                  className="mt-1 block w-full border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                >
                  <option value="collision">Collision</option>
                  <option value="distance">Distance</option>
                  <option value="safety_margin">Safety Margin</option>
                  <option value="ttc">Time to Collision</option>
                  <option value="ttc_div_dist">TTC / Distance</option>
                  <option value="weighted_multi">Weighted Multi</option>
                </select>
              </div>
            </div>
          </div>

          {/* System Settings */}
          <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
            <h4 className="text-base font-medium text-gray-900 dark:text-white mb-4">
              System Settings
            </h4>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Log Level
                </label>
                <select
                  {...register('log_level')}
                  className="mt-1 block w-full border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                >
                  <option value="DEBUG">Debug</option>
                  <option value="INFO">Info</option>
                  <option value="WARNING">Warning</option>
                  <option value="ERROR">Error</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Cleanup After (days)
                </label>
                <input
                  type="number"
                  {...register('cleanup_after_days', { valueAsNumber: true })}
                  className="mt-1 block w-full border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                />
                {errors.cleanup_after_days && (
                  <p className="mt-1 text-sm text-red-600">{errors.cleanup_after_days.message}</p>
                )}
              </div>
            </div>
          </div>

          {/* Save Button */}
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
            >
              {isSubmitting ? 'Saving...' : 'Save Configuration'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function ParameterRangesTab({
  parameterRanges,
  paramsLoading
}: {
  parameterRanges?: ParameterRange[]
  paramsLoading: boolean
}) {
  const [selectedScenarioType, setSelectedScenarioType] = useState<string>('')

  // Get unique scenario types
  const scenarioTypes = React.useMemo(() => {
    if (!parameterRanges) return []
    const types = new Set(parameterRanges.map(p => p.scenario_type).filter(Boolean))
    return Array.from(types)
  }, [parameterRanges])

  // Filter parameters by scenario type
  const filteredParameters = React.useMemo(() => {
    if (!parameterRanges) return []
    if (!selectedScenarioType) return parameterRanges
    return parameterRanges.filter(p => p.scenario_type === selectedScenarioType)
  }, [parameterRanges, selectedScenarioType])

  if (paramsLoading) {
    return (
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
        <div className="animate-pulse space-y-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="flex items-center space-x-4">
              <div className="h-12 w-12 bg-gray-200 dark:bg-gray-700 rounded"></div>
              <div className="flex-1 space-y-2">
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
                <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Filters */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white">
            Parameter Ranges
          </h3>
          <div className="flex items-center space-x-4">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Scenario Type:
            </label>
            <select
              value={selectedScenarioType}
              onChange={(e) => setSelectedScenarioType(e.target.value)}
              className="border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
            >
              <option value="">All types</option>
              {scenarioTypes.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="text-sm text-gray-500 dark:text-gray-400">
          Showing {filteredParameters.length} of {parameterRanges?.length || 0} parameters
        </div>
      </div>

      {/* Parameters Grid */}
      {filteredParameters && filteredParameters.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredParameters.map((param, index) => (
            <ParameterCard key={index} parameter={param} />
          ))}
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-12 text-center">
          <WrenchIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-white">
            No parameters found
          </h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {selectedScenarioType
              ? 'No parameters found for the selected scenario type.'
              : 'No parameter ranges have been loaded yet.'
            }
          </p>
        </div>
      )}
    </div>
  )
}

function ParameterCard({ parameter }: { parameter: ParameterRange }) {
  return (
    <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h4 className="text-lg font-medium text-gray-900 dark:text-white">
            {parameter.parameter_name}
          </h4>
          {parameter.scenario_type && (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-400 mt-1">
              {parameter.scenario_type}
            </span>
          )}
        </div>
        <AdjustmentsHorizontalIcon className="h-5 w-5 text-gray-400" />
      </div>

      <div className="mt-4 space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-gray-500 dark:text-gray-400">Range:</span>
          <span className="text-gray-900 dark:text-white">
            {parameter.min_value} - {parameter.max_value}
            {parameter.unit && ` ${parameter.unit}`}
          </span>
        </div>

        {parameter.default_value !== undefined && (
          <div className="flex justify-between text-sm">
            <span className="text-gray-500 dark:text-gray-400">Default:</span>
            <span className="text-gray-900 dark:text-white">
              {parameter.default_value}
              {parameter.unit && ` ${parameter.unit}`}
            </span>
          </div>
        )}
      </div>

      {parameter.description && (
        <div className="mt-4 text-sm text-gray-500 dark:text-gray-400">
          {parameter.description}
        </div>
      )}
    </div>
  )
} 