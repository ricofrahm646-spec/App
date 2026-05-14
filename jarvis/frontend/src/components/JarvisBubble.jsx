import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import NeuralGlowOrb from './NeuralGlowOrb';

const JarvisBubble = () => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="fixed bottom-10 right-10 z-50">
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ scale: 0, opacity: 0, y: 100 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0, opacity: 0, y: 100 }}
            className="mb-8 p-6 w-96 backdrop-blur-xl bg-black/40 border border-cyan-500/30 rounded-3xl shadow-[0_0_50px_rgba(6,182,212,0.2)] text-white"
          >
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-cyan-400 font-bold tracking-widest text-sm">MISSION_CONTROL</h3>
              <div className="w-2 h-2 rounded-full bg-cyan-500 animate-pulse" />
            </div>

            <div className="space-y-4">
              <div className="p-3 bg-white/5 rounded-xl border border-white/10 text-xs font-mono">
                <p className="text-cyan-300">$ Jarvis, status report.</p>
                <p className="mt-2 text-white/70">"All systems operational. Trading swarm backtesting gold strategies with 96% precision target."</p>
              </div>

              <div className="grid grid-cols-2 gap-2 text-[10px] font-mono">
                <div className="p-2 bg-white/5 rounded-lg border border-white/10">
                  <span className="text-white/40">BALANCE:</span> $20.00
                </div>
                <div className="p-2 bg-white/5 rounded-lg border border-white/10">
                  <span className="text-white/40">TARGET:</span> $100.00
                </div>
              </div>

              <button className="w-full py-2 bg-cyan-500/20 border border-cyan-500/50 rounded-xl text-cyan-400 text-xs font-bold hover:bg-cyan-500/40 transition-colors">
                INITIALIZE_QUANTUM_TRADE
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <motion.div
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={() => setIsOpen(!isOpen)}
        className="cursor-pointer"
      >
        <NeuralGlowOrb />
      </motion.div>
    </div>
  );
};

export default JarvisBubble;
