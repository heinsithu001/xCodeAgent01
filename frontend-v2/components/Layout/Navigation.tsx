import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  CodeBracketIcon, 
  CpuChipIcon, 
  BoltIcon, 
  Cog6ToothIcon,
  UserCircleIcon,
  BellIcon,
  MagnifyingGlassIcon,
  ChevronDownIcon,
  PlayIcon,
  PauseIcon,
  StopIcon
} from '@heroicons/react/24/outline';

interface NavigationProps {
  onToggleSidebar?: () => void;
  sidebarOpen?: boolean;
}

export const Navigation: React.FC<NavigationProps> = ({ 
  onToggleSidebar, 
  sidebarOpen = true 
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [showSearch, setShowSearch] = useState(false);
  const [vllmStatus, setVllmStatus] = useState({
    running: false,
    model: 'demo-mode-vllm-ready',
    cost: 'free'
  });

  const handleVLLMToggle = async () => {
    try {
      const endpoint = vllmStatus.running ? '/api/v2/vllm/stop' : '/api/v2/vllm/start';
      const response = await fetch(endpoint, { method: 'POST' });
      const result = await response.json();
      
      setVllmStatus(prev => ({
        ...prev,
        running: !prev.running,
        model: result.demo_mode ? 'demo-mode-vllm-ready' : 'deepseek-ai/DeepSeek-R1-0528'
      }));
    } catch (error) {
      console.error('Failed to toggle vLLM server:', error);
    }
  };

  return (
    <motion.nav 
      className="glass-card fixed top-0 left-0 right-0 z-50 border-b border-white/10"
      initial={{ y: -100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
    >
      <div className="flex items-center justify-between px-6 py-4">
        {/* Left Section - Logo & Brand */}
        <div className="flex items-center space-x-4">
          <motion.button
            onClick={onToggleSidebar}
            className="p-2 rounded-lg hover:bg-white/10 transition-colors lg:hidden"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <div className="w-6 h-6 flex flex-col justify-center space-y-1">
              <motion.div 
                className="w-full h-0.5 bg-white rounded"
                animate={{ 
                  rotate: sidebarOpen ? 45 : 0,
                  y: sidebarOpen ? 6 : 0 
                }}
              />
              <motion.div 
                className="w-full h-0.5 bg-white rounded"
                animate={{ opacity: sidebarOpen ? 0 : 1 }}
              />
              <motion.div 
                className="w-full h-0.5 bg-white rounded"
                animate={{ 
                  rotate: sidebarOpen ? -45 : 0,
                  y: sidebarOpen ? -6 : 0 
                }}
              />
            </div>
          </motion.button>

          <motion.div 
            className="flex items-center space-x-3"
            whileHover={{ scale: 1.02 }}
          >
            <div className="relative">
              <div className="w-10 h-10 rounded-xl bg-gradient-primary flex items-center justify-center shadow-lg">
                <CpuChipIcon className="w-6 h-6 text-white" />
              </div>
              <motion.div 
                className="absolute -top-1 -right-1 w-4 h-4 bg-gradient-success rounded-full"
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
              />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gradient-primary">
                Enhanced CodeAgent
              </h1>
              <p className="text-xs text-gray-400">
                v2.0 Production Ready
              </p>
            </div>
          </motion.div>
        </div>

        {/* Center Section - Search */}
        <div className="hidden md:flex flex-1 max-w-md mx-8">
          <div className="relative w-full">
            <motion.div
              className="relative"
              animate={{ width: showSearch ? '100%' : '300px' }}
              transition={{ duration: 0.3 }}
            >
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search commands, files, or ask AI..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onFocus={() => setShowSearch(true)}
                onBlur={() => setShowSearch(false)}
                className="w-full pl-10 pr-4 py-2 bg-white/5 border border-white/10 rounded-lg 
                         text-white placeholder-gray-400 focus:outline-none focus:border-accent-blue/50 
                         focus:bg-white/10 transition-all duration-300"
              />
            </motion.div>
          </div>
        </div>

        {/* Right Section - Status & Controls */}
        <div className="flex items-center space-x-4">
          {/* vLLM Server Status & Control */}
          <div className="hidden lg:flex items-center space-x-3 px-4 py-2 bg-white/5 rounded-lg border border-white/10">
            <div className={`w-3 h-3 rounded-full ${vllmStatus.running ? 'bg-green-400 animate-pulse' : 'bg-gray-400'}`} />
            <div className="text-sm">
              <p className="text-white font-medium">
                {vllmStatus.running ? 'DeepSeek R1 Active' : 'Demo Mode'}
              </p>
              <p className="text-gray-400 text-xs">
                {vllmStatus.model}
              </p>
            </div>
            <button
              onClick={handleVLLMToggle}
              className={`ml-2 px-3 py-1 rounded text-xs font-medium transition-all ${
                vllmStatus.running 
                  ? 'bg-red-500 hover:bg-red-600 text-white' 
                  : 'bg-green-500 hover:bg-green-600 text-white'
              }`}
            >
              {vllmStatus.running ? (
                <>
                  <StopIcon className="w-3 h-3 mr-1 inline" />
                  Stop
                </>
              ) : (
                <>
                  <PlayIcon className="w-3 h-3 mr-1 inline" />
                  Start vLLM
                </>
              )}
            </button>
          </div>

          {/* System Performance Indicator */}
          <motion.div 
            className="hidden md:flex items-center space-x-2 px-3 py-2 bg-white/5 rounded-lg border border-white/10"
            whileHover={{ scale: 1.02 }}
          >
            <BoltIcon className="w-4 h-4 text-accent-blue" />
            <div className="text-xs">
              <p className="text-white font-medium">Production Ready</p>
              <p className="text-gray-400">Cost: Free</p>
            </div>
          </motion.div>

          {/* Notifications */}
          <motion.button
            className="relative p-2 rounded-lg hover:bg-white/10 transition-colors"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <BellIcon className="w-6 h-6 text-gray-300" />
            <motion.div 
              className="absolute -top-1 -right-1 w-3 h-3 bg-gradient-danger rounded-full"
              animate={{ scale: [1, 1.2, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
            />
          </motion.button>

          {/* User Menu */}
          <motion.button
            className="flex items-center space-x-2 p-2 rounded-lg hover:bg-white/10 transition-colors"
            whileHover={{ scale: 1.02 }}
          >
            <div className="w-8 h-8 rounded-full bg-gradient-accent flex items-center justify-center">
              <UserCircleIcon className="w-5 h-5 text-white" />
            </div>
            <ChevronDownIcon className="w-4 h-4 text-gray-400" />
          </motion.button>
        </div>
      </div>

      {/* Mobile Search */}
      <AnimatePresence>
        {showSearch && (
          <motion.div
            className="md:hidden px-6 pb-4"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
          >
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search or ask AI..."
                className="w-full pl-10 pr-4 py-2 bg-white/5 border border-white/10 rounded-lg 
                         text-white placeholder-gray-400 focus:outline-none focus:border-accent-blue/50"
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.nav>
  );
};