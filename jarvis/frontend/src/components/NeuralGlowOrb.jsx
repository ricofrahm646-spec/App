import React from 'react';
import { motion } from 'framer-motion';

const NeuralGlowOrb = () => {
  return (
    <div className="relative flex items-center justify-center w-72 h-72">
      {/* Volumetric Plasma Field */}
      <motion.div
        animate={{
          scale: [1, 1.3, 1],
          opacity: [0.2, 0.5, 0.2],
          rotate: [0, 180, 360],
          background: [
            "radial-gradient(circle, rgba(6,182,212,0.2) 0%, transparent 70%)",
            "radial-gradient(circle, rgba(59,130,246,0.2) 0%, transparent 70%)",
            "radial-gradient(circle, rgba(6,182,212,0.2) 0%, transparent 70%)"
          ]
        }}
        transition={{
          duration: 8,
          repeat: Infinity,
          ease: "easeInOut"
        }}
        className="absolute w-full h-full rounded-full blur-2xl"
      />

      {/* Ray-Traced HUD Rings */}
      {[1, 2, 3, 4].map((i) => (
        <motion.div
          key={i}
          animate={{
            rotate: i % 2 === 0 ? 360 : -360,
            scale: [1, 1.05, 1],
            borderColor: i % 2 === 0 ? "rgba(6,182,212,0.3)" : "rgba(59,130,246,0.3)"
          }}
          transition={{
            duration: 15 / i,
            repeat: Infinity,
            ease: "linear"
          }}
          className="absolute rounded-full border border-dashed shadow-[0_0_15px_rgba(6,182,212,0.1)]"
          style={{
            width: `${100 - i * 12}%`,
            height: `${100 - i * 12}%`,
            borderWidth: '1px'
          }}
        />
      ))}

      {/* V3000 Quantum Core */}
      <motion.div
        animate={{
          boxShadow: [
            "0 0 30px rgba(6, 182, 212, 0.4)",
            "0 0 70px rgba(59, 130, 246, 0.6)",
            "0 0 30px rgba(6, 182, 212, 0.4)"
          ],
          rotate: [0, 360]
        }}
        transition={{
          duration: 5,
          repeat: Infinity,
          ease: "linear"
        }}
        className="relative w-32 h-32 rounded-full bg-black flex items-center justify-center overflow-hidden border border-cyan-500/50"
      >
        <div className="absolute inset-0 bg-gradient-to-tr from-cyan-500/20 via-blue-500/10 to-transparent" />
        <div className="absolute inset-0 opacity-30 bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')]" />

        {/* Anti-rotation layer for text */}
        <motion.div
          animate={{ rotate: [0, -360] }}
          transition={{ duration: 5, repeat: Infinity, ease: "linear" }}
          className="flex flex-col items-center justify-center z-10"
        >
          <span className="text-[10px] font-black tracking-[0.3em] text-cyan-400 drop-shadow-[0_0_5px_rgba(34,211,238,0.8)]">V3000</span>
          <span className="text-[8px] font-mono text-blue-300 opacity-60">SINGULARITY</span>
        </motion.div>
      </motion.div>

      {/* Plasma Telemetry */}
      <div className="absolute -right-24 top-0 text-[8px] font-mono text-cyan-400/80 space-y-1">
        <div className="flex items-center gap-2">
          <div className="w-1 h-1 bg-cyan-500 animate-ping" />
          ORACLE_CONF: 99.8%
        </div>
        <div>NEXUS_SYNC: ACTIVE</div>
        <div>LATENCY: 0.002ms</div>
        <div className="h-[1px] w-12 bg-cyan-500/30" />
        <div className="text-blue-400/60 italic">"Always ahead."</div>
      </div>
    </div>
  );
};

export default NeuralGlowOrb;
