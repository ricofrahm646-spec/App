'use client'

import { useState } from 'react'
import { Toaster } from 'react-hot-toast'
import DashboardOverview from '@/components/dashboard/DashboardOverview'
import AIChat from '@/components/chat/AIChat'
import TradingPanel from '@/components/trading/TradingPanel'
import StrategyManager from '@/components/strategies/StrategyManager'
import BacktestPanel from '@/components/backtesting/BacktestPanel'
import MQL5Generator from '@/components/mql5/MQL5Generator'
import RiskPanel from '@/components/risk/RiskPanel'
import TradingViewPanel from '@/components/tradingview/TradingViewPanel'
import TelegramConfig from '@/components/telegram/TelegramConfig'
import Sidebar from '@/components/layout/Sidebar'

export default function Home() {
  const [activeSection, setActiveSection] = useState('dashboard')

  const renderContent = () => {
    switch (activeSection) {
      case 'dashboard':
        return <DashboardOverview />
      case 'chat':
        return <AIChat />
      case 'trading':
        return <TradingPanel />
      case 'strategies':
        return <StrategyManager />
      case 'backtesting':
        return <BacktestPanel />
      case 'mql5':
        return <MQL5Generator />
      case 'risk':
        return <RiskPanel />
      case 'tradingview':
        return <TradingViewPanel />
      case 'telegram':
        return <TelegramConfig />
      default:
        return <DashboardOverview />
    }
  }

  return (
    <>
      <div className="flex h-screen overflow-hidden" style={{ backgroundColor: '#0a0a0f' }}>
        <Sidebar activeSection={activeSection} onNavigate={setActiveSection} />
        <main className="flex-1 overflow-auto">
          {renderContent()}
        </main>
      </div>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#12121a',
            color: '#e2e8f0',
            border: '1px solid #1e1e2e',
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '0.8rem',
          },
          success: {
            iconTheme: { primary: '#00ff88', secondary: '#12121a' },
          },
          error: {
            iconTheme: { primary: '#ff3366', secondary: '#12121a' },
          },
        }}
      />
    </>
  )
}
