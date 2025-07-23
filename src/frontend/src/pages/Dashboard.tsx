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
  BeakerIcon,
  EyeIcon
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
    queryKey: ['experiments', { limit: 10 }],
    queryFn: () => apiClient.listExperiments({ limit: 10 }),
    refetchInterval: 10000, // Poll every 10 seconds for recent experiments
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
      className="space-y-8"
    >
      {/* Header */}
      <motion.div variants={itemVariants} className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white">
            Dashboard
          </h1>
          <p className="mt-2 text-lg text-gray-600 dark:text-gray-400">
            CARLA Scenario Fuzzing Framework - Monitor and manage your experiments
          </p>
        </div>
        <div className="flex space-x-3">
          <Link
            to="/experiment"
            className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-lg shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-all duration-200"
          >
            <PlayIcon className="h-5 w-5 mr-2" />
            New Experiment
          </Link>
        </div>
      </motion.div>

      {/* Quick Actions */}
      <motion.div variants={itemVariants}>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Link
            to="/experiment"
            className="group relative p-8 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl shadow-xl hover:shadow-2xl transition-all duration-300 text-white overflow-hidden"
          >
            <div className="relative z-10">
              <div className="flex items-center space-x-4 mb-4">
                <PlayIcon className="h-12 w-12" />
                <div>
                  <h3 className="text-2xl font-bold">New Experiment</h3>
                  <p className="text-indigo-100">Configure and start fuzzing</p>
                </div>
              </div>
              <p className="text-indigo-100">
                Create a new scenario fuzzing experiment with customizable parameters and search algorithms.
              </p>
            </div>
            <div className="absolute inset-0 bg-white opacity-0 group-hover:opacity-10 transition-opacity" />
            <div className="absolute -top-10 -right-10 w-32 h-32 bg-white opacity-10 rounded-full" />
          </Link>

          <Link
            to="/history"
            className="group relative p-8 bg-gradient-to-br from-green-500 to-emerald-600 rounded-xl shadow-xl hover:shadow-2xl transition-all duration-300 text-white overflow-hidden"
          >
            <div className="relative z-10">
              <div className="flex items-center space-x-4 mb-4">
                <ClockIcon className="h-12 w-12" />
                <div>
                  <h3 className="text-2xl font-bold">Experiment History</h3>
                  <p className="text-green-100">Browse past results</p>
                </div>
              </div>
              <p className="text-green-100">
                View, analyze, and manage your experiment history with detailed results and insights.
              </p>
            </div>
            <div className="absolute inset-0 bg-white opacity-0 group-hover:opacity-10 transition-opacity" />
            <div className="absolute -top-10 -right-10 w-32 h-32 bg-white opacity-10 rounded-full" />
          </Link>

          <Link
            to="/configuration"
            className="group relative p-8 bg-gradient-to-br from-orange-500 to-red-600 rounded-xl shadow-xl hover:shadow-2xl transition-all duration-300 text-white overflow-hidden"
          >
            <div className="relative z-10">
              <div className="flex items-center space-x-4 mb-4">
                <CogIcon className="h-12 w-12" />
                <div>
                  <h3 className="text-2xl font-bold">Configuration</h3>
                  <p className="text-orange-100">System settings</p>
                </div>
              </div>
              <p className="text-orange-100">
                Configure system parameters, CARLA settings, and optimization algorithm parameters.
              </p>
            </div>
            <div className="absolute inset-0 bg-white opacity-0 group-hover:opacity-10 transition-opacity" />
            <div className="absolute -top-10 -right-10 w-32 h-32 bg-white opacity-10 rounded-full" />
          </Link>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        {/* System Status Details */}
        <motion.div variants={itemVariants} className="xl:col-span-1">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                System Health
              </h2>
              {systemInfo?.system_status.is_valid ? (
                <CheckCircleIcon className="h-6 w-6 text-green-500" />
              ) : (
                <ExclamationTriangleIcon className="h-6 w-6 text-red-500" />
              )}
            </div>

            {systemLoading ? (
              <div className="animate-pulse space-y-4">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
                ))}
              </div>
            ) : systemInfo ? (
              <div className="space-y-4">
                <StatusItem
                  label="CARLA Available"
                  status={systemInfo.system_status.carla_available}
                />
                <StatusItem
                  label="Apollo Available"
                  status={systemInfo.system_status.apollo_available}
                />
                <StatusItem
                  label="Parameter Ranges Loaded"
                  status={systemInfo.system_status.parameter_ranges_loaded}
                />
                <StatusItem
                  label="Output Directory Writable"
                  status={systemInfo.system_status.output_directory_writable}
                />
                
                <div className="pt-4 border-t border-gray-200 dark:border-gray-700 space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500 dark:text-gray-400">Version</span>
                    <span className="text-gray-900 dark:text-white font-medium">{systemInfo.version}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500 dark:text-gray-400">Uptime</span>
                    <span className="text-gray-900 dark:text-white font-medium">
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
        <motion.div variants={itemVariants} className="xl:col-span-2">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                Recent Experiments
              </h2>
              <Link
                to="/history"
                className="text-indigo-600 hover:text-indigo-500 text-sm font-medium"
              >
                View all →
              </Link>
            </div>

            {experimentsLoading ? (
              <div className="animate-pulse space-y-4">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="flex items-center space-x-4">
                    <div className="h-12 w-12 bg-gray-200 dark:bg-gray-700 rounded-full"></div>
                    <div className="flex-1 space-y-2">
                      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
                      <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
                    </div>
                  </div>
                ))}
              </div>
            ) : experiments && experiments.length > 0 ? (
              <div className="space-y-4">
                {experiments.slice(0, 8).map((experiment) => (
                  <div
                    key={experiment.id}
                    className="flex items-center justify-between p-4 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors group"
                  >
                    <div className="flex items-center space-x-4">
                      <div className={clsx(
                        'w-12 h-12 rounded-full flex items-center justify-center',
                        experiment.status === 'completed' && 'bg-green-100 text-green-600 dark:bg-green-900 dark:text-green-400',
                        experiment.status === 'running' && 'bg-blue-100 text-blue-600 dark:bg-blue-900 dark:text-blue-400',
                        experiment.status === 'failed' && 'bg-red-100 text-red-600 dark:bg-red-900 dark:text-red-400',
                        experiment.status === 'created' && 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                      )}>
                        <BeakerIcon className="h-6 w-6" />
                      </div>
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2">
                          <h3 className="text-sm font-medium text-gray-900 dark:text-white truncate">
                            {experiment.name}
                          </h3>
                          <span className={clsx(
                            'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium',
                            experiment.status === 'completed' && 'text-green-800 bg-green-100 dark:bg-green-900 dark:text-green-200',
                            experiment.status === 'running' && 'text-blue-800 bg-blue-100 dark:bg-blue-900 dark:text-blue-200',
                            experiment.status === 'failed' && 'text-red-800 bg-red-100 dark:bg-red-900 dark:text-red-200',
                            experiment.status === 'created' && 'text-gray-800 bg-gray-100 dark:bg-gray-700 dark:text-gray-200'
                          )}>
                            {experiment.status}
                          </span>
                        </div>
                        <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
                          {experiment.route_name || experiment.route_id} • {experiment.search_method} • {experiment.agent === 'apollo' ? '🚀 Apollo' : '🤖 BA'}
                        </p>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-3">
                      <div className="text-right">
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {new Date(experiment.created_at).toLocaleDateString()}
                        </p>
                        {experiment.collision_found !== undefined && (
                          <p className={clsx(
                            'text-xs font-medium',
                            experiment.collision_found 
                              ? 'text-red-600 dark:text-red-400'
                              : 'text-green-600 dark:text-green-400'
                          )}>
                            {experiment.collision_found ? 'Collision' : 'Safe'}
                          </p>
                        )}
                      </div>
                      <div className="flex space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <Link
                          to={`/experiment/${experiment.id}`}
                          className="p-2 text-gray-400 hover:text-indigo-600 transition-colors"
                          title="View details"
                        >
                          <EyeIcon className="h-4 w-4" />
                        </Link>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                <BeakerIcon className="h-16 w-16 mx-auto mb-4 opacity-40" />
                <h3 className="text-lg font-medium mb-2">No experiments yet</h3>
                <p className="mb-4">Get started by creating your first experiment</p>
                <Link
                  to="/experiment"
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
                >
                  <PlayIcon className="h-4 w-4 mr-2" />
                  Create Experiment
                </Link>
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </motion.div>
  )
}

function StatusItem({ label, status }: { label: string; status: boolean }) {
  return (
    <div className="flex items-center justify-between py-2">
      <span className="text-sm text-gray-600 dark:text-gray-400">{label}</span>
      <div className="flex items-center space-x-2">
        {status ? (
          <>
            <CheckCircleIcon className="h-4 w-4 text-green-500" />
            <span className="text-sm font-medium text-green-600 dark:text-green-400">OK</span>
          </>
        ) : (
          <>
            <ExclamationTriangleIcon className="h-4 w-4 text-red-500" />
            <span className="text-sm font-medium text-red-600 dark:text-red-400">Error</span>
          </>
        )}
      </div>
    </div>
  )
} 