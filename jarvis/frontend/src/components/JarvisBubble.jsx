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
            initial={{ scale: 0.8, opacity: 0, x: 50, rotateX: 45 }}
            animate={{ scale: 1, opacity: 1, x: 0, rotateX: 0 }}
            exit={{ scale: 0.8, opacity: 0, x: 50, rotateX: 45 }}
            transition={{ type: "spring", damping: 15 }}
            className="mb-8 p-8 w-[450px] backdrop-blur-3xl bg-black/60 border border-cyan-500/20 rounded-[2rem] shadow-[0_0_80px_rgba(6,182,212,0.15)] text-white overflow-hidden"
          >
            {/* Plasma Background Glow */}
            <div className="absolute -top-24 -left-24 w-48 h-48 bg-cyan-500/10 blur-[100px] rounded-full" />

            <div className="relative z-10">
              <div className="flex justify-between items-center mb-6">
                <div>
                  <h3 className="text-cyan-400 font-black tracking-[0.4em] text-xs uppercase">Omni-Kernel V3000</h3>
                  <div className="h-0.5 w-12 bg-cyan-500 mt-1" />
                </div>
                <div className="flex gap-1">
                  {[1, 2, 3].map(i => <div key={i} className="w-1 h-1 rounded-full bg-cyan-500/50" />)}
                </div>
              </div>

              <div className="space-y-6">
                <div className="p-4 bg-cyan-500/5 rounded-2xl border border-cyan-500/10 text-[11px] font-mono leading-relaxed">
                  <span className="text-cyan-500">$ j-oracle --predict --target XAUUSD</span>
                  <p className="mt-2 text-blue-200/80 italic">
                    "Neural weights synchronized. 10k price paths correlated. Liquidity pool detected at $2034.50. Ready for institutional strike."
                  </p>
                </div>

                <div className="grid grid-cols-3 gap-3">
                  {[
                    { label: "TRADES", val: "942", color: "text-cyan-400" },
                    { label: "WIN-RATE", val: "95.8%", color: "text-blue-400" },
                    { label: "PRECISION", val: "0.99", color: "text-indigo-400" }
                  ].map((stat, i) => (
                    <div key={i} className="p-3 bg-white/5 rounded-xl border border-white/5 text-center">
                      <div className="text-[8px] text-white/30 font-black mb-1">{stat.label}</div>
                      <div className={`text-xs font-bold ${stat.color}`}>{stat.val}</div>
                    </div>
                  ))}
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between text-[9px] font-mono text-white/40">
                    <span>NEXUS_CAPACITY</span>
                    <span>88%</span>
                  </div>
                  <div className="h-1 bg-white/10 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: "88%" }}
                      className="h-full bg-gradient-to-r from-cyan-500 to-blue-500"
                    />
                  </div>
                </div>

                <motion.button
                  whileHover={{ scale: 1.02, backgroundColor: "rgba(6,182,212,0.2)" }}
                  whileTap={{ scale: 0.98 }}
                  className="w-full py-4 bg-cyan-500/10 border border-cyan-500/30 rounded-2xl text-cyan-400 text-[10px] font-black tracking-[0.2em] transition-all uppercase"
                >
                  Initiate Quantum Strike
                </motion.button>
              </div>
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
