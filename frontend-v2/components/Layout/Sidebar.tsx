import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  CodeBracketIcon,
  DocumentTextIcon,
  BugAntIcon,
  SparklesIcon,
  BeakerIcon,
  FolderIcon,
  ChatBubbleLeftRightIcon,
  CpuChipIcon,
  ChartBarIcon,
  Cog6ToothIcon,
  PlusIcon,
  ChevronRightIcon,
  PlayIcon,
  PauseIcon,
  StopIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';

interface SidebarProps {
  isOpen: boolean;
  onClose?: () => void;
}

interface FeatureItem {
  id: string;
  name: string;
  icon: React.ComponentType<any>;
  description: string;
  category: 'code' | 'analysis' | 'tools' | 'workspace';
  badge?: string;
  active?: boolean;
}

interface TaskItem {
  id: string;
  type: string;
  description: string;
  status: 'running' | 'completed' | 'failed' | 'queued';
  progress?: number;
  timestamp: string;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const [activeTab, setActiveTab] = useState<'features' | 'tasks' | 'workspace'>('features');
  const [expandedCategories, setExpandedCategories] = useState<string[]>(['code']);

  const features: FeatureItem[] = [
    {
      id: 'code-generation',
      name: 'Code Generation',
      icon: CodeBracketIcon,
      description: 'Generate code from natural language',
      category: 'code',
      badge: 'AI',
      active: true
    },
    {
      id: 'code-review',
      name: 'Code Review',
      icon: DocumentTextIcon,
      description: 'Analyze and review code quality',
      category: 'analysis',
      badge: 'Pro'
    },
    {
      id: 'debugging',
      name: 'Smart Debugging',
      icon: BugAntIcon,
      description: 'Find and fix code issues',
      category: 'analysis',
      badge: 'AI'
    },
    {
      id: 'optimization',
      name: 'Code Optimization',
      icon: SparklesIcon,
      description: 'Improve code performance',
      category: 'analysis'
    },
    {
      id: 'testing',
      name: 'Test Generation',
      icon: BeakerIcon,
      description: 'Generate comprehensive tests',
      category: 'code',
      badge: 'Auto'
    },
    {
      id: 'documentation',
      name: 'Documentation',
      icon: DocumentTextIcon,
      description: 'Generate docs and comments',
      category: 'code'
    },
    {
      id: 'file-explorer',
      name: 'File Explorer',
      icon: FolderIcon,
      description: 'Browse and manage files',
      category: 'workspace'
    },
    {
      id: 'ai-chat',
      name: 'AI Assistant',
      icon: ChatBubbleLeftRightIcon,
      description: 'Chat with DeepSeek R1',
      category: 'tools',
      badge: 'Live'
    },
    {
      id: 'system-monitor',
      name: 'System Monitor',
      icon: CpuChipIcon,
      description: 'Monitor system performance',
      category: 'tools'
    },
    {
      id: 'analytics',
      name: 'Analytics',
      icon: ChartBarIcon,
      description: 'View usage analytics',
      category: 'tools'
    }
  ];

  const [recentTasks] = useState<TaskItem[]>([
    {
      id: '1',
      type: 'Code Generation',
      description: 'Generate Python function for data processing',
      status: 'completed',
      timestamp: '2 minutes ago'
    },
    {
      id: '2',
      type: 'Code Review',
      description: 'Review authentication module',
      status: 'running',
      progress: 65,
      timestamp: '5 minutes ago'
    },
    {
      id: '3',
      type: 'Documentation',
      description: 'Generate API documentation',
      status: 'queued',
      timestamp: '10 minutes ago'
    }
  ]);

  const toggleCategory = (category: string) => {
    setExpandedCategories(prev => 
      prev.includes(category) 
        ? prev.filter(c => c !== category)
        : [...prev, category]
    );
  };

  const getFeaturesByCategory = (category: string) => {
    return features.filter(feature => feature.category === category);
  };

  const getStatusIcon = (status: TaskItem['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon className="w-4 h-4 text-green-400" />;
      case 'running':
        return <PlayIcon className="w-4 h-4 text-blue-400 animate-pulse" />;
      case 'failed':
        return <ExclamationTriangleIcon className="w-4 h-4 text-red-400" />;
      case 'queued':
        return <ClockIcon className="w-4 h-4 text-yellow-400" />;
      default:
        return null;
    }
  };

  const categories = [
    { id: 'code', name: 'Code Tools', icon: CodeBracketIcon },
    { id: 'analysis', name: 'Analysis', icon: SparklesIcon },
    { id: 'workspace', name: 'Workspace', icon: FolderIcon },
    { id: 'tools', name: 'Tools', icon: Cog6ToothIcon }
  ];

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Mobile Overlay */}
          <motion.div
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 lg:hidden"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />

          {/* Sidebar */}
          <motion.aside
            className="fixed left-0 top-16 bottom-0 w-80 glass-card border-r border-white/10 z-50 lg:z-30"
            initial={{ x: -320, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -320, opacity: 0 }}
            transition={{ duration: 0.3, ease: "easeOut" }}
          >
            <div className="flex flex-col h-full">
              {/* Header Tabs */}
              <div className="flex border-b border-white/10">
                {[
                  { id: 'features', label: 'Features' },
                  { id: 'tasks', label: 'Tasks' },
                  { id: 'workspace', label: 'Files' }
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as any)}
                    className={`flex-1 px-4 py-3 text-sm font-medium transition-all ${
                      activeTab === tab.id
                        ? 'text-white border-b-2 border-accent-blue bg-white/5'
                        : 'text-gray-400 hover:text-white hover:bg-white/5'
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Content */}
              <div className="flex-1 overflow-y-auto p-4">
                {activeTab === 'features' && (
                  <div className="space-y-4">
                    {/* Quick Actions */}
                    <div className="mb-6">
                      <motion.button
                        className="w-full btn-gradient-primary text-white font-medium py-3 px-4 rounded-lg 
                                 flex items-center justify-center space-x-2"
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                      >
                        <PlusIcon className="w-5 h-5" />
                        <span>New AI Task</span>
                      </motion.button>
                    </div>

                    {/* Feature Categories */}
                    {categories.map((category) => (
                      <div key={category.id} className="mb-4">
                        <motion.button
                          onClick={() => toggleCategory(category.id)}
                          className="w-full flex items-center justify-between p-3 rounded-lg 
                                   hover:bg-white/5 transition-colors group"
                          whileHover={{ scale: 1.01 }}
                        >
                          <div className="flex items-center space-x-3">
                            <category.icon className="w-5 h-5 text-accent-blue" />
                            <span className="font-medium text-white">{category.name}</span>
                          </div>
                          <motion.div
                            animate={{ 
                              rotate: expandedCategories.includes(category.id) ? 90 : 0 
                            }}
                            transition={{ duration: 0.2 }}
                          >
                            <ChevronRightIcon className="w-4 h-4 text-gray-400 group-hover:text-white" />
                          </motion.div>
                        </motion.button>

                        <AnimatePresence>
                          {expandedCategories.includes(category.id) && (
                            <motion.div
                              initial={{ height: 0, opacity: 0 }}
                              animate={{ height: 'auto', opacity: 1 }}
                              exit={{ height: 0, opacity: 0 }}
                              transition={{ duration: 0.2 }}
                              className="ml-8 mt-2 space-y-1"
                            >
                              {getFeaturesByCategory(category.id).map((feature) => (
                                <motion.button
                                  key={feature.id}
                                  className={`w-full text-left p-3 rounded-lg transition-all group ${
                                    feature.active 
                                      ? 'bg-gradient-primary/20 border border-accent-blue/30' 
                                      : 'hover:bg-white/5'
                                  }`}
                                  whileHover={{ scale: 1.01, x: 4 }}
                                  whileTap={{ scale: 0.99 }}
                                >
                                  <div className="flex items-center justify-between mb-1">
                                    <div className="flex items-center space-x-2">
                                      <feature.icon className="w-4 h-4 text-accent-blue" />
                                      <span className="text-sm font-medium text-white">
                                        {feature.name}
                                      </span>
                                    </div>
                                    {feature.badge && (
                                      <span className="px-2 py-0.5 text-xs font-medium bg-gradient-accent 
                                                     text-white rounded-full">
                                        {feature.badge}
                                      </span>
                                    )}
                                  </div>
                                  <p className="text-xs text-gray-400 group-hover:text-gray-300">
                                    {feature.description}
                                  </p>
                                </motion.button>
                              ))}
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                    ))}
                  </div>
                )}

                {activeTab === 'tasks' && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold text-white">Recent Tasks</h3>
                      <span className="text-sm text-gray-400">{recentTasks.length} tasks</span>
                    </div>

                    {recentTasks.map((task) => (
                      <motion.div
                        key={task.id}
                        className="p-4 bg-white/5 rounded-lg border border-white/10 hover:bg-white/10 
                                 transition-all cursor-pointer"
                        whileHover={{ scale: 1.02, y: -2 }}
                        whileTap={{ scale: 0.98 }}
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center space-x-2">
                            {getStatusIcon(task.status)}
                            <span className="text-sm font-medium text-white">{task.type}</span>
                          </div>
                          <span className="text-xs text-gray-400">{task.timestamp}</span>
                        </div>
                        
                        <p className="text-sm text-gray-300 mb-2">{task.description}</p>
                        
                        {task.status === 'running' && task.progress && (
                          <div className="w-full bg-gray-700 rounded-full h-2">
                            <motion.div
                              className="bg-gradient-primary h-2 rounded-full"
                              initial={{ width: 0 }}
                              animate={{ width: `${task.progress}%` }}
                              transition={{ duration: 0.5 }}
                            />
                          </div>
                        )}
                        
                        <div className="flex items-center justify-between mt-2">
                          <span className={`text-xs px-2 py-1 rounded-full ${
                            task.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                            task.status === 'running' ? 'bg-blue-500/20 text-blue-400' :
                            task.status === 'failed' ? 'bg-red-500/20 text-red-400' :
                            'bg-yellow-500/20 text-yellow-400'
                          }`}>
                            {task.status.charAt(0).toUpperCase() + task.status.slice(1)}
                          </span>
                          
                          {task.status === 'running' && (
                            <button className="text-xs text-gray-400 hover:text-white transition-colors">
                              <PauseIcon className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      </motion.div>
                    ))}

                    {recentTasks.length === 0 && (
                      <div className="text-center py-8">
                        <ClockIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                        <p className="text-gray-400">No recent tasks</p>
                        <p className="text-sm text-gray-500 mt-1">
                          Start by creating a new AI task
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {activeTab === 'workspace' && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold text-white">Project Files</h3>
                      <button className="p-2 hover:bg-white/10 rounded-lg transition-colors">
                        <PlusIcon className="w-4 h-4 text-gray-400" />
                      </button>
                    </div>

                    {/* File Tree Placeholder */}
                    <div className="space-y-2">
                      {[
                        { name: 'src/', type: 'folder', expanded: true },
                        { name: 'components/', type: 'folder', level: 1 },
                        { name: 'Layout.tsx', type: 'file', level: 2 },
                        { name: 'Sidebar.tsx', type: 'file', level: 2 },
                        { name: 'utils/', type: 'folder', level: 1 },
                        { name: 'package.json', type: 'file' },
                        { name: 'README.md', type: 'file' }
                      ].map((item, index) => (
                        <motion.div
                          key={index}
                          className={`flex items-center space-x-2 p-2 rounded hover:bg-white/5 
                                   transition-colors cursor-pointer ${
                                     item.level ? `ml-${item.level * 4}` : ''
                                   }`}
                          whileHover={{ x: 2 }}
                        >
                          <FolderIcon className={`w-4 h-4 ${
                            item.type === 'folder' ? 'text-blue-400' : 'text-gray-400'
                          }`} />
                          <span className="text-sm text-white">{item.name}</span>
                        </motion.div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Footer */}
              <div className="border-t border-white/10 p-4">
                <div className="flex items-center justify-between text-xs text-gray-400">
                  <span>vLLM Infrastructure Ready</span>
                  <span className="text-green-400">● Online</span>
                </div>
              </div>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
};