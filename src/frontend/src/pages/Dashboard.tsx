import React from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { 
  PlayIcon, 
  ClockIcon, 
  CogIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  BeakerIcon 
} from '@heroicons/react/24/outline'
import { motion } from 'framer-motion'
import { apiClient } from '../services/api'
import clsx from 'clsx'

export function Dashboard() {
  // Fetch system info and recent experiments
  const { data: systemInfo, isLoading: systemLoading } = useQuery({
    queryKey: ['system-info'],
    queryFn: () => apiClient.getSystemInfo(),
    refetchInterval: 60000,
  })

  const { data: experiments, isLoading: experimentsLoading } = useQuery({
    queryKey: ['experiments', { limit: 5 }],
    queryFn: () => apiClient.listExperiments({ limit: 5 }),
    refetchInterval: 10000, // Poll every 10 seconds for recent experiments
  })

  const { data: scenarios } = useQuery({
    queryKey: ['scenario-stats'],
    queryFn: () => apiClient.getScenarioStatistics(),
  })

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  }

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1
    }
  }

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-6"
    >
      {/* Header */}
      <motion.div variants={itemVariants}>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          Dashboard
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Welcome to the CARLA Scenario Fuzzing Framework
        </p>
      </motion.div>

      {/* Quick Actions */}
      <motion.div variants={itemVariants}>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link
            to="/experiment"
            className="group relative p-6 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg shadow-lg hover:shadow-xl transition-all duration-300 text-white"
          >
            <div className="flex items-center space-x-3">
              <PlayIcon className="h-8 w-8" />
              <div>
                <h3 className="text-lg font-semibold">New Experiment</h3>
                <p className="text-indigo-100">Start fuzzing scenarios</p>
              </div>
            </div>
            <div className="absolute inset-0 bg-white opacity-0 group-hover:opacity-10 rounded-lg transition-opacity" />
          </Link>

          <Link
            to="/history"
            className="group relative p-6 bg-gradient-to-br from-green-500 to-teal-600 rounded-lg shadow-lg hover:shadow-xl transition-all duration-300 text-white"
          >
            <div className="flex items-center space-x-3">
              <ClockIcon className="h-8 w-8" />
              <div>
                <h3 className="text-lg font-semibold">Experiment History</h3>
                <p className="text-green-100">View past results</p>
              </div>
            </div>
            <div className="absolute inset-0 bg-white opacity-0 group-hover:opacity-10 rounded-lg transition-opacity" />
          </Link>

          <Link
            to="/configuration"
            className="group relative p-6 bg-gradient-to-br from-orange-500 to-red-600 rounded-lg shadow-lg hover:shadow-xl transition-all duration-300 text-white"
          >
            <div className="flex items-center space-x-3">
              <CogIcon className="h-8 w-8" />
              <div>
                <h3 className="text-lg font-semibold">Configuration</h3>
                <p className="text-orange-100">System settings</p>
              </div>
            </div>
            <div className="absolute inset-0 bg-white opacity-0 group-hover:opacity-10 rounded-lg transition-opacity" />
          </Link>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* System Status */}
        <motion.div variants={itemVariants}>
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                System Status
              </h2>
              {systemInfo?.system_status.is_valid ? (
                <CheckCircleIcon className="h-6 w-6 text-green-500" />
              ) : (
                <ExclamationTriangleIcon className="h-6 w-6 text-red-500" />
              )}
            </div>

            {systemLoading ? (
              <div className="animate-pulse space-y-3">
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-2/3"></div>
              </div>
            ) : systemInfo ? (
              <div className="space-y-3">
                <StatusItem
                  label="CARLA Available"
                  status={systemInfo.system_status.carla_available}
                />
                <StatusItem
                  label="Parameter Ranges Loaded"
                  status={systemInfo.system_status.parameter_ranges_loaded}
                />
                <StatusItem
                  label="Output Directory Writable"
                  status={systemInfo.system_status.output_directory_writable}
                />
                
                <div className="pt-3 border-t border-gray-200 dark:border-gray-700">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500 dark:text-gray-400">Version</span>
                    <span className="text-gray-900 dark:text-white">{systemInfo.version}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500 dark:text-gray-400">Active Experiments</span>
                    <span className="text-gray-900 dark:text-white">{systemInfo.active_experiments}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500 dark:text-gray-400">Uptime</span>
                    <span className="text-gray-900 dark:text-white">
                      {Math.round(systemInfo.uptime / 3600)}h
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-red-500">Failed to load system status</div>
            )}
          </div>
        </motion.div>

        {/* Recent Experiments */}
        <motion.div variants={itemVariants}>
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Recent Experiments
              </h2>
              <Link
                to="/history"
                className="text-indigo-600 hover:text-indigo-500 text-sm font-medium"
              >
                View all
              </Link>
            </div>

            {experimentsLoading ? (
              <div className="animate-pulse space-y-3">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="flex items-center space-x-3">
                    <div className="h-10 w-10 bg-gray-200 dark:bg-gray-700 rounded"></div>
                    <div className="flex-1 space-y-2">
                      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
                      <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
                    </div>
                  </div>
                ))}
              </div>
            ) : experiments && experiments.length > 0 ? (
              <div className="space-y-3">
                {experiments.map((experiment) => (
                  <div
                    key={experiment.id}
                    className="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                  >
                    <div className={clsx(
                      'w-10 h-10 rounded-full flex items-center justify-center',
                      experiment.status === 'completed' && 'bg-green-100 text-green-600 dark:bg-green-900 dark:text-green-400',
                      experiment.status === 'running' && 'bg-blue-100 text-blue-600 dark:bg-blue-900 dark:text-blue-400',
                      experiment.status === 'failed' && 'bg-red-100 text-red-600 dark:bg-red-900 dark:text-red-400',
                      experiment.status === 'created' && 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                    )}>
                      <BeakerIcon className="h-5 w-5" />
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <Link
                        to={`/experiment/${experiment.id}`}
                        className="text-sm font-medium text-gray-900 dark:text-white hover:text-indigo-600 dark:hover:text-indigo-400 truncate block"
                      >
                        {experiment.route_id}
                      </Link>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        {experiment.search_method} • {experiment.status}
                      </div>
                    </div>
                    
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      {new Date(experiment.created_at).toLocaleDateString()}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                <BeakerIcon className="h-12 w-12 mx-auto mb-3 opacity-40" />
                <p>No experiments yet</p>
                <Link
                  to="/experiment"
                  className="text-indigo-600 hover:text-indigo-500 text-sm font-medium mt-2 inline-block"
                >
                  Create your first experiment
                </Link>
              </div>
            )}
          </div>
        </motion.div>
      </div>

      {/* Statistics */}
      {scenarios && (
        <motion.div variants={itemVariants}>
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Available Scenarios
            </h2>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">
                  {scenarios.total_routes}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">Total Routes</div>
              </div>
              
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                  {scenarios.total_scenarios}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">Total Scenarios</div>
              </div>
              
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                  {scenarios.parameter_statistics?.length || 0}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">Fuzzable Parameters</div>
              </div>
              
              <div className="text-center">
                <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">
                  {scenarios.towns?.length || 0}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">Available Towns</div>
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}

function StatusItem({ label, status }: { label: string; status: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-gray-500 dark:text-gray-400">{label}</span>
      <div className="flex items-center space-x-2">
        {status ? (
          <>
            <CheckCircleIcon className="h-4 w-4 text-green-500" />
            <span className="text-sm text-green-600 dark:text-green-400">OK</span>
          </>
        ) : (
          <>
            <ExclamationTriangleIcon className="h-4 w-4 text-red-500" />
            <span className="text-sm text-red-600 dark:text-red-400">Error</span>
          </>
        )}
      </div>
    </div>
  )
} 