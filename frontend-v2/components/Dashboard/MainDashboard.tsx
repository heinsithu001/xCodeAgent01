import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  CodeBracketIcon,
  DocumentTextIcon,
  BugAntIcon,
  SparklesIcon,
  BeakerIcon,
  ChatBubbleLeftRightIcon,
  FolderOpenIcon,
  CpuChipIcon,
  ChartBarIcon,
  BoltIcon,
  CloudArrowUpIcon,
  PlayIcon,
  PauseIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';

interface DashboardCard {
  id: string;
  title: string;
  description: string;
  icon: React.ComponentType<any>;
  gradient: string;
  action: string;
  stats?: {
    label: string;
    value: string;
    trend?: 'up' | 'down' | 'stable';
  };
  badge?: string;
}

interface SystemMetrics {
  vllmStatus: 'online' | 'offline' | 'starting';
  activeRequests: number;
  totalTasks: number;
  successRate: number;
  avgResponseTime: string;
  modelLoaded: boolean;
}

export const MainDashboard: React.FC = () => {
  const [selectedCard, setSelectedCard] = useState<string | null>(null);
  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics>({
    vllmStatus: 'offline',
    activeRequests: 0,
    totalTasks: 127,
    successRate: 94.2,
    avgResponseTime: '2.3s',
    modelLoaded: false
  });

  const dashboardCards: DashboardCard[] = [
    {
      id: 'code-generation',
      title: 'AI Code Generation',
      description: 'Generate high-quality code from natural language descriptions using DeepSeek R1',
      icon: CodeBracketIcon,
      gradient: 'from-blue-500 to-purple-600',
      action: 'Generate Code',
      stats: {
        label: 'Generated Today',
        value: '23',
        trend: 'up'
      },
      badge: 'AI Powered'
    },
    {
      id: 'code-review',
      title: 'Smart Code Review',
      description: 'Comprehensive code analysis with best practices, security, and performance insights',
      icon: DocumentTextIcon,
      gradient: 'from-green-500 to-teal-600',
      action: 'Review Code',
      stats: {
        label: 'Reviews Completed',
        value: '45',
        trend: 'up'
      },
      badge: 'Pro'
    },
    {
      id: 'debugging',
      title: 'Intelligent Debugging',
      description: 'AI-powered bug detection and fixing with detailed explanations and solutions',
      icon: BugAntIcon,
      gradient: 'from-red-500 to-pink-600',
      action: 'Debug Code',
      stats: {
        label: 'Bugs Fixed',
        value: '18',
        trend: 'stable'
      },
      badge: 'Smart'
    },
    {
      id: 'optimization',
      title: 'Code Optimization',
      description: 'Improve code performance, readability, and maintainability with AI suggestions',
      icon: SparklesIcon,
      gradient: 'from-yellow-500 to-orange-600',
      action: 'Optimize',
      stats: {
        label: 'Optimizations',
        value: '31',
        trend: 'up'
      }
    },
    {
      id: 'testing',
      title: 'Test Generation',
      description: 'Automatically generate comprehensive unit tests and integration tests',
      icon: BeakerIcon,
      gradient: 'from-indigo-500 to-blue-600',
      action: 'Generate Tests',
      stats: {
        label: 'Tests Created',
        value: '89',
        trend: 'up'
      },
      badge: 'Auto'
    },
    {
      id: 'chat',
      title: 'AI Assistant Chat',
      description: 'Interactive chat with DeepSeek R1 for coding help, explanations, and guidance',
      icon: ChatBubbleLeftRightIcon,
      gradient: 'from-purple-500 to-pink-600',
      action: 'Start Chat',
      stats: {
        label: 'Conversations',
        value: '156',
        trend: 'up'
      },
      badge: 'Live'
    },
    {
      id: 'project-upload',
      title: 'Project Analysis',
      description: 'Upload and analyze entire projects for insights, improvements, and documentation',
      icon: FolderOpenIcon,
      gradient: 'from-cyan-500 to-blue-600',
      action: 'Upload Project',
      stats: {
        label: 'Projects Analyzed',
        value: '12',
        trend: 'stable'
      }
    },
    {
      id: 'documentation',
      title: 'Auto Documentation',
      description: 'Generate comprehensive documentation, README files, and API docs automatically',
      icon: DocumentTextIcon,
      gradient: 'from-emerald-500 to-green-600',
      action: 'Generate Docs',
      stats: {
        label: 'Docs Generated',
        value: '67',
        trend: 'up'
      }
    }
  ];

  const quickActions = [
    {
      id: 'new-task',
      label: 'New AI Task',
      icon: PlayIcon,
      gradient: 'from-blue-500 to-purple-600'
    },
    {
      id: 'upload-files',
      label: 'Upload Files',
      icon: CloudArrowUpIcon,
      gradient: 'from-green-500 to-teal-600'
    },
    {
      id: 'start-chat',
      label: 'AI Chat',
      icon: ChatBubbleLeftRightIcon,
      gradient: 'from-purple-500 to-pink-600'
    }
  ];

  useEffect(() => {
    // Simulate real-time updates
    const interval = setInterval(() => {
      setSystemMetrics(prev => ({
        ...prev,
        activeRequests: Math.floor(Math.random() * 5),
        avgResponseTime: `${(Math.random() * 3 + 1).toFixed(1)}s`
      }));
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  const handleCardClick = (cardId: string) => {
    setSelectedCard(cardId);
    // Here you would navigate to the specific feature
    console.log(`Navigating to ${cardId}`);
  };

  const getTrendIcon = (trend?: 'up' | 'down' | 'stable') => {
    switch (trend) {
      case 'up':
        return '↗️';
      case 'down':
        return '↘️';
      default:
        return '→';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-mesh p-6">
      {/* Header Section */}
      <motion.div
        className="mb-8"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-4xl font-bold text-gradient-primary mb-2">
              Welcome to Enhanced CodeAgent
            </h1>
            <p className="text-xl text-gray-300">
              Your AI-powered development companion with production-ready vLLM infrastructure
            </p>
          </div>
          
          {/* System Status */}
          <motion.div
            className="glass-card p-4 min-w-[300px]"
            whileHover={{ scale: 1.02 }}
          >
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-lg font-semibold text-white">System Status</h3>
              <div className={`w-3 h-3 rounded-full ${
                systemMetrics.vllmStatus === 'online' ? 'bg-green-400 animate-pulse' :
                systemMetrics.vllmStatus === 'starting' ? 'bg-yellow-400 animate-pulse' :
                'bg-gray-400'
              }`} />
            </div>
            
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-gray-400">vLLM Server</p>
                <p className="text-white font-medium">
                  {systemMetrics.vllmStatus === 'online' ? 'Active' : 'Demo Mode'}
                </p>
              </div>
              <div>
                <p className="text-gray-400">Active Requests</p>
                <p className="text-white font-medium">{systemMetrics.activeRequests}</p>
              </div>
              <div>
                <p className="text-gray-400">Success Rate</p>
                <p className="text-green-400 font-medium">{systemMetrics.successRate}%</p>
              </div>
              <div>
                <p className="text-gray-400">Avg Response</p>
                <p className="text-white font-medium">{systemMetrics.avgResponseTime}</p>
              </div>
            </div>
          </motion.div>
        </div>

        {/* Quick Actions */}
        <div className="flex space-x-4 mb-8">
          {quickActions.map((action, index) => (
            <motion.button
              key={action.id}
              className={`flex items-center space-x-2 px-6 py-3 bg-gradient-to-r ${action.gradient} 
                         rounded-lg text-white font-medium shadow-lg hover:shadow-xl transition-all`}
              whileHover={{ scale: 1.05, y: -2 }}
              whileTap={{ scale: 0.95 }}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
            >
              <action.icon className="w-5 h-5" />
              <span>{action.label}</span>
            </motion.button>
          ))}
        </div>
      </motion.div>

      {/* Feature Cards Grid */}
      <motion.div
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.8, delay: 0.2 }}
      >
        {dashboardCards.map((card, index) => (
          <motion.div
            key={card.id}
            className="glass-card p-6 cursor-pointer group relative overflow-hidden"
            whileHover={{ 
              scale: 1.05, 
              y: -10,
              boxShadow: "0 25px 50px rgba(0, 0, 0, 0.3)"
            }}
            whileTap={{ scale: 0.95 }}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ 
              duration: 0.5, 
              delay: index * 0.1,
              type: "spring",
              stiffness: 100
            }}
            onClick={() => handleCardClick(card.id)}
          >
            {/* Background Gradient */}
            <div className={`absolute inset-0 bg-gradient-to-br ${card.gradient} opacity-0 
                           group-hover:opacity-10 transition-opacity duration-300`} />
            
            {/* Badge */}
            {card.badge && (
              <motion.div
                className="absolute top-4 right-4 px-2 py-1 bg-gradient-accent rounded-full"
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: index * 0.1 + 0.3 }}
              >
                <span className="text-xs font-medium text-white">{card.badge}</span>
              </motion.div>
            )}

            {/* Icon */}
            <motion.div
              className={`w-12 h-12 rounded-lg bg-gradient-to-br ${card.gradient} 
                         flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}
              whileHover={{ rotate: 5 }}
            >
              <card.icon className="w-6 h-6 text-white" />
            </motion.div>

            {/* Content */}
            <div className="relative z-10">
              <h3 className="text-lg font-semibold text-white mb-2 group-hover:text-gradient-primary transition-all">
                {card.title}
              </h3>
              
              <p className="text-gray-400 text-sm mb-4 line-clamp-2 group-hover:text-gray-300">
                {card.description}
              </p>

              {/* Stats */}
              {card.stats && (
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <p className="text-xs text-gray-500">{card.stats.label}</p>
                    <p className="text-lg font-bold text-white">{card.stats.value}</p>
                  </div>
                  <span className="text-sm">
                    {getTrendIcon(card.stats.trend)}
                  </span>
                </div>
              )}

              {/* Action Button */}
              <motion.button
                className={`w-full py-2 px-4 bg-gradient-to-r ${card.gradient} rounded-lg 
                           text-white font-medium text-sm opacity-0 group-hover:opacity-100 
                           transition-all duration-300 transform translate-y-2 group-hover:translate-y-0`}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                {card.action}
              </motion.button>
            </div>

            {/* Hover Effect */}
            <motion.div
              className="absolute inset-0 border-2 border-transparent group-hover:border-white/20 
                         rounded-lg transition-all duration-300"
            />
          </motion.div>
        ))}
      </motion.div>

      {/* Recent Activity Section */}
      <motion.div
        className="mt-12 glass-card p-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.8 }}
      >
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-white">Recent Activity</h2>
          <button className="text-accent-blue hover:text-white transition-colors">
            View All
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            {
              type: 'Code Generation',
              description: 'Generated Python data processing function',
              time: '2 minutes ago',
              status: 'completed',
              icon: CodeBracketIcon
            },
            {
              type: 'Code Review',
              description: 'Reviewed authentication module',
              time: '15 minutes ago',
              status: 'completed',
              icon: DocumentTextIcon
            },
            {
              type: 'Bug Fix',
              description: 'Fixed memory leak in data handler',
              time: '1 hour ago',
              status: 'completed',
              icon: BugAntIcon
            }
          ].map((activity, index) => (
            <motion.div
              key={index}
              className="p-4 bg-white/5 rounded-lg border border-white/10 hover:bg-white/10 transition-all"
              whileHover={{ scale: 1.02 }}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.9 + index * 0.1 }}
            >
              <div className="flex items-start space-x-3">
                <div className="w-8 h-8 rounded-lg bg-gradient-primary flex items-center justify-center">
                  <activity.icon className="w-4 h-4 text-white" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-white">{activity.type}</span>
                    <CheckCircleIcon className="w-4 h-4 text-green-400" />
                  </div>
                  <p className="text-sm text-gray-400 mb-2">{activity.description}</p>
                  <span className="text-xs text-gray-500">{activity.time}</span>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* vLLM Infrastructure Status */}
      <motion.div
        className="mt-8 glass-card p-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 1.0 }}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-bold text-white">vLLM Infrastructure</h3>
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
            <span className="text-sm text-green-400">Production Ready</span>
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="text-center p-4 bg-white/5 rounded-lg">
            <CpuChipIcon className="w-8 h-8 text-accent-blue mx-auto mb-2" />
            <p className="text-sm text-gray-400">Infrastructure</p>
            <p className="text-lg font-bold text-white">Ready</p>
          </div>
          <div className="text-center p-4 bg-white/5 rounded-lg">
            <BoltIcon className="w-8 h-8 text-yellow-400 mx-auto mb-2" />
            <p className="text-sm text-gray-400">Performance</p>
            <p className="text-lg font-bold text-white">Optimized</p>
          </div>
          <div className="text-center p-4 bg-white/5 rounded-lg">
            <ChartBarIcon className="w-8 h-8 text-green-400 mx-auto mb-2" />
            <p className="text-sm text-gray-400">Cost</p>
            <p className="text-lg font-bold text-green-400">Free</p>
          </div>
          <div className="text-center p-4 bg-white/5 rounded-lg">
            <CheckCircleIcon className="w-8 h-8 text-purple-400 mx-auto mb-2" />
            <p className="text-sm text-gray-400">Status</p>
            <p className="text-lg font-bold text-white">Demo Mode</p>
          </div>
        </div>
        
        <div className="mt-4 p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
          <p className="text-sm text-blue-300">
            <strong>Production Ready:</strong> Complete vLLM infrastructure implemented. 
            Switch to production mode anytime by starting the vLLM server with actual DeepSeek R1 model.
          </p>
        </div>
      </motion.div>
    </div>
  );
};