import React from 'react';
import { motion } from 'framer-motion';
import NebulaSwarm from './NebulaSwarm';
import SpatialProjection from './SpatialProjection';

const NeuralGlowOrb = () => {
  return (
    <div className="relative flex items-center justify-center w-84 h-84">
      {/* V9000 Spatial Field */}
      <SpatialProjection />

      {/* Nebula Swarm Node Field */}
      <NebulaSwarm />

      {/* Liquid Metal Aether Field */}
      <motion.div
        animate={{
          scale: [1, 1.5, 1],
          opacity: [0.1, 0.4, 0.1],
          borderRadius: ["40% 60% 70% 30% / 40% 50% 60% 50%", "60% 40% 30% 70% / 50% 60% 40% 50%", "40% 60% 70% 30% / 40% 50% 60% 50%"]
        }}
        transition={{
          duration: 10,
          repeat: Infinity,
          ease: "linear"
        }}
        className="absolute w-full h-full bg-gradient-to-br from-cyan-400/20 via-pink-500/20 to-indigo-500/20 blur-3xl shadow-[inset_0_0_100px_rgba(255,255,255,0.1)]"
      />

      {/* Sovereignty Rings */}
      {[1, 2, 3, 4, 5, 6].map((i) => (
        <motion.div
          key={i}
          animate={{
            rotate: i % 2 === 0 ? 360 : -360,
            scale: [1, 1.05, 1],
            opacity: [0.1, 0.3, 0.1]
          }}
          transition={{
            duration: 25 / i,
            repeat: Infinity,
            ease: "easeInOut"
          }}
          className="absolute rounded-full border border-white/10"
          style={{
            width: `${100 - i * 8}%`,
            height: `${100 - i * 8}%`,
            borderStyle: i % 3 === 0 ? 'double' : 'dashed',
            borderWidth: '0.2px'
          }}
        />
      ))}

      {/* Aether Core V5000 */}
      <motion.div
        animate={{
          boxShadow: [
            "0 0 50px rgba(6, 182, 212, 0.2)",
            "0 0 120px rgba(236, 72, 153, 0.4)",
            "0 0 50px rgba(6, 182, 212, 0.2)"
          ],
          background: [
            "radial-gradient(circle, #020617 0%, #0f172a 100%)",
            "radial-gradient(circle, #1e1b4b 0%, #020617 100%)",
            "radial-gradient(circle, #020617 0%, #0f172a 100%)"
          ]
        }}
        transition={{
          duration: 6,
          repeat: Infinity,
          ease: "easeInOut"
        }}
        className="relative w-44 h-44 rounded-full flex items-center justify-center overflow-hidden border border-white/5 shadow-2xl"
      >
        {/* Bio-Sense Pulse */}
        <motion.div
          animate={{ scale: [0.8, 1.2, 0.8], opacity: [0.2, 0.5, 0.2] }}
          transition={{ duration: 2, repeat: Infinity }}
          className="absolute w-24 h-24 bg-cyan-500/20 rounded-full blur-xl"
        />

        {/* Fluid Metal Simulation */}
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
          className="absolute inset-0 opacity-20 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')]"
        />

        <div className="flex flex-col items-center justify-center z-10 text-center select-none">
          {/* Dynamic Voxel Core V9000 */}
          <motion.div
            animate={{ rotateY: 360, rotateX: 360 }}
            transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
            className="absolute inset-0 flex items-center justify-center opacity-30"
          >
             <div className="w-full h-full bg-[url('https://www.transparenttextures.com/patterns/microchip-grid.png')] scale-150" />
          </motion.div>

          <span className="text-[14px] font-black tracking-[0.8em] text-white drop-shadow-[0_0_25px_rgba(255,255,255,0.8)] ml-2">V9000</span>
          <span className="text-[6px] font-mono text-cyan-300 mt-2 opacity-50 tracking-[0.4em] uppercase">Aethelgard Omega</span>
        </div>
      </motion.div>

      {/* Aether Telemetry Aura */}
      <div className="absolute -left-24 top-0 text-[6px] font-mono text-white/30 space-y-4 pointer-events-none text-right">
        <div>
          <span className="block text-cyan-400 font-bold">DARK_POOL_SYNC</span>
          99.998% EQUILIBRIUM
        </div>
        <div>
          <span className="block text-pink-400 font-bold">BIO_FEEDBACK</span>
          STRESS: 0.12 | FOCUS: 0.98
        </div>
      </div>

      <div className="absolute -right-24 bottom-0 text-[6px] font-mono text-white/30 space-y-4 pointer-events-none text-left">
        <div>
          <span className="block text-indigo-400 font-bold">AETHER_EVOLUTION</span>
          FEATURE_SYNTHESIS: ACTIVE
        </div>
        <div>
          <span className="block text-white font-bold">PASSIVE_PNL</span>
          +$2.45/HR (YIELD_GEN)
        </div>
      </div>
    </div>
  );
};

export default NeuralGlowOrb;
