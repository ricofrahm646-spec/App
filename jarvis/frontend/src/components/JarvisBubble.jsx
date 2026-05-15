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
            initial={{ opacity: 0, backdropFilter: "blur(0px)", scale: 0.95 }}
            animate={{ opacity: 1, backdropFilter: "blur(40px)", scale: 1 }}
            exit={{ opacity: 0, backdropFilter: "blur(0px)", scale: 0.95 }}
            className="mb-12 p-12 w-[550px] bg-slate-950/40 border border-white/5 rounded-[4rem] shadow-[0_0_150px_rgba(99,102,241,0.1)] text-white relative overflow-hidden"
          >
            {/* Aether Aura Leuchten */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/5 blur-[120px] rounded-full" />
            <div className="absolute bottom-0 left-0 w-64 h-64 bg-cyan-500/5 blur-[120px] rounded-full" />

            <div className="relative z-10">
              <div className="flex justify-between items-start mb-10">
                <div>
                  <h3 className="text-white font-black tracking-[0.8em] text-[12px] uppercase opacity-70">Nebula Hive V6000</h3>
                  <div className="h-[1px] w-24 bg-gradient-to-r from-cyan-500 via-indigo-500 to-pink-500 mt-3" />
                </div>
                <div className="px-4 py-1.5 bg-white/2 rounded-full border border-white/5 shadow-inner">
                  <span className="text-[9px] font-black text-indigo-300 tracking-widest">NEBULA_SINGULARITY</span>
                </div>
              </div>

              <div className="space-y-10">
                <div className="p-6 bg-black/20 rounded-[2.5rem] border border-white/5 text-[12px] font-mono leading-relaxed group hover:border-white/10 transition-all shadow-2xl">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-1.5 h-1.5 rounded-full bg-cyan-500 shadow-[0_0_10px_rgba(34,211,238,0.8)]" />
                    <span className="text-white/20 tracking-tighter">$ nebula --hive-mind --sync-swarm --precision 99.9999%</span>
                  </div>
                  <p className="text-indigo-100/90 font-light italic">
                    "Nebula Swarm synchronized. 512 nodes active. Liquidity Sniper detected dark pool accumulation. Arbitrage Ghost exploiting cross-broker spreads. Recursive Builder synthesizing sub-agent for institutional front-running. Sir, the digital reality is under our control."
                  </p>
                </div>

                <div className="grid grid-cols-3 gap-6">
                  {[
                    { label: "QUANTUM-ACC", val: "99.99%", color: "text-cyan-300" },
                    { label: "PASSIVE-YIELD", val: "+$124/D", color: "text-white" },
                    { label: "EVOLUTION", val: "H-12", color: "text-pink-300" }
                  ].map((stat, i) => (
                    <div key={i} className="p-5 bg-white/2 rounded-3xl border border-white/5 text-center shadow-inner hover:scale-105 transition-transform cursor-default">
                      <div className="text-[7px] text-white/10 font-black mb-2 tracking-[0.3em] uppercase">{stat.label}</div>
                      <div className={`text-sm font-black tracking-tight ${stat.color}`}>{stat.val}</div>
                    </div>
                  ))}
                </div>

                <div className="space-y-4">
                  <div className="flex justify-between text-[8px] font-black tracking-[0.5em] text-white/20 uppercase">
                    <span>Sovereignty Level</span>
                    <span className="text-indigo-500">Infinite Computing</span>
                  </div>
                  <div className="h-[2px] bg-white/5 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: "99.99%" }}
                      transition={{ duration: 10, repeat: Infinity }}
                      className="h-full bg-gradient-to-r from-cyan-500 via-indigo-500 to-pink-500 shadow-[0_0_15px_rgba(99,102,241,0.5)]"
                    />
                  </div>
                </div>

                <motion.button
                  whileHover={{ scale: 1.02, letterSpacing: "0.6em", boxShadow: "0 0 50px rgba(99,102,241,0.2)" }}
                  whileTap={{ scale: 0.98 }}
                  className="w-full py-6 bg-gradient-to-r from-slate-900 to-slate-950 text-indigo-300 border border-indigo-500/20 rounded-[2.5rem] text-[11px] font-black tracking-[0.5em] transition-all uppercase shadow-2xl"
                >
                  EXECUTE NEBULA SINGULARITY
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
