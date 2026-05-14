import React from 'react';
import { motion } from 'framer-motion';

const NeuralGlowOrb = () => {
  return (
    <div className="relative flex items-center justify-center w-64 h-64">
      {/* Outer Pulse */}
      <motion.div
        animate={{
          scale: [1, 1.2, 1],
          opacity: [0.3, 0.6, 0.3],
          rotate: 360
        }}
        transition={{
          duration: 4,
          repeat: Infinity,
          ease: "linear"
        }}
        className="absolute w-full h-full rounded-full border-2 border-cyan-500/30 blur-sm"
      />

      {/* Holographic Rings */}
      {[1, 2, 3].map((i) => (
        <motion.div
          key={i}
          animate={{
            rotate: i % 2 === 0 ? 360 : -360,
            scale: [1, 1.1, 1]
          }}
          transition={{
            duration: 10 / i,
            repeat: Infinity,
            ease: "linear"
          }}
          className="absolute rounded-full border border-cyan-400/20"
          style={{
            width: `${100 - i * 15}%`,
            height: `${100 - i * 15}%`,
            borderDasharray: i * 10
          }}
        />
      ))}

      {/* Central Core (Neural Orb) */}
      <motion.div
        animate={{
          boxShadow: [
            "0 0 20px rgba(6, 182, 212, 0.5)",
            "0 0 50px rgba(6, 182, 212, 0.8)",
            "0 0 20px rgba(6, 182, 212, 0.5)"
          ]
        }}
        transition={{
          duration: 2,
          repeat: Infinity
        }}
        className="relative w-24 h-24 rounded-full bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center overflow-hidden"
      >
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-white/30 via-transparent to-transparent opacity-50" />
        <div className="text-white font-bold text-xs tracking-tighter opacity-80">J.A.R.V.I.S</div>
      </motion.div>

      {/* Data HUD Lines */}
      <div className="absolute -right-16 top-0 text-[8px] font-mono text-cyan-400 opacity-60 leading-tight">
        <div>CORE_TEMP: 32°C</div>
        <div>SWARM_NODES: 100</div>
        <div>MEM_LOAD: 12%</div>
        <div>MARKET_SYNC: 99.9%</div>
      </div>
    </div>
  );
};

export default NeuralGlowOrb;
