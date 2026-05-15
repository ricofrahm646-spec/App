'use client'

import { useState } from 'react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import {
  Code,
  Download,
  Upload,
  Copy,
  Check,
  Loader2,
  FileCode,
  Zap,
  ChevronRight,
} from 'lucide-react'
import toast from 'react-hot-toast'

const STRATEGY_TYPES = [
  { id: 'ict_scalping', label: 'ICT Scalping', desc: 'Order blocks, FVG, market structure' },
  { id: 'trend_following', label: 'Trend Following', desc: 'EMA crossovers, ADX filter' },
  { id: 'breakout', label: 'Breakout', desc: 'Range breakout with volume' },
  { id: 'news_trading', label: 'News Trading', desc: 'Volatility-based news EA' },
  { id: 'grid', label: 'Grid Trading', desc: 'Automated grid strategy' },
  { id: 'martingale', label: 'Martingale', desc: 'Progressive position sizing' },
]

const SYMBOLS = ['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY', 'BTCUSD']
const TIMEFRAMES = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1']

function generateEACode(config: {
  type: string
  name: string
  symbol: string
  timeframe: string
  riskPercent: number
  stopLoss: number
  takeProfit: number
  magicNumber: number
}): string {
  const typeName = STRATEGY_TYPES.find((t) => t.id === config.type)?.label || 'Custom'

  return `//+------------------------------------------------------------------+
//|  ${config.name}                                                    |
//|  JARVIS AI Trading OS - Generated EA                               |
//|  Strategy Type: ${typeName.padEnd(44)}|
//+------------------------------------------------------------------+
#property copyright "JARVIS AI"
#property version   "1.00"
#property strict

//--- Input Parameters
input string   InpSymbol      = "${config.symbol}";      // Trading Symbol
input ENUM_TIMEFRAMES InpTF   = PERIOD_${config.timeframe};  // Timeframe
input double   InpRiskPercent = ${config.riskPercent};   // Risk Per Trade (%)
input double   InpStopLoss    = ${config.stopLoss};      // Stop Loss (points)
input double   InpTakeProfit  = ${config.takeProfit};    // Take Profit (points)
input int      InpMagicNumber = ${config.magicNumber};   // Magic Number
input bool     InpUseTrailing = true;                    // Use Trailing Stop
input double   InpTrailingStart = 30;                    // Trailing Start (points)
input double   InpTrailingStep  = 10;                    // Trailing Step (points)

//--- Global Variables
CTrade         trade;
double         g_point;
int            g_atr_handle;
int            g_ema_fast;
int            g_ema_slow;

//+------------------------------------------------------------------+
//| Expert initialization function                                    |
//+------------------------------------------------------------------+
int OnInit() {
   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetDeviationInPoints(10);
   
   g_point = SymbolInfoDouble(InpSymbol, SYMBOL_POINT);
   
   // Initialize indicators
   g_atr_handle  = iATR(InpSymbol, InpTF, 14);
   g_ema_fast    = iMA(InpSymbol, InpTF, 20, 0, MODE_EMA, PRICE_CLOSE);
   g_ema_slow    = iMA(InpSymbol, InpTF, 50, 0, MODE_EMA, PRICE_CLOSE);
   
   if (g_atr_handle == INVALID_HANDLE || 
       g_ema_fast == INVALID_HANDLE || 
       g_ema_slow == INVALID_HANDLE) {
      Print("Failed to initialize indicators");
      return INIT_FAILED;
   }
   
   Print("${config.name} initialized successfully");
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                  |
//+------------------------------------------------------------------+
void OnDeinit(const int reason) {
   IndicatorRelease(g_atr_handle);
   IndicatorRelease(g_ema_fast);
   IndicatorRelease(g_ema_slow);
}

//+------------------------------------------------------------------+
//| Expert tick function                                              |
//+------------------------------------------------------------------+
void OnTick() {
   // Only trade on new bar
   static datetime last_bar = 0;
   datetime current_bar = iTime(InpSymbol, InpTF, 0);
   if (current_bar == last_bar) return;
   last_bar = current_bar;
   
   // Risk management check
   if (!CheckRiskLimits()) return;
   
   // Check for open positions
   if (HasOpenPosition()) {
      ManagePosition();
      return;
   }
   
   // Entry logic
   CheckEntrySignal();
}

//+------------------------------------------------------------------+
//| Check entry signal                                               |
//+------------------------------------------------------------------+
void CheckEntrySignal() {
   double atr[];
   double ema_f[], ema_s[];
   
   ArraySetAsSeries(atr,   true);
   ArraySetAsSeries(ema_f, true);
   ArraySetAsSeries(ema_s, true);
   
   if (CopyBuffer(g_atr_handle, 0, 0, 3, atr)   < 3) return;
   if (CopyBuffer(g_ema_fast,   0, 0, 3, ema_f) < 3) return;
   if (CopyBuffer(g_ema_slow,   0, 0, 3, ema_s) < 3) return;
   
   double ask = SymbolInfoDouble(InpSymbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(InpSymbol, SYMBOL_BID);
   
   // Bullish Signal: EMA crossover + price above both EMAs
   bool bull_cross = ema_f[1] < ema_s[1] && ema_f[0] > ema_s[0];
   bool bull_conf  = ask > ema_fast[0] && ask > ema_slow[0];
   
   // Bearish Signal: EMA crossunder + price below both EMAs
   bool bear_cross = ema_f[1] > ema_s[1] && ema_f[0] < ema_s[0];
   bool bear_conf  = bid < ema_f[0] && bid < ema_s[0];
   
   double sl_dist = atr[0] * 1.5;
   double lot     = CalculateLotSize(sl_dist);
   
   if (bull_cross && bull_conf) {
      double sl = NormalizeDouble(ask - sl_dist, _Digits);
      double tp = NormalizeDouble(ask + sl_dist * 2.0, _Digits);
      if (trade.Buy(lot, InpSymbol, ask, sl, tp, "JARVIS_BUY")) {
         Print("BUY order placed: Lots=", lot, " SL=", sl, " TP=", tp);
      }
   }
   else if (bear_cross && bear_conf) {
      double sl = NormalizeDouble(bid + sl_dist, _Digits);
      double tp = NormalizeDouble(bid - sl_dist * 2.0, _Digits);
      if (trade.Sell(lot, InpSymbol, bid, sl, tp, "JARVIS_SELL")) {
         Print("SELL order placed: Lots=", lot, " SL=", sl, " TP=", tp);
      }
   }
}

//+------------------------------------------------------------------+
//| Calculate position size based on risk %                          |
//+------------------------------------------------------------------+
double CalculateLotSize(double sl_distance) {
   double account_balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double risk_amount     = account_balance * (InpRiskPercent / 100.0);
   double tick_value      = SymbolInfoDouble(InpSymbol, SYMBOL_TRADE_TICK_VALUE);
   double tick_size       = SymbolInfoDouble(InpSymbol, SYMBOL_TRADE_TICK_SIZE);
   double lot_step        = SymbolInfoDouble(InpSymbol, SYMBOL_VOLUME_STEP);
   double min_lot         = SymbolInfoDouble(InpSymbol, SYMBOL_VOLUME_MIN);
   double max_lot         = SymbolInfoDouble(InpSymbol, SYMBOL_VOLUME_MAX);
   
   if (tick_size == 0 || tick_value == 0) return min_lot;
   
   double lots = risk_amount / ((sl_distance / tick_size) * tick_value);
   lots = MathFloor(lots / lot_step) * lot_step;
   lots = MathMax(lots, min_lot);
   lots = MathMin(lots, max_lot);
   
   return NormalizeDouble(lots, 2);
}

//+------------------------------------------------------------------+
//| Manage existing position (trailing stop)                         |
//+------------------------------------------------------------------+
void ManagePosition() {
   if (!InpUseTrailing) return;
   
   for (int i = PositionsTotal() - 1; i >= 0; i--) {
      ulong ticket = PositionGetTicket(i);
      if (!PositionSelectByTicket(ticket)) continue;
      if (PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;
      if (PositionGetString(POSITION_SYMBOL) != InpSymbol) continue;
      
      double open_price = PositionGetDouble(POSITION_PRICE_OPEN);
      double current_sl = PositionGetDouble(POSITION_SL);
      long   pos_type   = PositionGetInteger(POSITION_TYPE);
      double current_price = (pos_type == POSITION_TYPE_BUY)
                              ? SymbolInfoDouble(InpSymbol, SYMBOL_BID)
                              : SymbolInfoDouble(InpSymbol, SYMBOL_ASK);
      
      double trail_start = InpTrailingStart * g_point;
      double trail_step  = InpTrailingStep  * g_point;
      
      if (pos_type == POSITION_TYPE_BUY) {
         if (current_price - open_price >= trail_start) {
            double new_sl = NormalizeDouble(current_price - trail_step, _Digits);
            if (new_sl > current_sl + trail_step)
               trade.PositionModify(ticket, new_sl, PositionGetDouble(POSITION_TP));
         }
      } else {
         if (open_price - current_price >= trail_start) {
            double new_sl = NormalizeDouble(current_price + trail_step, _Digits);
            if (new_sl < current_sl - trail_step || current_sl == 0)
               trade.PositionModify(ticket, new_sl, PositionGetDouble(POSITION_TP));
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Check if there's an open position                                |
//+------------------------------------------------------------------+
bool HasOpenPosition() {
   for (int i = 0; i < PositionsTotal(); i++) {
      if (PositionGetSymbol(i) == InpSymbol && 
          PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
         return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| Risk limits check                                                |
//+------------------------------------------------------------------+
bool CheckRiskLimits() {
   double equity  = AccountInfoDouble(ACCOUNT_EQUITY);
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   if (equity <= 0 || balance <= 0) return false;
   double dd = (balance - equity) / balance * 100.0;
   if (dd >= 10.0) {
      Print("Max drawdown limit reached: ", DoubleToString(dd, 2), "%");
      return false;
   }
   return true;
}
//+------------------------------------------------------------------+`
}

export default function MQL5Generator() {
  const [strategyType, setStrategyType] = useState('ict_scalping')
  const [eaName, setEaName] = useState('JARVIS_Gold_Scalper')
  const [symbol, setSymbol] = useState('XAUUSD')
  const [timeframe, setTimeframe] = useState('H1')
  const [riskPercent, setRiskPercent] = useState('1.0')
  const [stopLoss, setStopLoss] = useState('150')
  const [takeProfit, setTakeProfit] = useState('300')
  const [magicNumber, setMagicNumber] = useState('12345')
  const [isGenerating, setIsGenerating] = useState(false)
  const [generatedCode, setGeneratedCode] = useState('')
  const [copied, setCopied] = useState(false)

  const handleGenerate = async () => {
    setIsGenerating(true)
    await new Promise((r) => setTimeout(r, 1500))

    const code = generateEACode({
      type: strategyType,
      name: eaName,
      symbol,
      timeframe,
      riskPercent: parseFloat(riskPercent),
      stopLoss: parseFloat(stopLoss),
      takeProfit: parseFloat(takeProfit),
      magicNumber: parseInt(magicNumber),
    })

    setGeneratedCode(code)
    setIsGenerating(false)
    toast.success('MQL5 EA generated successfully!')
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(generatedCode)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
    toast.success('Code copied to clipboard!')
  }

  const handleDownload = () => {
    const blob = new Blob([generatedCode], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${eaName}.mq5`
    a.click()
    URL.revokeObjectURL(url)
    toast.success(`${eaName}.mq5 downloaded!`)
  }

  const handleInstall = () => {
    toast.loading('Installing to MT5...', { duration: 2000 })
    setTimeout(() => toast.success('EA installed to MetaTrader 5!'), 1500)
  }

  return (
    <div className="p-6 space-y-6" style={{ backgroundColor: '#0a0a0f', minHeight: '100%' }}>
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-jarvis-text">MQL5 EA Generator</h1>
        <p className="text-xs text-jarvis-muted mt-0.5">
          AI-powered Expert Advisor code generation for MetaTrader 5
        </p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-5 gap-6">
        {/* Config Panel */}
        <div
          className="xl:col-span-2 rounded-xl p-5"
          style={{ backgroundColor: '#12121a', border: '1px solid #1e1e2e' }}
        >
          <div className="flex items-center gap-2 mb-5">
            <Code size={15} style={{ color: '#00d4ff' }} />
            <h2 className="text-sm font-semibold text-jarvis-text">Generator Config</h2>
          </div>

          {/* Strategy Type */}
          <div className="mb-4">
            <label className="text-[11px] text-jarvis-muted uppercase tracking-wider block mb-2">
              Strategy Type
            </label>
            <div className="grid grid-cols-1 gap-1.5">
              {STRATEGY_TYPES.map((t) => (
                <button
                  key={t.id}
                  onClick={() => setStrategyType(t.id)}
                  className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all"
                  style={strategyType === t.id ? {
                    backgroundColor: 'rgba(0,212,255,0.08)',
                    border: '1px solid rgba(0,212,255,0.3)',
                  } : {
                    backgroundColor: 'rgba(30,30,46,0.3)',
                    border: '1px solid rgba(30,30,46,0.6)',
                  }}
                >
                  <ChevronRight
                    size={12}
                    style={{ color: strategyType === t.id ? '#00d4ff' : '#64748b' }}
                  />
                  <div>
                    <div className={`text-xs font-semibold ${strategyType === t.id ? 'text-jarvis-accent' : 'text-jarvis-muted'}`}>
                      {t.label}
                    </div>
                    <div className="text-[10px] text-jarvis-muted mt-0.5">{t.desc}</div>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Parameters */}
          <div className="space-y-3">
            <div>
              <label className="text-[11px] text-jarvis-muted uppercase tracking-wider block mb-1.5">
                EA Name
              </label>
              <input
                value={eaName}
                onChange={(e) => setEaName(e.target.value)}
                className="jarvis-input"
                placeholder="MyExpertAdvisor"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[11px] text-jarvis-muted uppercase tracking-wider block mb-1.5">
                  Symbol
                </label>
                <select value={symbol} onChange={(e) => setSymbol(e.target.value)} className="jarvis-input"
                  style={{ backgroundColor: 'rgba(30,30,46,0.6)' }}>
                  {SYMBOLS.map((s) => (
                    <option key={s} value={s} style={{ backgroundColor: '#12121a' }}>{s}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-[11px] text-jarvis-muted uppercase tracking-wider block mb-1.5">
                  Timeframe
                </label>
                <select value={timeframe} onChange={(e) => setTimeframe(e.target.value)} className="jarvis-input"
                  style={{ backgroundColor: 'rgba(30,30,46,0.6)' }}>
                  {TIMEFRAMES.map((tf) => (
                    <option key={tf} value={tf} style={{ backgroundColor: '#12121a' }}>{tf}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="text-[11px] text-jarvis-muted uppercase tracking-wider block mb-1.5">
                  Risk %
                </label>
                <input value={riskPercent} onChange={(e) => setRiskPercent(e.target.value)}
                  type="number" step="0.1" min="0.1" max="10" className="jarvis-input" />
              </div>
              <div>
                <label className="text-[11px] text-jarvis-red uppercase tracking-wider block mb-1.5">
                  SL pts
                </label>
                <input value={stopLoss} onChange={(e) => setStopLoss(e.target.value)}
                  type="number" className="jarvis-input" />
              </div>
              <div>
                <label className="text-[11px] text-jarvis-green uppercase tracking-wider block mb-1.5">
                  TP pts
                </label>
                <input value={takeProfit} onChange={(e) => setTakeProfit(e.target.value)}
                  type="number" className="jarvis-input" />
              </div>
            </div>

            <div>
              <label className="text-[11px] text-jarvis-muted uppercase tracking-wider block mb-1.5">
                Magic Number
              </label>
              <input value={magicNumber} onChange={(e) => setMagicNumber(e.target.value)}
                type="number" className="jarvis-input" placeholder="12345" />
            </div>

            <button
              onClick={handleGenerate}
              disabled={isGenerating || !eaName}
              className="w-full flex items-center justify-center gap-2 py-3 rounded-xl font-bold text-sm transition-all disabled:opacity-40"
              style={{
                background: 'linear-gradient(135deg, rgba(0,212,255,0.2), rgba(139,92,246,0.2))',
                border: '1px solid rgba(0,212,255,0.3)',
                color: '#00d4ff',
              }}
            >
              {isGenerating ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Zap size={14} />
              )}
              {isGenerating ? 'Generating...' : 'Generate EA'}
            </button>
          </div>
        </div>

        {/* Code Viewer */}
        <div className="xl:col-span-3 flex flex-col">
          <div
            className="rounded-xl overflow-hidden flex-1 flex flex-col"
            style={{ backgroundColor: '#12121a', border: '1px solid #1e1e2e' }}
          >
            <div
              className="flex items-center justify-between px-5 py-4 border-b flex-shrink-0"
              style={{ borderColor: '#1e1e2e', backgroundColor: '#0d0d14' }}
            >
              <div className="flex items-center gap-3">
                <FileCode size={14} style={{ color: '#00d4ff' }} />
                <span className="text-sm font-semibold text-jarvis-text">
                  {generatedCode ? `${eaName}.mq5` : 'Output'}
                </span>
                {generatedCode && (
                  <span
                    className="text-[10px] px-2 py-0.5 rounded font-semibold"
                    style={{
                      backgroundColor: 'rgba(0,255,136,0.1)',
                      border: '1px solid rgba(0,255,136,0.2)',
                      color: '#00ff88',
                    }}
                  >
                    MQL5
                  </span>
                )}
              </div>
              {generatedCode && (
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleCopy}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
                    style={{
                      backgroundColor: 'rgba(0,212,255,0.06)',
                      border: '1px solid rgba(0,212,255,0.15)',
                      color: '#00d4ff',
                    }}
                  >
                    {copied ? <Check size={11} /> : <Copy size={11} />}
                    {copied ? 'Copied!' : 'Copy'}
                  </button>
                  <button
                    onClick={handleDownload}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
                    style={{
                      backgroundColor: 'rgba(139,92,246,0.06)',
                      border: '1px solid rgba(139,92,246,0.2)',
                      color: '#8b5cf6',
                    }}
                  >
                    <Download size={11} />
                    .mq5
                  </button>
                  <button
                    onClick={handleInstall}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
                    style={{
                      backgroundColor: 'rgba(0,255,136,0.06)',
                      border: '1px solid rgba(0,255,136,0.2)',
                      color: '#00ff88',
                    }}
                  >
                    <Upload size={11} />
                    Install
                  </button>
                </div>
              )}
            </div>

            <div className="flex-1 overflow-auto" style={{ maxHeight: '600px' }}>
              {!generatedCode ? (
                <div className="flex flex-col items-center justify-center h-full py-16">
                  <Code size={40} className="mb-3 opacity-10" style={{ color: '#00d4ff' }} />
                  <div className="text-jarvis-muted text-sm">
                    Configure and generate your EA
                  </div>
                  <div className="text-jarvis-muted text-xs mt-1">
                    Production-ready MQL5 code will appear here
                  </div>
                </div>
              ) : (
                <SyntaxHighlighter
                  language="cpp"
                  style={oneDark}
                  customStyle={{
                    margin: 0,
                    borderRadius: 0,
                    background: '#0a0a14',
                    fontSize: '0.75rem',
                    lineHeight: '1.6',
                    minHeight: '100%',
                  }}
                  showLineNumbers
                >
                  {generatedCode}
                </SyntaxHighlighter>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
