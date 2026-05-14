import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Zap,
  TrendingUp,
  Mail,
  Calendar,
  ShieldCheck,
  Cpu,
  Target,
  Send,
  Loader2,
  Minimize2
} from 'lucide-react';
import axios from 'axios';

const NeuralGlowOrb = () => {
  const [mission, setMission] = useState('');
  const [logs, setLogs] = useState([
    { type: 'system', text: 'J.A.R.V.I.S. V1000 - MISSION CONTROL ONLINE' },
    { type: 'system', text: 'STEALTH VISION CORE ACTIVE' }
  ]);
  const [isOpen, setIsOpen] = useState(false); // Changed from isMinimized
  const [isProcessing, setIsProcessing] = useState(false);
  const [activeMode, setActiveMode] = useState('IDLE');
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  const executeMission = async () => {
    if (!mission.trim()) return;

    setLogs(prev => [...prev, { type: 'user', text: `MISSION: ${mission}` }]);
    setIsProcessing(true);
    setActiveMode('EXECUTING');
    setMission('');

    try {
      const response = await axios.post('http://localhost:8000/mission', { mission });
      setLogs(prev => [...prev, { type: 'jarvis', text: response.data.output, agent: response.data.agent }]);
    } catch (error) {
      setLogs(prev => [...prev, { type: 'error', text: 'LINK FAILURE: CORE SYSTEM UNREACHABLE' }]);
    } finally {
      setIsProcessing(false);
      setActiveMode('IDLE');
    }
  };

  return (
    <div className="fixed bottom-10 right-10 flex flex-col items-end pointer-events-none">
      <AnimatePresence>
        {isOpen && (
          <motion.div
            key="hud"
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            className="w-[450px] h-[600px] mb-8 relative pointer-events-auto"
            data-testid="jarvis-hud"
          >
            {/* Glass Container */}
            <div className="absolute inset-0 bg-[#0a192f]/80 backdrop-blur-3xl border border-blue-400/20 rounded-[40px] shadow-[0_0_50px_rgba(0,212,255,0.1)] overflow-hidden flex flex-col">

              {/* Header / HUD */}
              <div className="p-6 border-b border-white/5 flex justify-between items-center bg-white/2">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-[#00d4ff] animate-pulse shadow-[0_0_10px_#00d4ff]" />
                  <span className="text-[10px] font-bold tracking-[0.3em] text-[#00d4ff] uppercase">Mission Control V10.0</span>
                </div>
                <button
                  onClick={() => setIsOpen(false)}
                  className="text-white/30 hover:text-white transition-colors"
                >
                  <Minimize2 size={16} />
                </button>
              </div>

              {/* Log Feed */}
              <div
                ref={scrollRef}
                className="flex-1 overflow-y-auto p-6 space-y-4 scrollbar-hide"
              >
                {logs.map((log, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    className={`flex flex-col ${log.type === 'user' ? 'items-end' : 'items-start'}`}
                  >
                    <div className={`max-w-[85%] p-4 rounded-2xl text-xs leading-relaxed ${
                      log.type === 'user'
                      ? 'bg-blue-400/10 border border-blue-400/20 text-white'
                      : log.type === 'error'
                      ? 'bg-red-500/10 border border-red-500/30 text-red-400'
                      : 'bg-white/5 border border-white/10 text-blue-400'
                    }`}>
                      {log.text}
                      {log.agent && (
                        <div className="mt-2 pt-2 border-t border-white/5 flex items-center gap-2 opacity-50 uppercase tracking-widest text-[8px]">
                          <Zap size={8} /> {log.agent} NODE ACTIVE
                        </div>
                      )}
                    </div>
                  </motion.div>
                ))}
                {isProcessing && (
                  <div className="flex items-center gap-2 text-blue-400/50 text-[10px] animate-pulse">
                    <Loader2 size={12} className="animate-spin" />
                    NEURAL PROCESSING IN PROGRESS...
                  </div>
                )}
              </div>

              {/* Interaction Bar */}
              <div className="p-6 bg-white/2 border-t border-white/5">
                <div className="relative">
                  <input
                    type="text"
                    value={mission}
                    onChange={(e) => setMission(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && executeMission()}
                    placeholder="ENTER MISSION OBJECTIVE..."
                    className="w-full bg-[#050c18] border border-blue-400/30 rounded-2xl px-6 py-4 text-xs tracking-widest focus:outline-none focus:border-blue-400 transition-all placeholder:text-white/20 text-white"
                    data-testid="mission-input"
                  />
                  <button
                    onClick={executeMission}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-blue-400 hover:text-white transition-colors"
                  >
                    <Target size={20} />
                  </button>
                </div>

                {/* Mode Selectors */}
                <div className="flex justify-around mt-6 pt-2">
                  <ModeIcon Icon={TrendingUp} label="TRADING" active={activeMode === 'EXECUTING'} />
                  <ModeIcon Icon={Mail} label="COMM" />
                  <ModeIcon Icon={ShieldCheck} label="HEAL" />
                  <ModeIcon Icon={Cpu} label="EVO" />
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* The Core Orb */}
      <motion.div
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={() => setIsOpen(!isOpen)}
        className="w-24 h-24 relative cursor-pointer pointer-events-auto"
        data-testid="jarvis-orb"
      >
        <div className="absolute inset-0 bg-blue-400/20 rounded-full blur-2xl animate-pulse" />
        <div className="absolute inset-0 border-2 border-blue-400/50 rounded-full animate-[spin_10s_linear_infinite]" />
        <div className="absolute inset-2 border border-white/20 rounded-full animate-[spin_15s_linear_infinite_reverse]" />

        <div className="w-full h-full rounded-full bg-[#0a192f] flex items-center justify-center border border-blue-400 shadow-[0_0_30px_rgba(0,212,255,0.3)] overflow-hidden relative z-10">
          <motion.div
            animate={{
              scale: isProcessing ? [1, 1.2, 1] : 1,
              rotate: 360
            }}
            transition={{
                scale: { repeat: Infinity, duration: 1 },
                rotate: { repeat: Infinity, duration: 20, ease: "linear" }
            }}
            className="text-blue-400"
          >
            <Zap size={32} fill="currentColor" className="opacity-80" />
          </motion.div>
        </div>
      </motion.div>
    </div>
  );
};

const ModeIcon = ({ Icon, label, active }) => (
  <div className={`flex flex-col items-center gap-2 group cursor-pointer ${active ? 'text-blue-400' : 'text-white/20'}`}>
    <div className={`p-2 rounded-lg transition-all ${active ? 'bg-blue-400/20' : 'group-hover:bg-white/5'}`}>
      <Icon size={16} />
    </div>
    <span className="text-[7px] font-bold tracking-[0.2em]">{label}</span>
  </div>
);

export default NeuralGlowOrb;
