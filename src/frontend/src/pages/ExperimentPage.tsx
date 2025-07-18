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
import clsx from 'clsx'

// Form validation schema
const experimentSchema = z.object({
  route_id: z.string().min(1, 'Route ID is required'),
  route_file: z.string().min(1, 'Route file is required'),
  search_method: z.enum(['random', 'pso', 'ga']),
  num_iterations: z.number().min(1).max(10000),
  timeout_seconds: z.number().min(30).max(3600),
  headless: z.boolean(),
  random_seed: z.number().min(0),
  reward_function: z.enum(['collision', 'distance', 'safety_margin', 'ttc', 'ttc_div_dist', 'weighted_multi']),
  // PSO parameters
  pso_pop_size: z.number().min(10).max(1000).optional(),
  pso_w: z.number().min(0).max(2).optional(),
  pso_c1: z.number().min(0).max(4).optional(),
  pso_c2: z.number().min(0).max(4).optional(),
  // GA parameters  
  ga_pop_size: z.number().min(10).max(1000).optional(),
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
      // Poll every 2 seconds if experiment is running, every 10 seconds otherwise
      if (query.state.data?.status === 'running') {
        return 2000 // 2 seconds for running experiments
      }
      return 10000 // 10 seconds for other statuses
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
      search_method: 'random',
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
      setValue('route_id', config.route_id)
      setValue('route_file', config.route_file)
      setValue('search_method', config.search_method)
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

  const onSubmit = (data: ExperimentFormData) => {
    const config: ExperimentConfig = {
      route_id: data.route_id,
      route_file: data.route_file,
      search_method: data.search_method,
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
      if (window.confirm(`Are you sure you want to delete experiment ${experiment.config.route_id}? This action cannot be undone.`)) {
        deleteMutation.mutate(id)
      }
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
      className="max-w-4xl mx-auto space-y-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            {isCreating ? 'New Experiment' : isEditMode ? 'Edit Experiment' : 'Experiment Details'}
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {isCreating 
              ? 'Configure a new fuzzing experiment'
              : isEditMode 
                ? 'Edit the configuration and run the experiment'
                : 'Configure and monitor your fuzzing experiment'
            }
          </p>
        </div>

        {isEditing && experiment && (
          <div className="flex space-x-2">
            {experiment.status === 'created' && (
              <button
                onClick={handleStartExperiment}
                disabled={startMutation.isPending}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50"
              >
                <PlayIcon className="h-4 w-4 mr-2" />
                Start
              </button>
            )}
            
            {experiment.status === 'running' && (
              <button
                onClick={handleStopExperiment}
                disabled={stopMutation.isPending}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50"
              >
                <StopIcon className="h-4 w-4 mr-2" />
                Stop
              </button>
            )}
            
            <button
              onClick={handleDuplicateExperiment}
              disabled={duplicateMutation.isPending}
              className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md shadow-sm text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-600 dark:hover:bg-gray-700"
            >
              <DocumentDuplicateIcon className="h-4 w-4 mr-2" />
              {duplicateMutation.isPending ? 'Duplicating...' : 'Duplicate'}
            </button>
            
            <button
              onClick={handleDeleteExperiment}
              disabled={deleteMutation.isPending}
              className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md shadow-sm text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50 dark:bg-gray-800 dark:text-red-400 dark:border-gray-600 dark:hover:bg-red-900/20"
            >
              <TrashIcon className="h-4 w-4 mr-2" />
              {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
            </button>
          </div>
        )}
      </div>

      {/* Status Card (for existing experiments) */}
      {isEditing && experiment && (
        <ExperimentStatus experiment={experiment} />
      )}

      {/* Configuration Form */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white mb-4">
            Experiment Configuration
          </h3>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            {/* Route Selection */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Route File
                </label>
                <select
                  {...register('route_file')}
                  disabled={!isEditingConfig}
                  className="mt-1 block w-full border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white disabled:bg-gray-100 dark:disabled:bg-gray-600"
                >
                  <option value="">Select route file...</option>
                  {routeFiles?.map((file) => (
                    <option key={file.filename} value={file.filename}>
                      {file.filename} ({file.total_routes} routes)
                    </option>
                  ))}
                </select>
                {errors.route_file && (
                  <p className="mt-1 text-sm text-red-600">{errors.route_file.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Route ID
                </label>
                <select
                  {...register('route_id')}
                  disabled={!isEditingConfig || !routes}
                  className="mt-1 block w-full border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white disabled:bg-gray-100 dark:disabled:bg-gray-600"
                >
                  <option value="">Select route...</option>
                  {routes?.map((route) => (
                    <option key={route.route_id} value={route.route_id}>
                      {route.route_id} ({route.town || 'Unknown'})
                    </option>
                  ))}
                </select>
                {errors.route_id && (
                  <p className="mt-1 text-sm text-red-600">{errors.route_id.message}</p>
                )}
              </div>
            </div>

            {/* Basic Parameters */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Search Method
                </label>
                <select
                  {...register('search_method')}
                  disabled={!isEditingConfig}
                  className="mt-1 block w-full border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white disabled:bg-gray-100 dark:disabled:bg-gray-600"
                >
                  <option value="random">Random</option>
                  <option value="pso">Particle Swarm Optimization</option>
                  <option value="ga">Genetic Algorithm</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Iterations
                </label>
                <input
                  type="number"
                  {...register('num_iterations', { valueAsNumber: true })}
                  disabled={!isEditingConfig}
                  className="mt-1 block w-full border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white disabled:bg-gray-100 dark:disabled:bg-gray-600"
                />
                {errors.num_iterations && (
                  <p className="mt-1 text-sm text-red-600">{errors.num_iterations.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Timeout (seconds)
                </label>
                <input
                  type="number"
                  {...register('timeout_seconds', { valueAsNumber: true })}
                  disabled={!isEditingConfig}
                  className="mt-1 block w-full border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white disabled:bg-gray-100 dark:disabled:bg-gray-600"
                />
                {errors.timeout_seconds && (
                  <p className="mt-1 text-sm text-red-600">{errors.timeout_seconds.message}</p>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Reward Function
                </label>
                <select
                  {...register('reward_function')}
                  disabled={!isEditingConfig}
                  className="mt-1 block w-full border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white disabled:bg-gray-100 dark:disabled:bg-gray-600"
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
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Random Seed
                </label>
                <input
                  type="number"
                  {...register('random_seed', { valueAsNumber: true })}
                  disabled={!isEditingConfig}
                  className="mt-1 block w-full border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white disabled:bg-gray-100 dark:disabled:bg-gray-600"
                />
              </div>

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

            {/* Method-specific parameters */}
            {searchMethod === 'pso' && (
              <PSOParameters register={register} errors={errors} disabled={!isEditingConfig} />
            )}

            {searchMethod === 'ga' && (
              <GAParameters register={register} errors={errors} disabled={!isEditingConfig} />
            )}

            {/* Submit button (for new experiments and edit mode) */}
            {isEditingConfig && (
              <div className="flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => navigate('/history')}
                  className="bg-white py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                  Cancel
                </button>
                {isEditMode && (
                  <button
                    type="button"
                    onClick={handleExitEditMode}
                    className="bg-white py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                  >
                    View Only
                  </button>
                )}
                <button
                  type="submit"
                  disabled={isSubmitting || createMutation.isPending}
                  className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                >
                  {createMutation.isPending ? 'Creating...' : isEditMode ? 'Save & Create' : 'Create Experiment'}
                </button>
              </div>
            )}
          </form>
        </div>
      </div>
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
        <h3 className="text-lg font-medium text-gray-900 dark:text-white">
          Experiment Status
        </h3>
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
        <div className="mt-4">
          <div className="flex justify-between text-sm">
            <span className="text-gray-500 dark:text-gray-400">Progress</span>
            <span className="text-gray-900 dark:text-white">
              {Math.round((experiment.progress.current_iteration / experiment.progress.total_iterations) * 100)}%
            </span>
          </div>
          <div className="mt-1 w-full bg-gray-200 rounded-full h-2 dark:bg-gray-700">
            <div
              className="bg-indigo-600 h-2 rounded-full transition-all duration-300"
              style={{
                width: `${(experiment.progress.current_iteration / experiment.progress.total_iterations) * 100}%`
              }}
            />
          </div>
        </div>
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