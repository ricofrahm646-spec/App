'use client'

import { useState, useRef, useEffect } from 'react'
import { useJarvisStore } from '@/store/useJarvisStore'
import { ChatMessage } from '@/types'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import {
  Send,
  Bot,
  User,
  Zap,
  Code,
  TrendingUp,
  BarChart2,
  Shield,
  Trash2,
  Copy,
  Check,
  FileCode,
  Download,
} from 'lucide-react'
import clsx from 'clsx'
import toast from 'react-hot-toast'
const QUICK_ACTIONS = [
  { label: 'Build Gold Bot', prompt: 'Create a professional MQL5 Expert Advisor for XAUUSD using ICT concepts including order blocks, fair value gaps, and market structure breaks. Include risk management with 1% per trade.', icon: TrendingUp },
  { label: 'Create ICT Strategy', prompt: 'Design a complete ICT (Inner Circle Trader) forex trading strategy for EURUSD on H1 timeframe with entry rules, stop loss placement, and take profit targets.', icon: Code },
  { label: 'Optimize Strategy', prompt: 'Analyze my current trading strategies and suggest optimization parameters for better risk-adjusted returns. Focus on reducing drawdown while maintaining winrate above 60%.', icon: BarChart2 },
  { label: 'Risk Analysis', prompt: 'Perform a comprehensive risk analysis of my trading account and provide recommendations for position sizing, maximum exposure limits, and drawdown prevention.', icon: Shield },
  { label: 'Backtest Setup', prompt: 'Help me set up a proper backtesting framework for my scalping strategy. What parameters should I optimize and what metrics should I focus on?', icon: BarChart2 },
  { label: 'News Trading Bot', prompt: 'Create an MQL5 Expert Advisor that trades high-impact news events. It should detect volatility spikes and execute trades with tight risk management.', icon: Zap },
]

function generateId(): string {
  return Math.random().toString(36).substr(2, 9) + Date.now().toString(36)
}

interface CodeBlockProps {
  language: string
  value: string
}

function CodeBlock({ language, value }: CodeBlockProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(value)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
    toast.success('Code copied!')
  }

  return (
    <div
      className="relative rounded-lg overflow-hidden my-3"
      style={{ border: '1px solid rgba(30,30,46,0.8)' }}
    >
      <div
        className="flex items-center justify-between px-4 py-2"
        style={{ backgroundColor: '#0d0d17', borderBottom: '1px solid rgba(30,30,46,0.8)' }}
      >
        <span className="text-[11px] text-jarvis-muted font-mono font-semibold uppercase tracking-wider">
          {language || 'code'}
        </span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 text-[11px] text-jarvis-muted hover:text-jarvis-accent transition-colors"
        >
          {copied ? <Check size={12} /> : <Copy size={12} />}
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <SyntaxHighlighter
        language={language || 'text'}
        style={oneDark}
        customStyle={{
          margin: 0,
          borderRadius: 0,
          background: '#0a0a14',
          fontSize: '0.78rem',
          lineHeight: '1.6',
        }}
        showLineNumbers={value.split('\n').length > 5}
      >
        {value}
      </SyntaxHighlighter>
    </div>
  )
}

interface MessageBubbleProps {
  message: ChatMessage
}

function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  return (
    <div
      className={clsx('flex gap-3 animate-slide-in', {
        'flex-row-reverse': isUser,
      })}
    >
      {/* Avatar */}
      <div
        className={clsx(
          'flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center',
          isUser
            ? 'bg-jarvis-border'
            : ''
        )}
        style={!isUser ? {
          background: 'linear-gradient(135deg, rgba(139,92,246,0.3), rgba(0,212,255,0.3))',
          border: '1px solid rgba(0,212,255,0.3)',
          boxShadow: '0 0 8px rgba(0,212,255,0.15)',
        } : {
          background: 'rgba(30,30,46,0.8)',
          border: '1px solid rgba(30,30,46,0.8)',
        }}
      >
        {isUser ? (
          <User size={14} className="text-jarvis-muted" />
        ) : (
          <Bot size={14} style={{ color: '#00d4ff' }} />
        )}
      </div>

      {/* Content */}
      <div
        className={clsx('flex-1 max-w-[85%] rounded-xl px-4 py-3', {
          'rounded-tr-sm': isUser,
          'rounded-tl-sm': !isUser,
        })}
        style={isUser ? {
          backgroundColor: 'rgba(0,212,255,0.08)',
          border: '1px solid rgba(0,212,255,0.15)',
        } : {
          backgroundColor: '#12121a',
          border: '1px solid #1e1e2e',
        }}
      >
        <div className="text-xs text-jarvis-muted mb-1.5 flex items-center gap-2">
          <span>{isUser ? 'You' : 'JARVIS'}</span>
          <span>•</span>
          <span>{new Date(message.timestamp).toLocaleTimeString()}</span>
        </div>
        <div className="text-sm text-jarvis-text leading-relaxed">
          {isUser ? (
            <p>{message.content}</p>
          ) : (
            <ReactMarkdown
              components={{
                code({ node, className, children, ...props }) {
                  const match = /language-(\w+)/.exec(className || '')
                  const isInline = !className
                  return !isInline ? (
                    <CodeBlock
                      language={match ? match[1] : ''}
                      value={String(children).replace(/\n$/, '')}
                    />
                  ) : (
                    <code
                      className="px-1.5 py-0.5 rounded text-jarvis-accent text-[0.8em]"
                      style={{ backgroundColor: 'rgba(0,212,255,0.1)' }}
                      {...props}
                    >
                      {children}
                    </code>
                  )
                },
                h1: ({ children }) => (
                  <h1 className="text-base font-bold text-jarvis-accent mb-2 mt-3 first:mt-0">
                    {children}
                  </h1>
                ),
                h2: ({ children }) => (
                  <h2 className="text-sm font-bold text-jarvis-text mb-1.5 mt-3 first:mt-0">
                    {children}
                  </h2>
                ),
                h3: ({ children }) => (
                  <h3 className="text-xs font-bold text-jarvis-text mb-1 mt-2 first:mt-0">
                    {children}
                  </h3>
                ),
                p: ({ children }) => (
                  <p className="mb-2 last:mb-0 text-jarvis-text leading-relaxed">{children}</p>
                ),
                ul: ({ children }) => (
                  <ul className="list-none space-y-1 mb-2 pl-2">{children}</ul>
                ),
                ol: ({ children }) => (
                  <ol className="list-decimal pl-5 space-y-1 mb-2 text-jarvis-text">{children}</ol>
                ),
                li: ({ children }) => (
                  <li className="flex items-start gap-2 text-jarvis-text">
                    <span className="mt-2 w-1 h-1 rounded-full bg-jarvis-accent flex-shrink-0" />
                    <span>{children}</span>
                  </li>
                ),
                strong: ({ children }) => (
                  <strong className="font-bold text-jarvis-accent">{children}</strong>
                ),
                em: ({ children }) => (
                  <em className="italic text-jarvis-muted">{children}</em>
                ),
                blockquote: ({ children }) => (
                  <blockquote
                    className="pl-3 my-2 italic text-jarvis-muted text-xs"
                    style={{ borderLeft: '2px solid rgba(0,212,255,0.4)' }}
                  >
                    {children}
                  </blockquote>
                ),
              }}
            >
              {message.content}
            </ReactMarkdown>
          )}
        </div>

        {/* Generated Files */}
        {message.files && message.files.length > 0 && (
          <div className="mt-3 pt-3" style={{ borderTop: '1px solid rgba(30,30,46,0.8)' }}>
            <div className="text-[11px] text-jarvis-muted mb-2 font-semibold uppercase tracking-wider">
              Generated Files
            </div>
            <div className="space-y-1.5">
              {message.files.map((file, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg"
                  style={{
                    backgroundColor: 'rgba(0,212,255,0.05)',
                    border: '1px solid rgba(0,212,255,0.15)',
                  }}
                >
                  <FileCode size={12} style={{ color: '#00d4ff' }} />
                  <span className="text-[11px] font-mono text-jarvis-text flex-1 truncate">
                    {file.name}
                  </span>
                  <span
                    className="text-[10px] px-1.5 py-0.5 rounded font-semibold"
                    style={{
                      backgroundColor: 'rgba(0,212,255,0.1)',
                      color: '#00d4ff',
                    }}
                  >
                    {file.type.toUpperCase()}
                  </span>
                  <button className="text-jarvis-muted hover:text-jarvis-accent transition-colors">
                    <Download size={11} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function ThinkingIndicator() {
  return (
    <div className="flex gap-3">
      <div
        className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center"
        style={{
          background: 'linear-gradient(135deg, rgba(139,92,246,0.3), rgba(0,212,255,0.3))',
          border: '1px solid rgba(0,212,255,0.3)',
          boxShadow: '0 0 8px rgba(0,212,255,0.15)',
        }}
      >
        <Bot size={14} style={{ color: '#00d4ff' }} />
      </div>
      <div
        className="flex items-center gap-2 px-4 py-3 rounded-xl rounded-tl-sm"
        style={{
          backgroundColor: '#12121a',
          border: '1px solid #1e1e2e',
        }}
      >
        <div className="flex items-center gap-1">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="w-1.5 h-1.5 rounded-full bg-jarvis-accent"
              style={{
                animation: `bounce 1.4s ease-in-out ${i * 0.2}s infinite`,
              }}
            />
          ))}
        </div>
        <span className="text-xs text-jarvis-muted ml-1">JARVIS is thinking...</span>
      </div>
      <style>{`
        @keyframes bounce {
          0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
          40% { transform: translateY(-6px); opacity: 1; }
        }
      `}</style>
    </div>
  )
}

export default function AIChat() {
  const { chatHistory, addMessage, clearChat, aiStatus, setAiStatus } = useJarvisStore()
  const [input, setInput] = useState('')
  const [isThinking, setIsThinking] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatHistory, isThinking])

  const simulateAIResponse = async (userMessage: string): Promise<string> => {
    await new Promise((resolve) => setTimeout(resolve, 1500 + Math.random() * 1000))

    const lowerMsg = userMessage.toLowerCase()

    if (lowerMsg.includes('gold') || lowerMsg.includes('xauusd')) {
      return `# XAUUSD Trading Strategy

I've analyzed the current market structure for **XAUUSD** and here's my recommendation:

## Market Bias: BULLISH

Current price action shows:
- **Order Block** identified at $2,290-$2,295
- **Fair Value Gap** at $2,305-$2,308 (unmitigated)
- **Break of Structure** to the upside on H4

## Entry Setup

\`\`\`
Symbol: XAUUSD
Direction: BUY
Entry: 2,295.00 (OB mitigation)
Stop Loss: 2,288.50 (below OB)
Take Profit 1: 2,310.00 (FVG fill)
Take Profit 2: 2,325.00 (previous high)
Risk/Reward: 1:2.5
\`\`\`

## MQL5 Code Snippet

\`\`\`cpp
// ICT Gold Scalper - Entry Logic
void CheckEntry() {
   double ob_high = 2295.00;
   double ob_low = 2290.00;
   double current = SymbolInfoDouble("XAUUSD", SYMBOL_BID);
   
   if (current >= ob_low && current <= ob_high) {
      double sl = ob_low - 6.50;  // Below OB
      double tp = 2310.00;        // FVG target
      PlaceBuyOrder(0.1, sl, tp, "ICT_XAUUSD");
   }
}
\`\`\`

Would you like me to generate the **complete Expert Advisor** for this strategy?`
    }

    if (lowerMsg.includes('risk') || lowerMsg.includes('position size')) {
      return `# Risk Management Analysis

Based on your account balance of **$12,547.83**, here are my recommendations:

## Position Sizing Formula

\`\`\`
Risk Amount = Balance × Risk% = $12,547.83 × 1% = $125.48
Lots = Risk Amount / (StopLoss_Pips × Pip_Value)
\`\`\`

## Recommended Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Risk per trade | 1.0% | Conservative, protects capital |
| Max daily loss | 3.0% | Stops trading after 3 losses |
| Max drawdown | 10% | Emergency stop threshold |
| Max positions | 3 | Reduces correlation risk |

## Current Risk Status

- **Daily P&L**: +$127.50 (1.02% of balance)
- **Open Risk**: $285.40 margin used
- **Account Health**: ✅ Excellent

Would you like me to adjust these parameters or calculate position sizes for specific symbols?`
    }

    if (lowerMsg.includes('backtest') || lowerMsg.includes('optimize')) {
      return `# Strategy Optimization Report

I've analyzed your trading history and identified key optimization opportunities:

## Current Performance
- Winrate: 64.3%
- Profit Factor: 2.12
- Max Drawdown: 8.7%
- Sharpe Ratio: 1.85

## Optimization Recommendations

### 1. Entry Timing
**Problem**: 23% of losing trades entered during low-liquidity sessions.
**Fix**: Add session filter - trade only during London (08:00-16:00 UTC) and NY (13:00-21:00 UTC).

### 2. Stop Loss Placement
**Problem**: Stops placed too close - being hit by normal noise.
**Fix**: Use ATR-based stops: \`SL = ATR(14) × 1.5\`

### 3. Take Profit Optimization
**Problem**: Average winner = 1.8R, could be improved.
**Fix**: Use partial close at 1R, trail remainder with breakeven.

\`\`\`cpp
// ATR-based Stop Loss
double atr = iATR(_Symbol, PERIOD_H1, 14, 0);
double sl_distance = atr * 1.5;
double sl = (trade_type == BUY) ? 
   entry_price - sl_distance : 
   entry_price + sl_distance;
\`\`\`

Want me to implement these optimizations in your EA?`
    }

    return `# JARVIS Response

I've processed your request. Here's what I can help you with:

## Available Commands

- **"Build [symbol] bot"** - Generate a complete MQL5 EA
- **"Create ICT strategy"** - Design ICT-based trading rules
- **"Optimize [strategy]"** - Analyze and improve existing strategies
- **"Risk analysis"** - Review and optimize risk parameters
- **"Backtest setup"** - Configure backtesting parameters
- **"Generate Pine Script"** - Create TradingView indicators

## Current System Status

- MT5 Connection: ✅ Active
- AI Engine: ✅ Online
- Open Trades: 3 positions
- Daily P&L: +$127.50

What would you like to build today? I can generate production-ready MQL5 code, analyze strategies, or help you optimize your trading system.`
  }

  const handleSend = async (messageText?: string) => {
    const text = messageText || input.trim()
    if (!text || isThinking) return

    setInput('')

    const userMessage: ChatMessage = {
      id: generateId(),
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    }

    addMessage(userMessage)
    setIsThinking(true)
    setAiStatus('thinking')

    try {
      const responseText = await simulateAIResponse(text)

      const assistantMessage: ChatMessage = {
        id: generateId(),
        role: 'assistant',
        content: responseText,
        timestamp: new Date().toISOString(),
      }

      addMessage(assistantMessage)
    } catch (error) {
      toast.error('Failed to get AI response')
      setAiStatus('error')
    } finally {
      setIsThinking(false)
      setAiStatus('idle')
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex flex-col h-full" style={{ backgroundColor: '#0a0a0f' }}>
      {/* Header */}
      <div
        className="flex items-center justify-between px-6 py-4 border-b flex-shrink-0"
        style={{ backgroundColor: '#0d0d14', borderColor: '#1e1e2e' }}
      >
        <div className="flex items-center gap-3">
          <div
            className="flex items-center justify-center w-9 h-9 rounded-lg"
            style={{
              background: 'linear-gradient(135deg, rgba(139,92,246,0.3), rgba(0,212,255,0.3))',
              border: '1px solid rgba(0,212,255,0.3)',
              boxShadow: '0 0 12px rgba(0,212,255,0.15)',
            }}
          >
            <Bot size={18} style={{ color: '#00d4ff' }} />
          </div>
          <div>
            <div className="text-sm font-bold text-jarvis-text">JARVIS AI Assistant</div>
            <div className="flex items-center gap-1.5 text-[11px]">
              <div className="w-1.5 h-1.5 rounded-full bg-jarvis-green animate-pulse" />
              <span className="text-jarvis-green">Online</span>
              <span className="text-jarvis-muted mx-1">•</span>
              <span className="text-jarvis-muted">GPT-4 Turbo • Trading Expert Mode</span>
            </div>
          </div>
        </div>
        <button
          onClick={clearChat}
          className="flex items-center gap-1.5 text-xs text-jarvis-muted hover:text-jarvis-red transition-colors px-3 py-1.5 rounded-lg"
          style={{ border: '1px solid rgba(30,30,46,0.8)' }}
        >
          <Trash2 size={12} />
          Clear
        </button>
      </div>

      {/* Quick Actions */}
      <div
        className="flex gap-2 px-4 py-3 overflow-x-auto flex-shrink-0"
        style={{ borderBottom: '1px solid #1e1e2e', backgroundColor: '#0d0d14' }}
      >
        {QUICK_ACTIONS.map((action) => {
          const Icon = action.icon
          return (
            <button
              key={action.label}
              onClick={() => handleSend(action.prompt)}
              disabled={isThinking}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold whitespace-nowrap transition-all hover:opacity-80 disabled:opacity-40"
              style={{
                backgroundColor: 'rgba(0,212,255,0.06)',
                border: '1px solid rgba(0,212,255,0.15)',
                color: '#00d4ff',
              }}
            >
              <Icon size={11} />
              {action.label}
            </button>
          )
        })}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5">
        {chatHistory.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        {isThinking && <ThinkingIndicator />}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div
        className="flex-shrink-0 px-6 py-4 border-t"
        style={{ backgroundColor: '#0d0d14', borderColor: '#1e1e2e' }}
      >
        <div
          className="flex gap-3 items-end rounded-xl p-3 transition-all"
          style={{
            backgroundColor: 'rgba(18,18,26,0.8)',
            border: '1px solid rgba(30,30,46,0.8)',
          }}
        >
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask JARVIS to build EAs, analyze markets, manage risk..."
            disabled={isThinking}
            rows={1}
            className="flex-1 bg-transparent text-sm text-jarvis-text placeholder-jarvis-muted resize-none outline-none font-mono leading-relaxed"
            style={{
              maxHeight: '120px',
              overflowY: 'auto',
            }}
            onInput={(e) => {
              const target = e.target as HTMLTextAreaElement
              target.style.height = 'auto'
              target.style.height = `${Math.min(target.scrollHeight, 120)}px`
            }}
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || isThinking}
            className="flex items-center justify-center w-9 h-9 rounded-lg transition-all flex-shrink-0 disabled:opacity-30"
            style={{
              background: input.trim() && !isThinking
                ? 'linear-gradient(135deg, rgba(0,212,255,0.3), rgba(139,92,246,0.3))'
                : 'rgba(30,30,46,0.5)',
              border: '1px solid rgba(0,212,255,0.3)',
            }}
          >
            <Send size={14} style={{ color: '#00d4ff' }} />
          </button>
        </div>
        <div className="text-[10px] text-jarvis-muted mt-2 text-center">
          Press Enter to send • Shift+Enter for new line
        </div>
      </div>
    </div>
  )
}
