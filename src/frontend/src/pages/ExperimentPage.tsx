import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  PlayIcon,
  StopIcon,
  ArrowDownTrayIcon,
  ChartBarIcon,
  InformationCircleIcon,
  BeakerIcon,
  DocumentIcon,
  TrashIcon,
  DocumentDuplicateIcon
} from '@heroicons/react/24/outline'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { apiClient } from '../services/api'
import type { ExperimentConfig, ExperimentData } from '../types'
import { AGENT_OPTIONS } from '../types/experiment'
import { LogViewer } from '../components/common/LogViewer'
import { RewardChart } from '../components/common/RewardChart'
import { generateExperimentName } from '../utils/nameGenerator'
import { getPrimaryProgress, getSecondaryProgress, formatProgressPercentage, getPollingInterval } from '../utils/progressUtils'
import clsx from 'clsx'

// Form validation schema
const experimentSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters').max(100, 'Name must be less than 100 characters'),
  route_id: z.string().min(1, 'Route ID is required'),
  route_file: z.string().min(1, 'Route file is required'),
  search_method: z.enum(['random', 'pso', 'ga']),
  agent: z.enum(['ba', 'apollo']),
  num_iterations: z.number().min(1).max(10000),
  timeout_seconds: z.number().min(30).max(3600),
  headless: z.boolean(),
  random_seed: z.number().min(0),
  reward_function: z.enum(['collision', 'distance', 'safety_margin', 'ttc', 'ttc_div_dist', 'weighted_multi']),
  // PSO parameters
  pso_pop_size: z.number().min(1).max(1000).optional(),
  pso_w: z.number().min(0).max(2).optional(),
  pso_c1: z.number().min(0).max(4).optional(),
  pso_c2: z.number().min(0).max(4).optional(),
  // GA parameters  
  ga_pop_size: z.number().min(1).max(1000).optional(),
  ga_prob_mut: z.number().min(0).max(1).optional(),
})

type ExperimentFormData = z.infer<typeof experimentSchema>

export function ExperimentPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [selectedRoute, setSelectedRoute] = useState<string>('')
  
  // Check if we're in edit mode (from URL params)
  const searchParams = new URLSearchParams(window.location.search)
  const isEditMode = searchParams.get('edit') === 'true'
  
  const isEditing = Boolean(id)
  const isCreating = !id
  const isEditingConfig = isCreating || isEditMode

  // Fetch existing experiment if editing
  const { data: experiment, isLoading: experimentLoading } = useQuery({
    queryKey: ['experiment', id],
    queryFn: () => apiClient.getExperiment(id!),
    enabled: isEditing,
    refetchInterval: (query) => {
      // Use utility function to determine polling interval
      if (query.state.data) {
        return getPollingInterval(query.state.data)
      }
      return 10000 // Default fallback
    },
  })

  // Fetch route files
  const { data: routeFiles } = useQuery({
    queryKey: ['route-files'],
    queryFn: () => apiClient.listRouteFiles(),
  })

  // Fetch routes for selected file
  const { data: routes } = useQuery({
    queryKey: ['routes', selectedRoute],
    queryFn: () => apiClient.listRoutes(selectedRoute),
    enabled: Boolean(selectedRoute),
  })

  // Form setup
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isSubmitting }
  } = useForm<ExperimentFormData>({
    resolver: zodResolver(experimentSchema),
    defaultValues: {
      name: generateExperimentName('mixed'),
      search_method: 'random',
      agent: 'ba',
      num_iterations: 100,
      timeout_seconds: 300,
      headless: false,
      random_seed: Math.floor(Math.random() * 1000000),
      reward_function: 'collision',
      pso_pop_size: 20,
      pso_w: 0.9,
      pso_c1: 0.5,
      pso_c2: 0.3,
      ga_pop_size: 30,
      ga_prob_mut: 0.1,
    }
  })

  const searchMethod = watch('search_method')
  const routeFile = watch('route_file')

  // Update selected route when route_file changes
  useEffect(() => {
    if (routeFile && routeFile !== selectedRoute) {
      setSelectedRoute(routeFile)
    }
  }, [routeFile, selectedRoute])

  // Populate form when editing existing experiment
  useEffect(() => {
    if (experiment) {
      const config = experiment.config
      setValue('name', config.name)
      setValue('route_id', config.route_id)
      setValue('route_file', config.route_file)
      setValue('search_method', config.search_method)
      setValue('agent', (config.agent || 'ba') as 'ba' | 'apollo')
      setValue('num_iterations', config.num_iterations)
      setValue('timeout_seconds', config.timeout_seconds)
      setValue('headless', config.headless)
      setValue('random_seed', config.random_seed)
      setValue('reward_function', config.reward_function)
      
      if (config.pso_pop_size) setValue('pso_pop_size', config.pso_pop_size)
      if (config.pso_w) setValue('pso_w', config.pso_w)
      if (config.pso_c1) setValue('pso_c1', config.pso_c1)
      if (config.pso_c2) setValue('pso_c2', config.pso_c2)
      if (config.ga_pop_size) setValue('ga_pop_size', config.ga_pop_size)
      if (config.ga_prob_mut) setValue('ga_prob_mut', config.ga_prob_mut)
      
      setSelectedRoute(config.route_file)
    }
  }, [experiment, setValue])

  // Create experiment mutation
  const createMutation = useMutation({
    mutationFn: ({ config, startImmediately }: { config: ExperimentConfig; startImmediately: boolean }) =>
      apiClient.createExperiment(config, startImmediately),
    onSuccess: (data) => {
      toast.success('Experiment created successfully!')
      queryClient.invalidateQueries({ queryKey: ['experiments'] })
      navigate(`/experiment/${data.id}`)
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create experiment')
    }
  })

  // Start experiment mutation
  const startMutation = useMutation({
    mutationFn: (experimentId: string) => apiClient.startExperiment(experimentId),
    onSuccess: () => {
      toast.success('Experiment started!')
      queryClient.invalidateQueries({ queryKey: ['experiment', id] })
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to start experiment')
    }
  })

  // Stop experiment mutation
  const stopMutation = useMutation({
    mutationFn: (experimentId: string) => apiClient.stopExperiment(experimentId),
    onSuccess: () => {
      toast.success('Experiment stopped!')
      queryClient.invalidateQueries({ queryKey: ['experiment', id] })
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to stop experiment')
    }
  })

  // Duplicate experiment mutation
  const duplicateMutation = useMutation({
    mutationFn: (experimentId: string) => apiClient.duplicateExperiment(experimentId),
    onSuccess: (data) => {
      toast.success('Experiment duplicated successfully!')
      queryClient.invalidateQueries({ queryKey: ['experiments'] })
      navigate(`/experiment/${data.id}?edit=true`)
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to duplicate experiment')
    }
  })

  // Delete experiment mutation
  const deleteMutation = useMutation({
    mutationFn: (experimentId: string) => apiClient.deleteExperiment(experimentId),
    onSuccess: () => {
      toast.success('Experiment deleted successfully!')
      queryClient.invalidateQueries({ queryKey: ['experiments'] })
      navigate('/history')
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

  const onSubmit = (data: ExperimentFormData) => {
    // Find the selected route to get its name
    const selectedRoute = routes?.find(route => route.route_id === data.route_id)
    
    const config: ExperimentConfig = {
      name: data.name,
      route_id: data.route_id,
      route_name: selectedRoute?.route_name,  // Include route name
      route_file: data.route_file,
      search_method: data.search_method,
      agent: data.agent,
      num_iterations: data.num_iterations,
      timeout_seconds: data.timeout_seconds,
      headless: data.headless,
      random_seed: data.random_seed,
      reward_function: data.reward_function,
    }

    // Add method-specific parameters
    if (data.search_method === 'pso') {
      config.pso_pop_size = data.pso_pop_size
      config.pso_w = data.pso_w
      config.pso_c1 = data.pso_c1
      config.pso_c2 = data.pso_c2
    } else if (data.search_method === 'ga') {
      config.ga_pop_size = data.ga_pop_size
      config.ga_prob_mut = data.ga_prob_mut
    }

    createMutation.mutate({ config, startImmediately: false })
  }

  const handleExitEditMode = () => {
    if (id) {
      navigate(`/experiment/${id}`)
    }
  }

  const handleStartExperiment = () => {
    if (id) {
      startMutation.mutate(id)
    }
  }

  const handleStopExperiment = () => {
    if (id) {
      stopMutation.mutate(id)
    }
  }

  const handleDuplicateExperiment = () => {
    if (id) {
      duplicateMutation.mutate(id)
    }
  }

  const handleDeleteExperiment = () => {
    if (id && experiment) {
      if (window.confirm(`Are you sure you want to delete experiment "${experiment.name}"? This action cannot be undone.`)) {
        deleteMutation.mutate(id)
      }
    }
  }

  const handleDownloadExperiment = () => {
    if (id) {
      downloadMutation.mutate(id)
    }
  }

  if (experimentLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    )
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
            {isCreating 
              ? 'New Experiment' 
              : isEditMode 
                ? `Edit: ${experiment?.name || 'Experiment'}` 
                : experiment?.name || 'Experiment Details'
            }
          </h1>
          <p className="mt-2 text-lg text-gray-600 dark:text-gray-400">
            {isCreating 
              ? 'Configure a new fuzzing experiment'
              : isEditMode 
                ? 'Edit the configuration and run the experiment'
                : 'Configure and monitor your fuzzing experiment'
            }
          </p>
        </div>

        {isEditing && experiment && (
          <div className="flex space-x-3">
            {experiment.status === 'created' && (
              <button
                onClick={handleStartExperiment}
                disabled={startMutation.isPending}
                className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-lg shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 transition-all duration-200"
              >
                <PlayIcon className="h-5 w-5 mr-2" />
                {startMutation.isPending ? 'Starting...' : 'Start'}
              </button>
            )}
            
            {experiment.status === 'running' && (
              <button
                onClick={handleStopExperiment}
                disabled={stopMutation.isPending}
                className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-lg shadow-sm text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50 transition-all duration-200"
              >
                <StopIcon className="h-5 w-5 mr-2" />
                {stopMutation.isPending ? 'Stopping...' : 'Stop'}
              </button>
            )}

            {experiment.status === 'completed' && (
              <button
                onClick={handleDownloadExperiment}
                disabled={downloadMutation.isPending}
                className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-lg shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 transition-all duration-200"
              >
                <ArrowDownTrayIcon className="h-5 w-5 mr-2" />
                {downloadMutation.isPending ? 'Downloading...' : 'Download'}
              </button>
            )}
            
            <button
              onClick={handleDuplicateExperiment}
              disabled={duplicateMutation.isPending}
              className="inline-flex items-center px-6 py-3 border border-gray-300 text-base font-medium rounded-lg shadow-sm text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-600 dark:hover:bg-gray-700 transition-all duration-200"
            >
              <DocumentDuplicateIcon className="h-5 w-5 mr-2" />
              {duplicateMutation.isPending ? 'Duplicating...' : 'Duplicate'}
            </button>
            
            <button
              onClick={handleDeleteExperiment}
              disabled={deleteMutation.isPending}
              className="inline-flex items-center px-6 py-3 border border-gray-300 text-base font-medium rounded-lg shadow-sm text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50 dark:bg-gray-800 dark:text-red-400 dark:border-gray-600 dark:hover:bg-red-900/20 transition-all duration-200"
            >
              <TrashIcon className="h-5 w-5 mr-2" />
              {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
            </button>
          </div>
        )}
      </div>

      {/* Status Card (for existing experiments) */}
      {isEditing && experiment && (
        <ExperimentStatus experiment={experiment} />
      )}

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        {/* Left Column - Configuration Form */}
        <div className="xl:col-span-2">
          <div className="bg-white dark:bg-gray-800 shadow-lg rounded-xl">
            <div className="px-6 py-6 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-indigo-100 dark:bg-indigo-900 rounded-lg">
                  <BeakerIcon className="h-6 w-6 text-indigo-600 dark:text-indigo-400" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
                  Experiment Configuration
                </h3>
              </div>
            </div>

            <div className="p-6">
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-8">
                {/* Experiment Name */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Experiment Name
                  </label>
                  <div className="flex space-x-3">
                    <input
                      type="text"
                      {...register('name')}
                      disabled={!isEditingConfig}
                      placeholder="Enter a descriptive name for your experiment"
                      className="flex-1 border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white disabled:bg-gray-100 dark:disabled:bg-gray-600 text-base py-3 px-4"
                    />
                    {isEditingConfig && (
                      <button
                        type="button"
                        onClick={() => setValue('name', generateExperimentName('mixed'))}
                        className="px-4 py-3 text-base bg-gray-100 hover:bg-gray-200 dark:bg-gray-600 dark:hover:bg-gray-500 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 transition-colors"
                        title="Generate random name"
                      >
                        🎲
                      </button>
                    )}
                  </div>
                  {errors.name && (
                    <p className="mt-2 text-sm text-red-600">{errors.name.message}</p>
                  )}
                </div>

                {/* Route Selection */}
                <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-6">
                  <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Scenario Configuration</h4>
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Route File
                      </label>
                      <select
                        {...register('route_file')}
                        disabled={!isEditingConfig}
                        className="block w-full border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white disabled:bg-gray-100 dark:disabled:bg-gray-600 text-base py-3 px-4"
                      >
                        <option value="">Select route file...</option>
                        {routeFiles?.map((file) => (
                          <option key={file.filename} value={file.filename}>
                            {file.filename} ({file.total_routes} routes)
                          </option>
                        ))}
                      </select>
                      {errors.route_file && (
                        <p className="mt-2 text-sm text-red-600">{errors.route_file.message}</p>
                      )}
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Route
                      </label>
                      <select
                        {...register('route_id')}
                        disabled={!isEditingConfig || !routes}
                        className="block w-full border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white disabled:bg-gray-100 dark:disabled:bg-gray-600 text-base py-3 px-4"
                      >
                        <option value="">Select route...</option>
                        {routes?.map((route) => (
                          <option key={route.route_id} value={route.route_id}>
                            {route.route_name || route.route_id} {route.town ? `(${route.town})` : ''}
                          </option>
                        ))}
                      </select>
                      {errors.route_id && (
                        <p className="mt-2 text-sm text-red-600">{errors.route_id.message}</p>
                      )}
                    </div>
                  </div>
                </div>

                {/* Basic Parameters */}
                <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-6">
                  <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Basic Parameters</h4>
                  <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Search Method
                      </label>
                      <select
                        {...register('search_method')}
                        disabled={!isEditingConfig}
                        className="block w-full border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white disabled:bg-gray-100 dark:disabled:bg-gray-600 text-base py-3 px-4"
                      >
                        <option value="random">Random</option>
                        <option value="pso">Particle Swarm Optimization</option>
                        <option value="ga">Genetic Algorithm</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Agent Type
                      </label>
                      <select
                        {...register('agent')}
                        disabled={!isEditingConfig}
                        className="block w-full border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white disabled:bg-gray-100 dark:disabled:bg-gray-600 text-base py-3 px-4"
                      >
                        {AGENT_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                      <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                        {AGENT_OPTIONS.find(opt => opt.value === watch('agent'))?.description}
                      </p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Iterations
                      </label>
                      <input
                        type="number"
                        {...register('num_iterations', { valueAsNumber: true })}
                        disabled={!isEditingConfig}
                        className="block w-full border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white disabled:bg-gray-100 dark:disabled:bg-gray-600 text-base py-3 px-4"
                      />
                      {errors.num_iterations && (
                        <p className="mt-2 text-sm text-red-600">{errors.num_iterations.message}</p>
                      )}
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Timeout (seconds)
                      </label>
                      <input
                        type="number"
                        {...register('timeout_seconds', { valueAsNumber: true })}
                        disabled={!isEditingConfig}
                        className="block w-full border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white disabled:bg-gray-100 dark:disabled:bg-gray-600 text-base py-3 px-4"
                      />
                      {errors.timeout_seconds && (
                        <p className="mt-2 text-sm text-red-600">{errors.timeout_seconds.message}</p>
                      )}
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Reward Function
                      </label>
                      <select
                        {...register('reward_function')}
                        disabled={!isEditingConfig}
                        className="block w-full border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white disabled:bg-gray-100 dark:disabled:bg-gray-600 text-base py-3 px-4"
                      >
                        <option value="collision">Collision</option>
                        <option value="distance">Distance</option>
                        <option value="safety_margin">Safety Margin</option>
                        <option value="ttc">Time to Collision</option>
                        <option value="ttc_div_dist">TTC / Distance</option>
                        <option value="weighted_multi">Weighted Multi</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Random Seed
                      </label>
                      <input
                        type="number"
                        {...register('random_seed', { valueAsNumber: true })}
                        disabled={!isEditingConfig}
                        className="block w-full border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white disabled:bg-gray-100 dark:disabled:bg-gray-600 text-base py-3 px-4"
                      />
                    </div>
                  </div>

                  <div className="mt-6">
                    <div className="flex items-center">
                      <input
                        type="checkbox"
                        {...register('headless')}
                        disabled={!isEditingConfig}
                        className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded disabled:bg-gray-100"
                      />
                      <label className="ml-2 block text-sm text-gray-900 dark:text-white">
                        Headless mode
                      </label>
                    </div>
                  </div>
                </div>

                {/* Method-specific parameters */}
                {searchMethod === 'pso' && (
                  <PSOParameters register={register} errors={errors} disabled={!isEditingConfig} />
                )}

                {searchMethod === 'ga' && (
                  <GAParameters register={register} errors={errors} disabled={!isEditingConfig} />
                )}

                {/* Submit button (for new experiments and edit mode) */}
                {isEditingConfig && (
                  <div className="flex justify-end space-x-4 pt-6 border-t border-gray-200 dark:border-gray-700">
                    <button
                      type="button"
                      onClick={() => navigate('/history')}
                      className="px-6 py-3 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm text-base font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
                    >
                      Cancel
                    </button>
                    {isEditMode && (
                      <button
                        type="button"
                        onClick={handleExitEditMode}
                        className="px-6 py-3 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm text-base font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
                      >
                        View Only
                      </button>
                    )}
                    <button
                      type="submit"
                      disabled={isSubmitting || createMutation.isPending}
                      className="inline-flex justify-center px-6 py-3 border border-transparent shadow-sm text-base font-medium rounded-lg text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 transition-colors"
                    >
                      {createMutation.isPending ? 'Creating...' : isEditMode ? 'Save & Create' : 'Create Experiment'}
                    </button>
                  </div>
                )}
              </form>
            </div>
          </div>
        </div>

        {/* Right Column - Progress & Actions */}
        <div className="xl:col-span-1 space-y-6">
          {/* Real-time Reward Chart (for experiments with data) */}
          {isEditing && experiment && experiment.progress?.reward_history && experiment.progress.reward_history.length > 0 && (
            <div className="bg-white dark:bg-gray-800 shadow-lg rounded-xl p-6">
              <div className="flex items-center space-x-3 mb-4">
                <div className="p-2 bg-green-100 dark:bg-green-900 rounded-lg">
                  <ChartBarIcon className="h-5 w-5 text-green-600 dark:text-green-400" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Reward Progress
                </h3>
              </div>
              <RewardChart 
                rewardHistory={experiment.progress.reward_history}
                title=""
                isRunning={experiment.status === 'running'}
                height={300}
                className=""
              />
            </div>
          )}

          {/* Quick Actions (for new experiments) */}
          {isCreating && (
            <div className="bg-white dark:bg-gray-800 shadow-lg rounded-xl p-6">
              <div className="flex items-center space-x-3 mb-4">
                <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
                  <InformationCircleIcon className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Quick Start Guide
                </h3>
              </div>
              <div className="space-y-3 text-sm text-gray-600 dark:text-gray-400">
                <div className="flex items-start space-x-3">
                  <span className="flex-shrink-0 w-6 h-6 bg-indigo-100 dark:bg-indigo-900 text-indigo-600 dark:text-indigo-400 rounded-full flex items-center justify-center text-xs font-medium">1</span>
                  <p>Select a route file and specific route</p>
                </div>
                <div className="flex items-start space-x-3">
                  <span className="flex-shrink-0 w-6 h-6 bg-indigo-100 dark:bg-indigo-900 text-indigo-600 dark:text-indigo-400 rounded-full flex items-center justify-center text-xs font-medium">2</span>
                  <p>Choose your search method and agent type</p>
                </div>
                <div className="flex items-start space-x-3">
                  <span className="flex-shrink-0 w-6 h-6 bg-indigo-100 dark:bg-indigo-900 text-indigo-600 dark:text-indigo-400 rounded-full flex items-center justify-center text-xs font-medium">3</span>
                  <p>Configure iterations and timeout</p>
                </div>
                <div className="flex items-start space-x-3">
                  <span className="flex-shrink-0 w-6 h-6 bg-indigo-100 dark:bg-indigo-900 text-indigo-600 dark:text-indigo-400 rounded-full flex items-center justify-center text-xs font-medium">4</span>
                  <p>Create and start your experiment</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Real-time Logs (for existing experiments) */}
      {isEditing && experiment && (
        <LogViewer 
          experimentId={experiment.id} 
          isRunning={experiment.status === 'running'}
          experimentStatus={experiment.status}
        />
      )}
    </motion.div>
  )
}

// Component for PSO parameters
function PSOParameters({ register, errors, disabled }: any) {
  return (
    <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
      <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-3">
        Particle Swarm Optimization Parameters
      </h4>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div>
          <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">
            Population Size
          </label>
          <input
            type="number"
            {...register('pso_pop_size', { valueAsNumber: true })}
            disabled={disabled}
            className="mt-1 block w-full border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 text-sm dark:bg-gray-700 dark:text-white disabled:bg-gray-100 dark:disabled:bg-gray-600"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">
            Inertia Weight (w)
          </label>
          <input
            type="number"
            step="0.1"
            {...register('pso_w', { valueAsNumber: true })}
            disabled={disabled}
            className="mt-1 block w-full border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 text-sm dark:bg-gray-700 dark:text-white disabled:bg-gray-100 dark:disabled:bg-gray-600"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">
            Cognitive Coeff (c1)
          </label>
          <input
            type="number"
            step="0.1"
            {...register('pso_c1', { valueAsNumber: true })}
            disabled={disabled}
            className="mt-1 block w-full border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 text-sm dark:bg-gray-700 dark:text-white disabled:bg-gray-100 dark:disabled:bg-gray-600"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">
            Social Coeff (c2)
          </label>
          <input
            type="number"
            step="0.1"
            {...register('pso_c2', { valueAsNumber: true })}
            disabled={disabled}
            className="mt-1 block w-full border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 text-sm dark:bg-gray-700 dark:text-white disabled:bg-gray-100 dark:disabled:bg-gray-600"
          />
        </div>
      </div>
    </div>
  )
}

// Component for GA parameters
function GAParameters({ register, errors, disabled }: any) {
  return (
    <div className="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg">
      <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-3">
        Genetic Algorithm Parameters
      </h4>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">
            Population Size
          </label>
          <input
            type="number"
            {...register('ga_pop_size', { valueAsNumber: true })}
            disabled={disabled}
            className="mt-1 block w-full border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 text-sm dark:bg-gray-700 dark:text-white disabled:bg-gray-100 dark:disabled:bg-gray-600"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">
            Mutation Probability
          </label>
          <input
            type="number"
            step="0.01"
            {...register('ga_prob_mut', { valueAsNumber: true })}
            disabled={disabled}
            className="mt-1 block w-full border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 text-sm dark:bg-gray-700 dark:text-white disabled:bg-gray-100 dark:disabled:bg-gray-600"
          />
        </div>
      </div>
    </div>
  )
}

// Component for enhanced progress display
function EnhancedProgressDisplay({ experiment }: { experiment: ExperimentData }) {
  const primaryProgress = getPrimaryProgress(experiment)
  const secondaryProgress = getSecondaryProgress(experiment)
  
  return (
    <div className="mt-4 space-y-4">
      {/* Primary Progress Bar */}
      <div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-500 dark:text-gray-400">{primaryProgress.label}</span>
          <span className="text-gray-900 dark:text-white">
            {primaryProgress.current} / {primaryProgress.total}
          </span>
        </div>
        <div className="mt-1 w-full bg-gray-200 rounded-full h-2 dark:bg-gray-700">
          <div 
            className="bg-indigo-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${primaryProgress.percentage}%` }}
          />
        </div>
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{primaryProgress.subtitle}</p>
      </div>

      {/* Method-specific details for PSO/GA */}
      {secondaryProgress && (
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-gray-500 dark:text-gray-400">Optimization Progress</div>
            <div className="font-medium text-gray-900 dark:text-white">
              {secondaryProgress.optimization_progress}
            </div>
          </div>
          <div>
            <div className="text-gray-500 dark:text-gray-400">Current Iteration</div>
            <div className="font-medium text-gray-900 dark:text-white">
              {secondaryProgress.current_iteration_progress}
            </div>
          </div>
        </div>
      )}

      {/* Results Information */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
        {experiment.progress?.best_reward !== null && experiment.progress?.best_reward !== undefined && (
          <div>
            <div className="text-gray-500 dark:text-gray-400">Best Reward</div>
            <div className="font-medium text-gray-900 dark:text-white">
              {experiment.progress.best_reward.toFixed(3)}
            </div>
          </div>
        )}
        
        {experiment.progress?.collision_found && (
          <div>
            <div className="text-gray-500 dark:text-gray-400">Collision Status</div>
            <div className="font-medium text-red-600 dark:text-red-400">
              🎯 Collision Found!
            </div>
          </div>
        )}
        
        {experiment.progress?.elapsed_time !== null && experiment.progress?.elapsed_time !== undefined && (
          <div>
            <div className="text-gray-500 dark:text-gray-400">Elapsed Time</div>
            <div className="font-medium text-gray-900 dark:text-white">
              {Math.round(experiment.progress.elapsed_time)}s
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// Component for experiment status
function ExperimentStatus({ experiment }: { experiment: ExperimentData }) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-600 bg-green-100 dark:bg-green-900 dark:text-green-400'
      case 'running': return 'text-blue-600 bg-blue-100 dark:bg-blue-900 dark:text-blue-400'
      case 'failed': return 'text-red-600 bg-red-100 dark:bg-red-900 dark:text-red-400'
      case 'stopped': return 'text-yellow-600 bg-yellow-100 dark:bg-yellow-900 dark:text-yellow-400'
      default: return 'text-gray-600 bg-gray-100 dark:bg-gray-700 dark:text-gray-400'
    }
  }

  return (
    <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">
            {experiment.name}
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Route: {experiment.config.route_name || experiment.config.route_id} • File: {experiment.config.route_file} • Agent: {experiment.config.agent === 'apollo' ? '🚀 Apollo' : '🤖 BA'}
          </p>
        </div>
        <span className={clsx(
          'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
          getStatusColor(experiment.status)
        )}>
          {experiment.status.charAt(0).toUpperCase() + experiment.status.slice(1)}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div>
          <div className="text-sm text-gray-500 dark:text-gray-400">Created</div>
          <div className="text-sm font-medium text-gray-900 dark:text-white">
            {new Date(experiment.created_at).toLocaleString()}
          </div>
        </div>

        {experiment.started_at && (
          <div>
            <div className="text-sm text-gray-500 dark:text-gray-400">Started</div>
            <div className="text-sm font-medium text-gray-900 dark:text-white">
              {new Date(experiment.started_at).toLocaleString()}
            </div>
          </div>
        )}

        {experiment.completed_at && (
          <div>
            <div className="text-sm text-gray-500 dark:text-gray-400">Completed</div>
            <div className="text-sm font-medium text-gray-900 dark:text-white">
              {new Date(experiment.completed_at).toLocaleString()}
            </div>
          </div>
        )}

        {experiment.progress && (
          <div>
            <div className="text-sm text-gray-500 dark:text-gray-400">Progress</div>
            <div className="text-sm font-medium text-gray-900 dark:text-white">
              {experiment.progress.current_iteration} / {experiment.progress.total_iterations}
            </div>
          </div>
        )}
      </div>

      {experiment.progress && (
        <EnhancedProgressDisplay experiment={experiment} />
      )}

      {experiment.error_message && (
        <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
          <div className="text-sm text-red-600 dark:text-red-400">
            {experiment.error_message}
          </div>
        </div>
      )}
    </div>
  )
} 