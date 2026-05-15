import React from 'react';

const App: React.FC = () => {
  return (
    <div className="min-h-screen bg-omega-black text-white p-8">
      <header className="border-b border-cyber-red pb-4 mb-8">
        <h1 className="text-4xl font-bold text-cyber-red tracking-widest">JARVIS V9000</h1>
        <p className="text-gray-400">Aethelgard Omega Trading Interface</p>
      </header>
      <main className="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div className="bg-gray-900 border border-gray-800 p-6 rounded-lg">
          <h2 className="text-xl mb-4 border-b border-cyber-red/30 pb-2">Telemetry</h2>
          <div className="space-y-2">
            <div className="flex justify-between"><span>Balance:</span><span className="text-green-500">$10,420.50</span></div>
            <div className="flex justify-between"><span>Equity:</span><span className="text-blue-500">$10,420.50</span></div>
            <div className="flex justify-between"><span>Drawdown:</span><span className="text-red-500">0.00%</span></div>
          </div>
        </div>
        <div className="md:col-span-2 bg-gray-900 border border-gray-800 p-6 rounded-lg h-96">
          <h2 className="text-xl mb-4 border-b border-cyber-red/30 pb-2">Neural Terminal</h2>
          <div className="bg-black p-4 rounded h-64 font-mono text-sm overflow-y-auto">
            <p className="text-green-400">> System initialized...</p>
            <p className="text-green-400">> Neural God Protocol: Online</p>
            <p className="text-cyber-red animate-pulse">> Ready for command.</p>
          </div>
          <input
            type="text"
            placeholder="Baue einen neuen Gold-Scalping-Bot..."
            className="w-full mt-4 bg-gray-800 border border-gray-700 p-2 rounded focus:border-cyber-red outline-none"
          />
        </div>
      </main>
    </div>
  );
};

export default App;
