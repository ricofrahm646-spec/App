'use client'

import { Trade } from '@/types'
import { ArrowUpRight, ArrowDownRight, X } from 'lucide-react'
import clsx from 'clsx'
import { format, parseISO } from 'date-fns'
import toast from 'react-hot-toast'

interface OpenTradesTableProps {
  trades: Trade[]
  onClose: (ticket: number) => void
  isLoading?: boolean
}

export default function OpenTradesTable({ trades, onClose, isLoading }: OpenTradesTableProps) {
  const totalProfit = trades.reduce((sum, t) => sum + t.profit, 0)

  const handleClose = (ticket: number, symbol: string) => {
    toast((t) => (
      <div className="flex flex-col gap-3">
        <div className="text-sm font-semibold">Close trade #{ticket} ({symbol})?</div>
        <div className="flex gap-2">
          <button
            className="px-3 py-1.5 rounded text-xs font-semibold"
            style={{
              backgroundColor: 'rgba(255,51,102,0.2)',
              border: '1px solid rgba(255,51,102,0.4)',
              color: '#ff3366',
            }}
            onClick={() => {
              onClose(ticket)
              toast.dismiss(t.id)
              toast.success(`Trade #${ticket} closed`)
            }}
          >
            Confirm Close
          </button>
          <button
            className="px-3 py-1.5 rounded text-xs font-semibold text-jarvis-muted"
            style={{ backgroundColor: 'rgba(30,30,46,0.8)', border: '1px solid rgba(30,30,46,0.8)' }}
            onClick={() => toast.dismiss(t.id)}
          >
            Cancel
          </button>
        </div>
      </div>
    ), { duration: 10000 })
  }

  return (
    <div
      className="rounded-xl overflow-hidden"
      style={{ backgroundColor: '#12121a', border: '1px solid #1e1e2e' }}
    >
      <div
        className="flex items-center justify-between px-5 py-4 border-b"
        style={{ borderColor: '#1e1e2e' }}
      >
        <div>
          <h2 className="text-sm font-semibold text-jarvis-text">Open Positions</h2>
          <p className="text-[11px] text-jarvis-muted mt-0.5">
            {trades.length} active trade{trades.length !== 1 ? 's' : ''}
          </p>
        </div>
        <div
          className={clsx(
            'text-sm font-bold font-mono px-3 py-1.5 rounded-lg',
          )}
          style={{
            backgroundColor: totalProfit >= 0 ? 'rgba(0,255,136,0.1)' : 'rgba(255,51,102,0.1)',
            border: totalProfit >= 0 ? '1px solid rgba(0,255,136,0.2)' : '1px solid rgba(255,51,102,0.2)',
            color: totalProfit >= 0 ? '#00ff88' : '#ff3366',
          }}
        >
          {totalProfit >= 0 ? '+' : ''}${totalProfit.toFixed(2)}
        </div>
      </div>

      {trades.length === 0 ? (
        <div className="py-12 text-center">
          <div className="text-jarvis-muted text-sm">No open positions</div>
          <div className="text-jarvis-muted text-xs mt-1">Place an order to see it here</div>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="jarvis-table">
            <thead>
              <tr>
                <th>Ticket</th>
                <th>Symbol</th>
                <th>Type</th>
                <th>Lots</th>
                <th>Open</th>
                <th>Current</th>
                <th>SL</th>
                <th>TP</th>
                <th>P&amp;L</th>
                <th>Time</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {trades.map((trade) => (
                <tr key={trade.ticket}>
                  <td className="font-mono text-jarvis-muted">#{trade.ticket}</td>
                  <td className="font-bold text-jarvis-text">{trade.symbol}</td>
                  <td>
                    <span
                      className="inline-flex items-center gap-0.5 px-2 py-0.5 rounded text-[10px] font-bold"
                      style={{
                        backgroundColor: trade.type === 'BUY'
                          ? 'rgba(0,255,136,0.1)'
                          : 'rgba(255,51,102,0.1)',
                        color: trade.type === 'BUY' ? '#00ff88' : '#ff3366',
                      }}
                    >
                      {trade.type === 'BUY' ? (
                        <ArrowUpRight size={10} />
                      ) : (
                        <ArrowDownRight size={10} />
                      )}
                      {trade.type}
                    </span>
                  </td>
                  <td className="font-mono text-jarvis-text">{trade.lots.toFixed(2)}</td>
                  <td className="font-mono text-jarvis-muted">{trade.openPrice.toFixed(5)}</td>
                  <td className="font-mono font-semibold text-jarvis-text">{trade.currentPrice.toFixed(5)}</td>
                  <td className="font-mono text-jarvis-red">{trade.stopLoss > 0 ? trade.stopLoss.toFixed(5) : '-'}</td>
                  <td className="font-mono text-jarvis-green">{trade.takeProfit > 0 ? trade.takeProfit.toFixed(5) : '-'}</td>
                  <td
                    className="font-bold font-mono"
                    style={{ color: trade.profit >= 0 ? '#00ff88' : '#ff3366' }}
                  >
                    {trade.profit >= 0 ? '+' : ''}${trade.profit.toFixed(2)}
                  </td>
                  <td className="text-jarvis-muted text-[11px]">
                    {format(parseISO(trade.openTime), 'HH:mm')}
                  </td>
                  <td>
                    <button
                      onClick={() => handleClose(trade.ticket, trade.symbol)}
                      className="flex items-center justify-center w-6 h-6 rounded transition-all hover:scale-110"
                      style={{
                        backgroundColor: 'rgba(255,51,102,0.1)',
                        border: '1px solid rgba(255,51,102,0.2)',
                        color: '#ff3366',
                      }}
                      title="Close trade"
                    >
                      <X size={11} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
