import type { TradeSnapshot } from "@/lib/api";

type TradeTableProps = {
  trades: TradeSnapshot[];
};

export function TradeTable({ trades }: TradeTableProps) {
  if (!trades.length) {
    return (
      <div className="rounded-2xl border border-dashed border-white/10 bg-slate-950/40 p-6 text-sm text-slate-400">
        No live trades are active. JARVIS currently enforces a one-trade maximum and starts in paper mode.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-white/10">
      <table className="min-w-full divide-y divide-white/10 text-sm">
        <thead className="bg-white/5 text-left text-slate-300">
          <tr>
            <th className="px-4 py-3">Symbol</th>
            <th className="px-4 py-3">Direction</th>
            <th className="px-4 py-3">Entry</th>
            <th className="px-4 py-3">SL</th>
            <th className="px-4 py-3">TP</th>
            <th className="px-4 py-3">Strategy</th>
            <th className="px-4 py-3">State</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/10 bg-slate-950/60 text-slate-200">
          {trades.map((trade) => (
            <tr key={`${trade.symbol}-${trade.strategy}-${trade.state}`}>
              <td className="px-4 py-3">{trade.symbol}</td>
              <td className="px-4 py-3 uppercase">{trade.direction}</td>
              <td className="px-4 py-3">{trade.entry_price}</td>
              <td className="px-4 py-3">{trade.stop_loss}</td>
              <td className="px-4 py-3">{trade.take_profit}</td>
              <td className="px-4 py-3">{trade.strategy}</td>
              <td className="px-4 py-3 capitalize">{trade.state}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
