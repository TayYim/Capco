// Re-export all types from individual modules
export * from './experiment'
export * from './scenario'
export * from './api'

// Common utility types
export interface ApiResponse<T = any> {
  data?: T
  message?: string
  errors?: string[]
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  hasNext: boolean
  hasPrevious: boolean
}

export interface SelectOption {
  label: string
  value: string
  disabled?: boolean
}

export interface TableColumn<T = any> {
  key: string
  title: string
  sortable?: boolean
  render?: (value: any, record: T) => React.ReactNode
}

export interface FormFieldProps {
  label?: string
  error?: string
  required?: boolean
  disabled?: boolean
  helpText?: string
} 