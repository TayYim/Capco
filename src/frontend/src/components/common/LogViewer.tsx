import React, { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import clsx from 'clsx'
import { 
  ChevronDownIcon, 
  ChevronUpIcon,
  DocumentTextIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  InformationCircleIcon,
  XCircleIcon
} from '@heroicons/react/24/outline'

interface LogEntry {
  message: string
  level: string
  timestamp?: string
}

interface LogViewerProps {
  experimentId: string
  isRunning: boolean
  experimentStatus?: string
}

export function LogViewer({ experimentId, isRunning, experimentStatus }: LogViewerProps) {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [isExpanded, setIsExpanded] = useState(true)
  const [isConnected, setIsConnected] = useState(false)
  const [autoScroll, setAutoScroll] = useState(true)
  const logsContainerRef = useRef<HTMLDivElement>(null)
  const websocketRef = useRef<WebSocket | null>(null)

  // WebSocket connection management
  useEffect(() => {
    if (!experimentId) return

    // Connect to WebSocket for real-time logs
    const connectWebSocket = () => {
      try {
        const wsUrl = `ws://localhost:8089/ws/console/${experimentId}`
        const ws = new WebSocket(wsUrl)
        websocketRef.current = ws

        ws.onopen = () => {
          console.log('WebSocket connected for experiment logs')
          setIsConnected(true)
        }

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            
            if (data.type === 'log') {
              const newLog: LogEntry = {
                message: data.message,
                level: data.level || 'INFO',
                timestamp: new Date().toISOString()
              }
              
              setLogs(prev => [...prev, newLog])
            }
          } catch (error) {
            console.error('Error parsing WebSocket message:', error)
          }
        }

        ws.onclose = () => {
          console.log('WebSocket disconnected')
          setIsConnected(false)
          // Only try to reconnect if experiment is still running
          if (isRunning) {
            setTimeout(connectWebSocket, 5000)
          }
        }

        ws.onerror = (error) => {
          console.error('WebSocket error:', error)
          setIsConnected(false)
        }
      } catch (error) {
        console.error('Failed to connect WebSocket:', error)
        setIsConnected(false)
      }
    }

    // Only connect to WebSocket for running experiments
    if (isRunning) {
      connectWebSocket()
    }

    // Cleanup on unmount
    return () => {
      if (websocketRef.current) {
        websocketRef.current.close()
        websocketRef.current = null
      }
    }
  }, [experimentId, isRunning])

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && logsContainerRef.current) {
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight
    }
  }, [logs, autoScroll])

  // Handle manual scroll to detect if user scrolled up
  const handleScroll = () => {
    if (logsContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = logsContainerRef.current
      const isAtBottom = scrollTop + clientHeight >= scrollHeight - 10
      setAutoScroll(isAtBottom)
    }
  }

  // Fetch initial logs from API
  useEffect(() => {
    const fetchInitialLogs = async () => {
      try {
        const response = await fetch(`http://localhost:8089/api/experiments/${experimentId}/logs?lines=100`)
        if (response.ok) {
          const data = await response.json()
          if (data.logs && Array.isArray(data.logs)) {
            setLogs(data.logs)
          }
        }
      } catch (error) {
        console.error('Failed to fetch initial logs:', error)
      }
    }

    if (experimentId && logs.length === 0) {
      fetchInitialLogs()
    }
  }, [experimentId])

  const getLogLevelIcon = (level: string) => {
    switch (level.toUpperCase()) {
      case 'ERROR':
        return <XCircleIcon className="h-4 w-4 text-red-500" />
      case 'WARNING':
        return <ExclamationTriangleIcon className="h-4 w-4 text-yellow-500" />
      case 'SUCCESS':
        return <CheckCircleIcon className="h-4 w-4 text-green-500" />
      case 'INFO':
        return <InformationCircleIcon className="h-4 w-4 text-blue-500" />
      default:
        return <DocumentTextIcon className="h-4 w-4 text-gray-500" />
    }
  }

  const getLogLevelColor = (level: string) => {
    switch (level.toUpperCase()) {
      case 'ERROR':
        return 'text-red-600 dark:text-red-400'
      case 'WARNING':
        return 'text-yellow-600 dark:text-yellow-400'
      case 'SUCCESS':
        return 'text-green-600 dark:text-green-400'
      case 'INFO':
        return 'text-blue-600 dark:text-blue-400'
      default:
        return 'text-gray-600 dark:text-gray-400'
    }
  }

  // Only show the log viewer if the experiment has been started or has logs
  if (!isRunning && logs.length === 0 && experimentStatus === 'created') {
    return null // Don't show component for brand new experiments
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white dark:bg-gray-800 shadow rounded-lg overflow-hidden"
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <DocumentTextIcon className="h-5 w-5 text-gray-500" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">
              Experiment Logs
            </h3>
            
            {/* Connection status - only show for running experiments */}
            {isRunning && (
              <div className="flex items-center space-x-1">
                <div className={clsx(
                  'w-2 h-2 rounded-full',
                  isConnected ? 'bg-green-400' : 'bg-gray-400'
                )} />
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {isConnected ? 'Live' : 'Disconnected'}
                </span>
              </div>
            )}
          </div>

          <div className="flex items-center space-x-2">
            {logs.length > 0 && (
              <span className="text-sm text-gray-500 dark:text-gray-400">
                {logs.length} lines
              </span>
            )}
            
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              {isExpanded ? (
                <ChevronUpIcon className="h-5 w-5 text-gray-500" />
              ) : (
                <ChevronDownIcon className="h-5 w-5 text-gray-500" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Logs content */}
      {isExpanded && (
        <div className="relative">
          {logs.length === 0 ? (
            <div className="p-6 text-center text-gray-500 dark:text-gray-400">
              {isRunning ? (
                <div className="flex items-center justify-center space-x-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-indigo-600"></div>
                  <span>Waiting for logs...</span>
                </div>
              ) : experimentStatus === 'created' ? (
                <div className="flex items-center justify-center space-x-2">
                  <InformationCircleIcon className="h-5 w-5 text-gray-400" />
                  <span>Experiment not started yet - no logs available</span>
                </div>
              ) : experimentStatus === 'completed' || experimentStatus === 'failed' ? (
                <div className="flex items-center justify-center space-x-2">
                  <InformationCircleIcon className="h-5 w-5 text-gray-400" />
                  <span>Loading historical logs...</span>
                </div>
              ) : (
                'No logs available'
              )}
            </div>
          ) : (
            <div
              ref={logsContainerRef}
              onScroll={handleScroll}
              className="h-80 overflow-y-auto bg-gray-50 dark:bg-gray-900 p-4 font-mono text-sm"
            >
              <div className="space-y-1">
                {logs.map((log, index) => (
                  <div
                    key={index}
                    className="flex items-start space-x-2 py-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded px-2 -mx-2"
                  >
                    <div className="flex-shrink-0 mt-0.5">
                      {getLogLevelIcon(log.level)}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2">
                        {log.timestamp && (
                          <span className="text-xs text-gray-400 dark:text-gray-500">
                            {new Date(log.timestamp).toLocaleTimeString()}
                          </span>
                        )}
                        <span className={clsx(
                          'text-xs font-medium',
                          getLogLevelColor(log.level)
                        )}>
                          {log.level.toUpperCase()}
                        </span>
                      </div>
                      
                      <div className="text-gray-800 dark:text-gray-200 break-words">
                        {log.message}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Auto-scroll indicator */}
          {!autoScroll && (
            <div className="absolute bottom-4 right-4">
              <button
                onClick={() => {
                  setAutoScroll(true)
                  if (logsContainerRef.current) {
                    logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight
                  }
                }}
                className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs px-2 py-1 rounded shadow-lg"
              >
                Scroll to bottom
              </button>
            </div>
          )}
        </div>
      )}
    </motion.div>
  )
} 