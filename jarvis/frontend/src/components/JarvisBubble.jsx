import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageSquare, TrendingUp, Code, Monitor, Send, Loader2 } from 'lucide-react';
import axios from 'axios';

const JarvisBubble = () => {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([
    { role: 'jarvis', content: 'System online. JARVIS at your service.' }
  ]);
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMsg = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const response = await axios.post('http://localhost:8000/chat', { message: input });
      setMessages(prev => [...prev, { role: 'jarvis', content: response.data.response, agent: response.data.agent }]);
    } catch (error) {
      setMessages(prev => [...prev, { role: 'jarvis', content: 'Error connecting to core systems.' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed bottom-10 right-10 flex flex-col items-end">
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.8, y: 20 }}
            className="glass w-96 h-[500px] rounded-3xl mb-6 p-6 flex flex-col shadow-2xl overflow-hidden relative"
          >
            {/* HUD Elements */}
            <div className="absolute top-2 left-1/2 -translate-x-1/2 text-[10px] text-jarvis-blue opacity-50 tracking-[0.2em]">
              SYSTEM INTERFACE V4.2
            </div>

            <div className="flex-1 overflow-y-auto space-y-4 pr-2 scrollbar-hide">
              {messages.map((msg, i) => (
                <motion.div
                  key={i}
                  initial={{ x: msg.role === 'user' ? 20 : -20, opacity: 0 }}
                  animate={{ x: 0, opacity: 1 }}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`max-w-[80%] p-3 rounded-2xl text-sm ${
                    msg.role === 'user'
                    ? 'bg-jarvis-blue/20 text-white'
                    : 'bg-white/5 text-jarvis-blue border border-jarvis-blue/30'
                  }`}>
                    {msg.content}
                    {msg.agent && (
                        <div className="text-[8px] mt-1 uppercase opacity-50 flex items-center gap-1">
                            {msg.agent === 'trading' && <TrendingUp size={8}/>}
                            {msg.agent === 'coding' && <Code size={8}/>}
                            {msg.agent === 'system' && <Monitor size={8}/>}
                            {msg.agent}
                        </div>
                    )}
                  </div>
                </motion.div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <Loader2 className="animate-spin text-jarvis-blue" size={20} />
                </div>
              )}
            </div>

            <div className="mt-4 flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                placeholder="Talk to JARVIS..."
                className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-sm focus:outline-none focus:border-jarvis-blue"
              />
              <button
                onClick={handleSend}
                className="bg-jarvis-blue/20 hover:bg-jarvis-blue/40 text-jarvis-blue p-2 rounded-xl transition-colors"
              >
                <Send size={18} />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <motion.div
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        onClick={() => setIsOpen(!isOpen)}
        className="w-20 h-20 rounded-full cursor-pointer flex items-center justify-center relative"
      >
        {/* Animated Glow Rings */}
        <motion.div
            animate={{ scale: [1, 1.2, 1], opacity: [0.3, 0.1, 0.3] }}
            transition={{ repeat: Infinity, duration: 2 }}
            className="absolute inset-0 bg-jarvis-blue rounded-full blur-xl"
        />

        <div className="w-16 h-16 rounded-full border-2 border-jarvis-blue flex items-center justify-center bg-jarvis-dark relative z-10 overflow-hidden">
            <motion.div
                animate={{ rotate: 360 }}
                transition={{ repeat: Infinity, duration: 8, ease: "linear" }}
                className="absolute inset-0 border-t-2 border-jarvis-blue/40 rounded-full"
            />
            <MessageSquare className="text-jarvis-blue" size={24} />
        </div>
      </motion.div>
    </div>
  );
};

export default JarvisBubble;
