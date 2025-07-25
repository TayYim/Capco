import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  EyeIcon,
  TrashIcon,
  ArrowDownTrayIcon,
  FunnelIcon,
  MagnifyingGlassIcon,
  PlayIcon,
  StopIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  DocumentDuplicateIcon,
  ChartBarIcon,
  BeakerIcon,
  FireIcon,
  TrophyIcon
} from '@heroicons/react/24/outline'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { apiClient } from '../services/api'
import type { ExperimentListItem } from '../types'
import clsx from 'clsx'

export function HistoryPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [methodFilter, setMethodFilter] = useState<string>('')
  const [agentFilter, setAgentFilter] = useState<string>('')
  const [limit, setLimit] = useState(20)
  const [offset, setOffset] = useState(0)
  const queryClient = useQueryClient()

  const { data: experiments, isLoading } = useQuery({
    queryKey: ['experiments', { limit, offset, statusFilter, methodFilter, agentFilter, search: searchQuery }],
    queryFn: () => apiClient.listExperiments({
      limit,
      offset,
      status_filter: statusFilter || undefined,
      search_method: methodFilter || undefined,
      // Note: Backend doesn't support agent filtering yet, will filter client-side
    }),
    refetchInterval: 5000, // Poll every 5 seconds for updated statuses
  })

  // Duplicate experiment mutation
  const duplicateMutation = useMutation({
    mutationFn: (experimentId: string) => apiClient.duplicateExperiment(experimentId),
    onSuccess: (data) => {
      toast.success('Experiment duplicated successfully!')
      queryClient.invalidateQueries({ queryKey: ['experiments'] })
      // Navigate to the new experiment in edit mode
      window.location.href = `/experiment/${data.id}?edit=true`
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to duplicate experiment')
    }
  })

  // Delete experiment mutation
  const deleteMutation = useMutation({
    mutationFn: (experimentId: string) => apiClient.deleteExperiment(experimentId),
    onSuccess: (data, experimentId) => {
      toast.success('Experiment deleted successfully!')
      queryClient.invalidateQueries({ queryKey: ['experiments'] })
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to delete experiment')
    }
  })

  // Download experiment archive mutation
  const downloadMutation = useMutation({
    mutationFn: (experimentId: string) => apiClient.downloadExperimentArchive(experimentId, 'zip'),
    onSuccess: (blob, experimentId) => {
      // Create a download link and trigger the download
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      
      // Generate filename with timestamp
      const timestamp = new Date().toISOString().slice(0, 19).replace(/[T:]/g, '_')
      link.download = `experiment_${experimentId}_${timestamp}.zip`
      
      document.body.appendChild(link)
      link.click()
      
      // Cleanup
      window.URL.revokeObjectURL(url)
      document.body.removeChild(link)
      
      toast.success('Download started!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to download experiment files')
    }
  })

  const filteredExperiments = experiments?.filter(experiment => {
    // Search query filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      const matchesSearch = experiment.name.toLowerCase().includes(query) ||
                           (experiment.route_name || experiment.route_id).toLowerCase().includes(query) ||
                           experiment.route_file.toLowerCase().includes(query) ||
                           experiment.search_method.toLowerCase().includes(query)
      if (!matchesSearch) return false
    }
    
    // Agent filter
    if (agentFilter && experiment.agent !== agentFilter) {
      return false
    }
    
    return true
  })

  // Calculate summary statistics
  const summaryStats = React.useMemo(() => {
    if (!filteredExperiments) return null
    
    const total = filteredExperiments.length
    const completed = filteredExperiments.filter(e => e.status === 'completed').length
    const running = filteredExperiments.filter(e => e.status === 'running').length
    const failed = filteredExperiments.filter(e => e.status === 'failed').length
    const withCollisions = filteredExperiments.filter(e => e.collision_found === true).length
    
    return { total, completed, running, failed, withCollisions }
  }, [filteredExperiments])

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />
      case 'running':
        return <PlayIcon className="h-5 w-5 text-blue-500 animate-pulse" />
      case 'failed':
        return <XCircleIcon className="h-5 w-5 text-red-500" />
      case 'stopped':
        return <StopIcon className="h-5 w-5 text-yellow-500" />
      default:
        return <ClockIcon className="h-5 w-5 text-gray-500" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-600 bg-green-100 dark:bg-green-900 dark:text-green-400'
      case 'running': return 'text-blue-600 bg-blue-100 dark:bg-blue-900 dark:text-blue-400'
      case 'failed': return 'text-red-600 bg-red-100 dark:bg-red-900 dark:text-red-400'
      case 'stopped': return 'text-yellow-600 bg-yellow-100 dark:bg-yellow-900 dark:text-yellow-400'
      default: return 'text-gray-600 bg-gray-100 dark:bg-gray-700 dark:text-gray-400'
    }
  }

  const formatDuration = (startTime: string, endTime?: string) => {
    if (!endTime) return 'In progress...'
    
    const start = new Date(startTime)
    const end = new Date(endTime)
    const duration = end.getTime() - start.getTime()
    
    const hours = Math.floor(duration / (1000 * 60 * 60))
    const minutes = Math.floor((duration % (1000 * 60 * 60)) / (1000 * 60))
    const seconds = Math.floor((duration % (1000 * 60)) / 1000)
    
    if (hours > 0) {
      return `${hours}h ${minutes}m ${seconds}s`
    } else if (minutes > 0) {
      return `${minutes}m ${seconds}s`
    } else {
      return `${seconds}s`
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-8"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white">
            Experiment History
          </h1>
          <p className="mt-2 text-lg text-gray-600 dark:text-gray-400">
            View, manage, and analyze your fuzzing experiments
          </p>
        </div>

        <Link
          to="/experiment"
          className="inline-flex items-center px-6 py-3 border border-transparent shadow-sm text-base font-medium rounded-lg text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-all duration-200"
        >
          <PlayIcon className="h-5 w-5 mr-2" />
          New Experiment
        </Link>
      </div>

      {/* Summary Statistics */}
      {summaryStats && (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 border-l-4 border-blue-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{summaryStats.total}</p>
              </div>
              <div className="p-3 bg-blue-100 text-blue-600 dark:bg-blue-900 dark:text-blue-400 rounded-full">
                <BeakerIcon className="h-6 w-6" />
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 border-l-4 border-green-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Completed</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{summaryStats.completed}</p>
              </div>
              <div className="p-3 bg-green-100 text-green-600 dark:bg-green-900 dark:text-green-400 rounded-full">
                <TrophyIcon className="h-6 w-6" />
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 border-l-4 border-blue-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Running</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{summaryStats.running}</p>
              </div>
              <div className="p-3 bg-blue-100 text-blue-600 dark:bg-blue-900 dark:text-blue-400 rounded-full">
                <ChartBarIcon className="h-6 w-6" />
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 border-l-4 border-red-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Failed</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{summaryStats.failed}</p>
              </div>
              <div className="p-3 bg-red-100 text-red-600 dark:bg-red-900 dark:text-red-400 rounded-full">
                <XCircleIcon className="h-6 w-6" />
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 border-l-4 border-orange-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Collisions</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{summaryStats.withCollisions}</p>
              </div>
              <div className="p-3 bg-orange-100 text-orange-600 dark:bg-orange-900 dark:text-orange-400 rounded-full">
                <FireIcon className="h-6 w-6" />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white dark:bg-gray-800 shadow-lg rounded-xl p-6">
        <div className="flex items-center mb-4">
          <FunnelIcon className="h-5 w-5 text-gray-400 mr-2" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">Filters</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          {/* Search */}
          <div className="lg:col-span-2">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Search
            </label>
            <div className="relative rounded-md shadow-sm">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />
              </div>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="block w-full pl-10 border-gray-300 dark:border-gray-600 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                placeholder="Search by name, route ID, or file..."
              />
            </div>
          </div>

          {/* Status Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Status
            </label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="block w-full border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
            >
              <option value="">All statuses</option>
              <option value="completed">Completed</option>
              <option value="running">Running</option>
              <option value="failed">Failed</option>
              <option value="stopped">Stopped</option>
              <option value="created">Created</option>
            </select>
          </div>

          {/* Method Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Method
            </label>
            <select
              value={methodFilter}
              onChange={(e) => setMethodFilter(e.target.value)}
              className="block w-full border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
            >
              <option value="">All methods</option>
              <option value="random">Random</option>
              <option value="pso">PSO</option>
              <option value="ga">Genetic Algorithm</option>
            </select>
          </div>

          {/* Agent Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Agent
            </label>
            <select
              value={agentFilter}
              onChange={(e) => setAgentFilter(e.target.value)}
              className="block w-full border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
            >
              <option value="">All agents</option>
              <option value="ba">🤖 Behavior Agent</option>
              <option value="apollo">🚀 Apollo</option>
            </select>
          </div>
        </div>
      </div>

      {/* Experiments Table */}
      <div className="bg-white dark:bg-gray-800 shadow-lg overflow-hidden rounded-xl">
        {isLoading ? (
          <div className="p-8">
            <div className="animate-pulse space-y-4">
              {[...Array(8)].map((_, i) => (
                <div key={i} className="flex items-center space-x-4">
                  <div className="h-12 w-12 bg-gray-200 dark:bg-gray-700 rounded-full"></div>
                  <div className="flex-1 space-y-2">
                    <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
                    <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
                  </div>
                  <div className="h-8 w-24 bg-gray-200 dark:bg-gray-700 rounded"></div>
                </div>
              ))}
            </div>
          </div>
        ) : filteredExperiments && filteredExperiments.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Experiment
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Method
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Agent
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Progress
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Results
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Duration
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Created
                  </th>
                  <th className="px-6 py-4 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {filteredExperiments.map((experiment) => (
                  <ExperimentRow 
                    key={experiment.id} 
                    experiment={experiment} 
                    onDuplicate={(id) => duplicateMutation.mutate(id)}
                    duplicating={duplicateMutation.isPending}
                    onDelete={(id) => deleteMutation.mutate(id)}
                    deleting={deleteMutation.isPending}
                    onDownload={(id) => downloadMutation.mutate(id)}
                    downloading={downloadMutation.isPending}
                  />
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-16">
            <div className="max-w-md mx-auto">
              <BeakerIcon className="mx-auto h-16 w-16 text-gray-400 mb-4" />
              <h3 className="text-xl font-medium text-gray-900 dark:text-white mb-2">
                No experiments found
              </h3>
              <p className="text-gray-500 dark:text-gray-400 mb-6">
                {searchQuery || statusFilter || methodFilter || agentFilter
                  ? 'Try adjusting your filters to see more results.'
                  : 'Get started by creating your first experiment.'
                }
              </p>
              <Link
                to="/experiment"
                className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-lg shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >
                <PlayIcon className="h-5 w-5 mr-2" />
                New Experiment
              </Link>
            </div>
          </div>
        )}
      </div>

      {/* Pagination */}
      {filteredExperiments && filteredExperiments.length >= limit && (
        <div className="bg-white dark:bg-gray-800 px-6 py-4 flex items-center justify-between border-t border-gray-200 dark:border-gray-700 rounded-b-xl">
          <div className="flex-1 flex justify-between sm:hidden">
            <button
              onClick={() => setOffset(Math.max(0, offset - limit))}
              disabled={offset === 0}
              className="relative inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <button
              onClick={() => setOffset(offset + limit)}
              disabled={filteredExperiments.length < limit}
              className="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
          <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
            <div>
              <p className="text-sm text-gray-700 dark:text-gray-300">
                Showing <span className="font-medium">{offset + 1}</span> to{' '}
                <span className="font-medium">{offset + filteredExperiments.length}</span> of{' '}
                <span className="font-medium">{filteredExperiments.length}</span> results
              </p>
            </div>
            <div>
              <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
                <button
                  onClick={() => setOffset(Math.max(0, offset - limit))}
                  disabled={offset === 0}
                  className="relative inline-flex items-center px-4 py-2 rounded-l-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm font-medium text-gray-500 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <button
                  onClick={() => setOffset(offset + limit)}
                  disabled={filteredExperiments.length < limit}
                  className="relative inline-flex items-center px-4 py-2 rounded-r-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm font-medium text-gray-500 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </nav>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  )
}

function ExperimentRow({ 
  experiment, 
  onDuplicate,
  duplicating,
  onDelete, 
  deleting,
  onDownload,
  downloading
}: { 
  experiment: ExperimentListItem
  onDuplicate: (id: string) => void
  duplicating: boolean
  onDelete: (id: string) => void
  deleting: boolean
  onDownload: (id: string) => void
  downloading: boolean
}) {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />
      case 'running':
        return <PlayIcon className="h-5 w-5 text-blue-500 animate-pulse" />
      case 'failed':
        return <XCircleIcon className="h-5 w-5 text-red-500" />
      case 'stopped':
        return <StopIcon className="h-5 w-5 text-yellow-500" />
      default:
        return <ClockIcon className="h-5 w-5 text-gray-500" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-600 bg-green-100 dark:bg-green-900 dark:text-green-400'
      case 'running': return 'text-blue-600 bg-blue-100 dark:bg-blue-900 dark:text-blue-400'
      case 'failed': return 'text-red-600 bg-red-100 dark:bg-red-900 dark:text-red-400'
      case 'stopped': return 'text-yellow-600 bg-yellow-100 dark:bg-yellow-900 dark:text-yellow-400'
      default: return 'text-gray-600 bg-gray-100 dark:bg-gray-700 dark:text-gray-400'
    }
  }

  const formatDuration = (startTime: string, endTime?: string) => {
    if (!endTime) return 'In progress...'
    
    const start = new Date(startTime)
    const end = new Date(endTime)
    const duration = end.getTime() - start.getTime()
    
    const hours = Math.floor(duration / (1000 * 60 * 60))
    const minutes = Math.floor((duration % (1000 * 60 * 60)) / (1000 * 60))
    const seconds = Math.floor((duration % (1000 * 60)) / 1000)
    
    if (hours > 0) {
      return `${hours}h ${minutes}m`
    } else if (minutes > 0) {
      return `${minutes}m ${seconds}s`
    } else {
      return `${seconds}s`
    }
  }

  return (
    <tr className="hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="flex items-center">
          <div className="flex-shrink-0 h-10 w-10">
            <div className={clsx(
              'h-10 w-10 rounded-full flex items-center justify-center',
              getStatusColor(experiment.status)
            )}>
              {getStatusIcon(experiment.status)}
            </div>
          </div>
          <div className="ml-4">
            <div className="text-sm font-medium text-gray-900 dark:text-white">
              <Link
                to={`/experiment/${experiment.id}`}
                className="hover:text-indigo-600 dark:hover:text-indigo-400"
              >
                {experiment.name}
              </Link>
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Route {experiment.route_name || experiment.route_id} • {experiment.route_file}
            </p>
          </div>
        </div>
      </td>

      <td className="px-6 py-4 whitespace-nowrap">
        <span className={clsx(
          'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
          getStatusColor(experiment.status)
        )}>
          {experiment.status.charAt(0).toUpperCase() + experiment.status.slice(1)}
        </span>
      </td>

      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
        {experiment.search_method.toUpperCase()}
      </td>

      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
        <span className={clsx(
          'inline-flex items-center px-2 py-1 rounded text-xs font-medium',
          experiment.agent === 'apollo' 
            ? 'text-purple-800 bg-purple-100 dark:bg-purple-900 dark:text-purple-200'
            : 'text-blue-800 bg-blue-100 dark:bg-blue-900 dark:text-blue-200'
        )}>
          {experiment.agent === 'apollo' ? '🚀 Apollo' : '🤖 BA'}
        </span>
      </td>

      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
        {experiment.total_iterations ? (
          <div className="flex items-center">
            <div className="flex-1">
              <div className="text-xs text-gray-500 dark:text-gray-400">
                {experiment.total_iterations} iterations
              </div>
            </div>
          </div>
        ) : (
          <span className="text-gray-500 dark:text-gray-400">-</span>
        )}
      </td>

      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
        <div className="space-y-1">
          {typeof experiment.collision_found === 'boolean' && (
            <div className={clsx(
              'text-xs px-2 py-1 rounded',
              experiment.collision_found 
                ? 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-400'
                : 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-400'
            )}>
              {experiment.collision_found ? 'Collision Found' : 'No Collision'}
            </div>
          )}
          {typeof experiment.best_reward === 'number' && (
            <div className="text-xs text-gray-500 dark:text-gray-400">
              Best: {experiment.best_reward.toFixed(3)}
            </div>
          )}
        </div>
      </td>

      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
        {formatDuration(experiment.created_at, experiment.completed_at)}
      </td>

      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
        {new Date(experiment.created_at).toLocaleDateString()}
      </td>

      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
        <div className="flex items-center justify-end space-x-2">
          <Link
            to={`/experiment/${experiment.id}`}
            className="text-indigo-600 hover:text-indigo-900 dark:text-indigo-400 dark:hover:text-indigo-300"
            title="View details"
          >
            <EyeIcon className="h-4 w-4" />
          </Link>
          
          {experiment.status === 'completed' && (
            <button
              onClick={() => onDownload(experiment.id)}
              disabled={downloading}
              className="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300 disabled:opacity-50"
              title="Download results"
            >
              <ArrowDownTrayIcon className="h-4 w-4" />
            </button>
          )}
          
          <button
            onClick={() => onDuplicate(experiment.id)}
            disabled={duplicating}
            className="text-indigo-600 hover:text-indigo-900 dark:text-indigo-400 dark:hover:text-indigo-300 disabled:opacity-50"
            title="Duplicate experiment"
          >
            <DocumentDuplicateIcon className="h-4 w-4" />
          </button>
          
          <button
            onClick={() => {
              if (window.confirm(`Are you sure you want to delete experiment "${experiment.name}"? This action cannot be undone.`)) {
                onDelete(experiment.id)
              }
            }}
            disabled={deleting}
            className="text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300 disabled:opacity-50"
            title="Delete experiment"
          >
            <TrashIcon className="h-4 w-4" />
          </button>
        </div>
      </td>
    </tr>
  )
} 