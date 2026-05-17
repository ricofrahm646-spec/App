import React from 'react'
import NeuralGlowOrb from './components/NeuralGlowOrb'
import { motion } from 'framer-motion'

function App() {
  return (
    <div className="min-h-screen w-full relative flex items-center justify-center bg-[#050c18] overflow-hidden">
      {/* Background Grid Decoration */}
      <div className="absolute inset-0 opacity-10 pointer-events-none"
           style={{ backgroundImage: 'radial-gradient(#00d4ff 0.5px, transparent 0.5px)', backgroundSize: '30px 30px' }} />

      <div className="text-center relative z-0">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1.5 }}
          className="space-y-4"
        >
            <h1 className="text-8xl font-black tracking-tighter text-white uppercase mix-blend-overlay opacity-5 select-none">
            J.A.R.V.I.S.
            </h1>
            <p className="text-blue-400/20 text-[10px] tracking-[1em] font-bold select-none">
            MISSION CONTROL SYSTEM V1000
            </p>
        </motion.div>
      </div>

      <NeuralGlowOrb />

      {/* HUD Analytics Overlay */}
      <div className="absolute top-10 left-10 text-[8px] text-blue-400/30 font-mono space-y-1 select-none">
        <div>CORE_LATENCY: 0.0004s</div>
        <div>TRADING_NODES: 101_ACTIVE</div>
        <div>VISION_STABILITY: 1.0</div>
        <div>EVOLUTION_EQUILIBRIUM: REACHED</div>
      </div>
    </div>
  )
}

export default App
