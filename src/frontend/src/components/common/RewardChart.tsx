import { useEffect, useRef } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ChartOptions,
  ChartData
} from 'chart.js'
import { Line } from 'react-chartjs-2'
import { RewardDataPoint } from '@/types/experiment'
import clsx from 'clsx'

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
)

interface RewardChartProps {
  rewardHistory: RewardDataPoint[]
  className?: string
  height?: number
  title?: string
  isRunning?: boolean
}

export function RewardChart({ 
  rewardHistory, 
  className, 
  height = 300, 
  title = "Reward Progress",
  isRunning = false 
}: RewardChartProps) {
  const chartRef = useRef<ChartJS<'line', number[], string>>(null)

  // Prepare chart data
  const chartData: ChartData<'line', number[], string> = {
    labels: rewardHistory.map(point => point.scenario_number.toString()),
    datasets: [
      {
        label: 'Reward',
        data: rewardHistory.map(point => point.reward),
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        borderWidth: 2,
        pointRadius: 3,
        pointHoverRadius: 5,
        pointBackgroundColor: 'rgb(59, 130, 246)',
        pointBorderColor: '#ffffff',
        pointBorderWidth: 1,
        tension: 0.1,
        fill: true
      }
    ]
  }

  // Chart configuration
  const chartOptions: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
        labels: {
          font: {
            size: 12
          }
        }
      },
      title: {
        display: true,
        text: title,
        font: {
          size: 14,
          weight: 'bold'
        }
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        callbacks: {
          title: (context) => {
            const dataPoint = rewardHistory[context[0].dataIndex]
            return `Scenario ${dataPoint.scenario_number} (Iteration ${dataPoint.iteration})`
          },
          label: (context) => {
            return `Reward: ${context.parsed.y.toFixed(4)}`
          },
          afterLabel: (context) => {
            const dataPoint = rewardHistory[context.dataIndex]
            if (dataPoint.timestamp) {
              const date = new Date(dataPoint.timestamp)
              return `Time: ${date.toLocaleTimeString()}`
            }
            return undefined
          }
        }
      }
    },
    scales: {
      x: {
        display: true,
        title: {
          display: true,
          text: 'Scenario Number',
          font: {
            size: 12,
            weight: 'bold'
          }
        },
        grid: {
          display: true,
          color: 'rgba(0, 0, 0, 0.1)'
        }
      },
      y: {
        display: true,
        title: {
          display: true,
          text: 'Reward Value',
          font: {
            size: 12,
            weight: 'bold'
          }
        },
        grid: {
          display: true,
          color: 'rgba(0, 0, 0, 0.1)'
        },
        beginAtZero: false
      }
    },
    interaction: {
      mode: 'nearest',
      axis: 'x',
      intersect: false
    },
    elements: {
      point: {
        hoverRadius: 8
      }
    },
    animation: {
      duration: isRunning ? 500 : 0,
      easing: 'easeInOutQuart'
    }
  }

  // Auto-scroll to latest data point when new data arrives
  useEffect(() => {
    if (chartRef.current && rewardHistory.length > 0 && isRunning) {
      const chart = chartRef.current
      const chartArea = chart.chartArea
      const meta = chart.getDatasetMeta(0)
      
      if (meta && meta.data.length > 0) {
        const lastPoint = meta.data[meta.data.length - 1]
        if (lastPoint && chartArea) {
          // Scroll to show the latest point
          const maxVisible = Math.floor(chartArea.width / 50) // Approximate points that fit
          if (rewardHistory.length > maxVisible) {
            const startIndex = Math.max(0, rewardHistory.length - maxVisible)
            chart.options.scales!.x!.min = rewardHistory[startIndex].scenario_number.toString()
            chart.options.scales!.x!.max = rewardHistory[rewardHistory.length - 1].scenario_number.toString()
            chart.update('none')
          }
        }
      }
    }
  }, [rewardHistory, isRunning])

  // Show empty state if no data
  if (rewardHistory.length === 0) {
    return (
      <div className={clsx('bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700', className)}>
        <div className="p-6">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">{title}</h3>
          <div 
            className="flex items-center justify-center border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg"
            style={{ height: `${height}px` }}
          >
            <div className="text-center">
              <div className="text-gray-400 dark:text-gray-500 mb-2">
                <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {isRunning ? 'Waiting for reward data...' : 'No reward data available'}
              </p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Calculate statistics for display
  const statistics = {
    count: rewardHistory.length,
    bestReward: Math.min(...rewardHistory.map(p => p.reward)),
    worstReward: Math.max(...rewardHistory.map(p => p.reward)),
    averageReward: rewardHistory.reduce((sum, p) => sum + p.reward, 0) / rewardHistory.length,
    latestReward: rewardHistory[rewardHistory.length - 1]?.reward
  }

  return (
    <div className={clsx('bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700', className)}>
      <div className="p-6">
        {/* Header with statistics */}
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">{title}</h3>
          {isRunning && (
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-sm text-green-600 dark:text-green-400">Live</span>
            </div>
          )}
        </div>
        
        {/* Statistics summary */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6 text-sm">
          <div className="text-center">
            <div className="text-gray-500 dark:text-gray-400">Scenarios</div>
            <div className="font-semibold text-gray-900 dark:text-white">{statistics.count}</div>
          </div>
          <div className="text-center">
            <div className="text-gray-500 dark:text-gray-400">Best</div>
            <div className="font-semibold text-green-600 dark:text-green-400">{statistics.bestReward.toFixed(3)}</div>
          </div>
          <div className="text-center">
            <div className="text-gray-500 dark:text-gray-400">Worst</div>
            <div className="font-semibold text-red-600 dark:text-red-400">{statistics.worstReward.toFixed(3)}</div>
          </div>
          <div className="text-center">
            <div className="text-gray-500 dark:text-gray-400">Average</div>
            <div className="font-semibold text-gray-900 dark:text-white">{statistics.averageReward.toFixed(3)}</div>
          </div>
          <div className="text-center">
            <div className="text-gray-500 dark:text-gray-400">Latest</div>
            <div className="font-semibold text-blue-600 dark:text-blue-400">{statistics.latestReward?.toFixed(3) || 'N/A'}</div>
          </div>
        </div>

        {/* Chart */}
        <div style={{ height: `${height}px` }}>
          <Line ref={chartRef} data={chartData} options={chartOptions} />
        </div>
      </div>
    </div>
  )
} 