import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { LayoutDashboard, Bot, Terminal, BarChart3, Settings, ShieldAlert } from 'lucide-react';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState('dashboard');

  const tabs = [
    { id: 'dashboard', icon: <LayoutDashboard size={20} />, label: 'Dashboard' },
    { id: 'bots', icon: <Bot size={20} />, label: 'Bots' },
    { id: 'terminal', icon: <Terminal size={20} />, label: 'AI Terminal' },
    { id: 'backtest', icon: <BarChart3 size={20} />, label: 'Backtest' },
  ];

  return (
    <div className="min-h-screen bg-[#050505] text-white flex overflow-hidden font-sans">
      {/* Sidebar */}
      <aside className="w-64 border-r border-red-900/30 bg-[#0a0a0a] flex flex-col">
        <div className="p-6 border-b border-red-900/30">
          <h1 className="text-2xl font-bold text-red-600 tracking-tighter">JARVIS <span className="text-xs font-mono align-top opacity-50">V9</span></h1>
        </div>
        <nav className="flex-1 p-4 space-y-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                activeTab === tab.id ? 'bg-red-900/20 text-red-500 border border-red-900/50' : 'text-gray-500 hover:text-white hover:bg-white/5'
              }`}
            >
              {tab.icon}
              <span className="font-medium">{tab.label}</span>
            </button>
          ))}
        </nav>
        <div className="p-4 border-t border-red-900/30">
           <div className="flex items-center gap-2 text-yellow-500 text-sm">
             <ShieldAlert size={16} />
             <span>Daily Risk Active</span>
           </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto p-8 relative">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            {activeTab === 'dashboard' && (
              <div className="space-y-8">
                <header>
                  <h2 className="text-3xl font-bold">Global Telemetry</h2>
                  <p className="text-gray-400">Live account performance & AI status</p>
                </header>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                   <StatCard title="Balance" value="$10,420.50" color="text-green-500" />
                   <StatCard title="Equity" value="$10,420.50" color="text-blue-500" />
                   <StatCard title="Drawdown" value="0.00%" color="text-red-500" />
                </div>
              </div>
            )}

            {activeTab === 'terminal' && (
              <div className="h-[calc(100vh-10rem)] flex flex-col">
                <div className="bg-black/50 border border-red-900/20 rounded-xl p-6 flex-1 overflow-hidden flex flex-col font-mono text-sm">
                   <div className="flex-1 overflow-y-auto space-y-2 mb-4">
                      <p className="text-green-500">>> Neural God Aethelgard protocol active.</p>
                      <p className="text-gray-500">>> Awaiting command...</p>
                   </div>
                   <input
                    type="text"
                    placeholder="Ask JARVIS to build or optimize..."
                    className="w-full bg-[#111] border border-red-900/30 p-4 rounded-lg focus:outline-none focus:border-red-600 transition-colors"
                   />
                </div>
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
};

const StatCard = ({ title, value, color }: any) => (
  <div className="bg-[#0a0a0a] border border-red-900/10 p-6 rounded-2xl">
    <p className="text-gray-500 text-sm mb-1 uppercase tracking-wider font-bold">{title}</p>
    <p className={`text-2xl font-mono ${color}`}>{value}</p>
  </div>
);

export default App;
