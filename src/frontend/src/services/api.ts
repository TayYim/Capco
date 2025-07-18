import axios, { AxiosInstance, AxiosError } from 'axios'
import toast from 'react-hot-toast'
import type { 
  ExperimentData, 
  ExperimentConfig, 
  ExperimentResult,
  ExperimentListItem,
  RouteInfo,
  RouteFileInfo,
  ScenarioStatistics,
  SystemConfiguration,
  ConfigurationStatus,
  ParameterRange,
  SystemInfo,
  FileInfo,
  ExperimentAnalysis 
} from '@/types'

// Environment configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8089'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        // Add authentication token if available
        const token = localStorage.getItem('auth_token')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        this.handleApiError(error)
        return Promise.reject(error)
      }
    )
  }

  private handleApiError(error: AxiosError) {
    if (error.response) {
      const status = error.response.status
      const data = error.response.data as any

      switch (status) {
        case 400:
          toast.error(data.detail || 'Bad request')
          break
        case 401:
          toast.error('Unauthorized - please log in')
          // Handle token expiration
          localStorage.removeItem('auth_token')
          break
        case 403:
          toast.error('Forbidden - insufficient permissions')
          break
        case 404:
          toast.error(data.detail || 'Resource not found')
          break
        case 500:
          toast.error('Server error - please try again later')
          break
        default:
          toast.error(data.detail || 'An unexpected error occurred')
      }
    } else if (error.request) {
      toast.error('Network error - please check your connection')
    }
  }

  // Experiments API
  async createExperiment(config: ExperimentConfig, startImmediately = false): Promise<ExperimentData> {
    const response = await this.client.post('/api/experiments', {
      config,
      start_immediately: startImmediately,
    })
    return response.data
  }

  async listExperiments(params?: {
    limit?: number
    offset?: number
    status_filter?: string
    search_method?: string
  }): Promise<ExperimentListItem[]> {
    const response = await this.client.get('/api/experiments', { params })
    return response.data
  }

  async getExperiment(id: string): Promise<ExperimentData> {
    const response = await this.client.get(`/api/experiments/${id}`)
    return response.data
  }

  async startExperiment(id: string): Promise<ExperimentData> {
    const response = await this.client.post(`/api/experiments/${id}/start`)
    return response.data
  }

  async stopExperiment(id: string): Promise<ExperimentData> {
    const response = await this.client.post(`/api/experiments/${id}/stop`)
    return response.data
  }

  async getExperimentResults(id: string): Promise<ExperimentResult> {
    const response = await this.client.get(`/api/experiments/${id}/results`)
    return response.data
  }

  async deleteExperiment(id: string): Promise<void> {
    await this.client.delete(`/api/experiments/${id}`)
  }

  async downloadExperimentFile(id: string, filename: string): Promise<Blob> {
    const response = await this.client.get(`/api/experiments/${id}/download/${filename}`, {
      responseType: 'blob',
    })
    return response.data
  }

  // Scenarios API
  async listRouteFiles(): Promise<RouteFileInfo[]> {
    const response = await this.client.get('/api/scenarios/files')
    return response.data
  }

  async listRoutes(routeFile: string): Promise<any[]> {
    const response = await this.client.get(`/api/scenarios/${routeFile}`)
    return response.data
  }

  async getRouteInfo(routeFile: string, routeId: string): Promise<RouteInfo> {
    const response = await this.client.get(`/api/scenarios/${routeFile}/${routeId}`)
    return response.data
  }

  async getScenarioStatistics(routeFile?: string): Promise<ScenarioStatistics> {
    const params = routeFile ? { route_file: routeFile } : {}
    const response = await this.client.get('/api/scenarios/statistics', { params })
    return response.data
  }

  async getScenarioTypes(): Promise<string[]> {
    const response = await this.client.get('/api/scenarios/types')
    return response.data
  }

  async getAvailableTowns(): Promise<string[]> {
    const response = await this.client.get('/api/scenarios/towns')
    return response.data
  }

  // Configuration API
  async getSystemConfiguration(): Promise<SystemConfiguration> {
    const response = await this.client.get('/api/config')
    return response.data
  }

  async updateSystemConfiguration(update: any): Promise<SystemConfiguration> {
    const response = await this.client.put('/api/config', update)
    return response.data
  }

  async getConfigurationStatus(): Promise<ConfigurationStatus> {
    const response = await this.client.get('/api/config/status')
    return response.data
  }

  async getParameterRanges(scenarioType?: string): Promise<ParameterRange[]> {
    const params = scenarioType ? { scenario_type: scenarioType } : {}
    const response = await this.client.get('/api/config/parameters', { params })
    return response.data
  }

  async updateParameterRanges(update: any): Promise<ParameterRange[]> {
    const response = await this.client.put('/api/config/parameters', update)
    return response.data
  }

  async getSystemInfo(): Promise<SystemInfo> {
    const response = await this.client.get('/api/config/info')
    return response.data
  }

  // Results API
  async listExperimentFiles(experimentId: string): Promise<FileInfo[]> {
    const response = await this.client.get(`/api/results/files/${experimentId}`)
    return response.data
  }

  async downloadFile(experimentId: string, filename: string): Promise<Blob> {
    const response = await this.client.get(`/api/results/download/${experimentId}/${filename}`, {
      responseType: 'blob',
    })
    return response.data
  }

  async downloadExperimentArchive(experimentId: string, format = 'zip'): Promise<Blob> {
    const response = await this.client.get(`/api/results/download-archive/${experimentId}`, {
      params: { format },
      responseType: 'blob',
    })
    return response.data
  }

  async previewFile(experimentId: string, filename: string, maxLines = 100): Promise<any> {
    const response = await this.client.get(`/api/results/preview/${experimentId}/${filename}`, {
      params: { max_lines: maxLines },
    })
    return response.data
  }

  async getExperimentAnalysis(experimentId: string): Promise<ExperimentAnalysis> {
    const response = await this.client.get(`/api/results/analysis/${experimentId}`)
    return response.data
  }

  // Health check
  async healthCheck(): Promise<{ status: string; version: string }> {
    const response = await this.client.get('/health')
    return response.data
  }
}

// Create singleton instance
export const apiClient = new ApiClient()

// Export for use in React Query
export default apiClient 