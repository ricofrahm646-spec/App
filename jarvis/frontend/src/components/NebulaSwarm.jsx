import React from 'react';
import { motion } from 'framer-motion';

const NebulaSwarm = () => {
  // Simulate 500+ micro-agent nodes as tiny shimmering particles
  const nodes = Array.from({ length: 120 }).map((_, i) => ({
    id: i,
    x: Math.random() * 600 - 300,
    y: Math.random() * 600 - 300,
    size: Math.random() * 2 + 1,
    duration: Math.random() * 5 + 5
  }));

  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden">
      {nodes.map((node) => (
        <motion.div
          key={node.id}
          initial={{ x: 0, y: 0, opacity: 0 }}
          animate={{
            x: node.x,
            y: node.y,
            opacity: [0, 0.4, 0],
            scale: [1, 1.5, 1]
          }}
          transition={{
            duration: node.duration,
            repeat: Infinity,
            ease: "easeInOut"
          }}
          className="absolute left-1/2 top-1/2 w-1 h-1 bg-cyan-400 rounded-full blur-[1px]"
          style={{ width: node.size, height: node.size }}
        />
      ))}

      {/* Neural Pathways */}
      <svg className="absolute inset-0 w-full h-full opacity-10">
        <defs>
          <linearGradient id="nebula-grad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#22d3ee" />
            <stop offset="100%" stopColor="#818cf8" />
          </linearGradient>
        </defs>
        {Array.from({ length: 20 }).map((_, i) => (
          <motion.path
            key={i}
            d={`M ${Math.random() * 1000} ${Math.random() * 1000} Q ${Math.random() * 1000} ${Math.random() * 1000} ${Math.random() * 1000} ${Math.random() * 1000}`}
            stroke="url(#nebula-grad)"
            strokeWidth="0.5"
            fill="none"
            initial={{ pathLength: 0, opacity: 0 }}
            animate={{ pathLength: 1, opacity: [0, 0.5, 0] }}
            transition={{ duration: 10, repeat: Infinity, delay: i * 0.5 }}
          />
        ))}
      </svg>
    </div>
  );
};

export default NebulaSwarm;
