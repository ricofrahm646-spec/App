import React from 'react';
import { motion } from 'framer-motion';

const SpatialProjection = () => {
  return (
    <div className="fixed inset-0 pointer-events-none z-0">
      {/* Table Surface Projection Simulation */}
      <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[1200px] h-[400px] bg-cyan-500/5 rounded-[100%] blur-[120px]" />

      {/* Holographic Controls */}
      <div className="absolute bottom-10 left-1/2 -translate-x-1/2 flex gap-20">
        {[1, 2, 3].map((i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 0.3, y: 0 }}
            transition={{ delay: i * 0.2 }}
            className="w-32 h-2 bg-gradient-to-r from-cyan-500 to-transparent rounded-full relative"
          >
            <motion.div
              animate={{ x: [0, 80, 0] }}
              transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
              className="absolute -top-1 w-4 h-4 bg-white/20 rounded-full blur-[2px] border border-white/40"
            />
            <div className="absolute -top-6 left-0 text-[6px] font-black tracking-widest text-white/40 uppercase">
              Quantum_Parameter_{i}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default SpatialProjection;
