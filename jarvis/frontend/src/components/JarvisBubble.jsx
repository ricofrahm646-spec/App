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
            initial={{ scale: 0.9, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.9, opacity: 0, y: 20 }}
            className="mb-10 p-10 w-[500px] backdrop-blur-[50px] bg-slate-950/70 border border-white/5 rounded-[3rem] shadow-[0_0_120px_rgba(6,182,212,0.1)] text-white relative overflow-hidden"
          >
            {/* Apex Chromatic Aberration Effect */}
            <div className="absolute inset-0 border border-pink-500/5 translate-x-1 translate-y-1 rounded-[3rem] pointer-events-none" />

            <div className="relative z-10">
              <div className="flex justify-between items-start mb-8">
                <div>
                  <h3 className="text-white font-black tracking-[0.6em] text-[10px] uppercase opacity-90">Omni-Reign Apex</h3>
                  <div className="h-[1px] w-full bg-gradient-to-r from-cyan-500 to-pink-500 mt-2 opacity-50" />
                </div>
                <div className="px-3 py-1 bg-white/5 rounded-full border border-white/10">
                  <span className="text-[8px] font-bold text-cyan-400 animate-pulse">SINGULARITY_LIVE</span>
                </div>
              </div>

              <div className="space-y-8">
                <div className="p-5 bg-white/2 rounded-3xl border border-white/5 text-[11px] font-mono leading-relaxed relative overflow-hidden group">
                  <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                  <span className="text-white/30">$ apex --intuition --feel market</span>
                  <p className="mt-3 text-cyan-100/90 font-medium">
                    "Market heartbeat detected. RL-Policy optimization active. Trend reversal probability for XAUUSD increased to 99.2%. Proactive strike window opening in 40ms."
                  </p>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  {[
                    { label: "RL-EFFICIENCY", val: "99.9%", color: "text-cyan-400" },
                    { label: "OMNI-REVENUE", val: "+14.2K", color: "text-white" },
                    { label: "INTENT-SYNC", val: "1.0", color: "text-pink-400" }
                  ].map((stat, i) => (
                    <div key={i} className="p-4 bg-white/2 rounded-2xl border border-white/5 hover:border-white/10 transition-colors">
                      <div className="text-[7px] text-white/20 font-black mb-1 tracking-widest">{stat.label}</div>
                      <div className={`text-sm font-black ${stat.color}`}>{stat.val}</div>
                    </div>
                  ))}
                </div>

                <div className="space-y-3">
                  <div className="flex justify-between text-[8px] font-bold tracking-widest text-white/30 uppercase">
                    <span>Ghost-Programmer Status</span>
                    <span className="text-cyan-500">Autonomous Synthesis</span>
                  </div>
                  <div className="h-1 bg-white/5 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ x: "-100%" }}
                      animate={{ x: "100%" }}
                      transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
                      className="h-full w-1/3 bg-gradient-to-r from-transparent via-cyan-400 to-transparent"
                    />
                  </div>
                </div>

                <motion.button
                  whileHover={{ scale: 1.01, boxShadow: "0 0 30px rgba(6,182,212,0.2)" }}
                  whileTap={{ scale: 0.99 }}
                  className="w-full py-5 bg-white text-black rounded-3xl text-[10px] font-black tracking-[0.4em] transition-all uppercase hover:bg-cyan-50"
                >
                  Execute Apex Mandate
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
