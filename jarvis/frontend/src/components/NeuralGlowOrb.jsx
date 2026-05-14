import React from 'react';
import { motion } from 'framer-motion';

const NeuralGlowOrb = () => {
  return (
    <div className="relative flex items-center justify-center w-80 h-82">
      {/* Apex Singularity Field */}
      <motion.div
        animate={{
          scale: [1, 1.4, 1],
          opacity: [0.1, 0.4, 0.1],
          rotate: [0, -180, -360],
          background: [
            "radial-gradient(circle, rgba(236,72,153,0.15) 0%, transparent 70%)",
            "radial-gradient(circle, rgba(6,182,212,0.15) 0%, transparent 70%)",
            "radial-gradient(circle, rgba(236,72,153,0.15) 0%, transparent 70%)"
          ]
        }}
        transition={{
          duration: 12,
          repeat: Infinity,
          ease: "linear"
        }}
        className="absolute w-full h-full rounded-full blur-3xl"
      />

      {/* Omni-Reign HUD Rings */}
      {[1, 2, 3, 4, 5].map((i) => (
        <motion.div
          key={i}
          animate={{
            rotate: i % 2 === 0 ? 360 : -360,
            scale: [1, 1.02, 1],
            opacity: [0.2, 0.5, 0.2]
          }}
          transition={{
            duration: 20 / i,
            repeat: Infinity,
            ease: "easeInOut"
          }}
          className="absolute rounded-full border border-cyan-400/20"
          style={{
            width: `${100 - i * 10}%`,
            height: `${100 - i * 10}%`,
            borderStyle: i % 2 === 0 ? 'solid' : 'dashed',
            borderWidth: '0.5px'
          }}
        />
      ))}

      {/* Apex Core V4000 */}
      <motion.div
        animate={{
          boxShadow: [
            "0 0 40px rgba(236, 72, 153, 0.3)",
            "0 0 100px rgba(6, 182, 212, 0.5)",
            "0 0 40px rgba(236, 72, 153, 0.3)"
          ]
        }}
        transition={{
          duration: 4,
          repeat: Infinity,
          ease: "easeInOut"
        }}
        className="relative w-40 h-40 rounded-full bg-slate-950 flex items-center justify-center overflow-hidden border border-white/10"
      >
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_rgba(255,255,255,0.05)_0%,_transparent_100%)]" />

        {/* Intention Stream */}
        <motion.div
          animate={{ y: [-100, 100] }}
          transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
          className="absolute inset-0 opacity-10 bg-gradient-to-b from-transparent via-cyan-500 to-transparent"
        />

        <div className="flex flex-col items-center justify-center z-10 text-center">
          <span className="text-[12px] font-black tracking-[0.5em] text-white drop-shadow-[0_0_10px_rgba(255,255,255,0.5)]">APEX</span>
          <span className="text-[7px] font-mono text-cyan-400 mt-1 opacity-80 tracking-widest">V4000 REIGN</span>
        </div>
      </motion.div>

      {/* Apex Telemetry Overlay */}
      <div className="absolute -left-20 top-1/2 -translate-y-1/2 text-[7px] font-mono text-white/40 space-y-2 pointer-events-none">
        <div className="flex flex-col items-end">
          <span>RL_INTUITION</span>
          <span className="text-cyan-400">EVOLVING...</span>
        </div>
        <div className="flex flex-col items-end">
          <span>KERNEL_LOAD</span>
          <span className="text-pink-400">0.0001%</span>
        </div>
      </div>

      <div className="absolute -right-20 top-1/2 -translate-y-1/2 text-[7px] font-mono text-white/40 space-y-2 pointer-events-none text-left">
        <div className="flex flex-col">
          <span>OMNI_SYNC</span>
          <span className="text-cyan-400">SYNCHRONIZED</span>
        </div>
        <div className="flex flex-col">
          <span>MOBILE_LINK</span>
          <span className="text-indigo-400">ENCRYPTED</span>
        </div>
      </div>
    </div>
  );
};

export default NeuralGlowOrb;
