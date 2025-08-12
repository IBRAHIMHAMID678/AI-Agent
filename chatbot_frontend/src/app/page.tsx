'use client'
import { useState, useRef, useEffect } from 'react'
import { Menu } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import './stars.css'

export default function Chatbot() {
  const [messages, setMessages] = useState([
    { sender: 'bot', text: 'Hello! How can I help you today?', isTyping: false }
  ])
  const [input, setInput] = useState("")
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [awaitingAction, setAwaitingAction] = useState<{ type: string; prompt?: string } | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  useEffect(() => {
    inputRef.current?.focus()
  }, [messages])

  const cleanTextForSpeech = (text: string): string => {
    return text
      .replace(/[\u{1F600}-\u{1F64F}]/gu, '')
      .replace(/[^\w\s.,?!]/g, '')
      .replace(/\/+/g, '')
      .trim()
  }

  const speakLastBotMessage = () => {
    const lastBotMessage = [...messages].reverse().find(msg => msg.sender === 'bot' && msg.text)
    if (lastBotMessage) {
      const cleaned = cleanTextForSpeech(lastBotMessage.text)
      const utterance = new SpeechSynthesisUtterance(cleaned)
      utterance.lang = 'en-US'
      speechSynthesis.speak(utterance)
    }
  }

  const sendMessage = async () => {
    if (input.trim() === '') return

    const userMessage = { sender: 'user', text: input, isTyping: false }
    setMessages(prev => [...prev, userMessage, { sender: 'bot', text: '', isTyping: true }])
    setInput('')
    setLoading(true)

    try {
      const response = await fetch('http://127.0.0.1:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_input: input }),
      })

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)

      const data = await response.json()
      const botReply = { sender: 'bot', text: data.response, isTyping: false }

      setMessages(prev => {
        const newMessages = prev.slice(0, -1)
        return [...newMessages, botReply]
      })
    } catch (error) {
      console.error("Failed to fetch from backend:", error)
      const errorReply = { sender: 'bot', text: 'Sorry, I am having trouble connecting to my brain.', isTyping: false }
      setMessages(prev => {
        const newMessages = prev.slice(0, -1)
        return [...newMessages, errorReply]
      })
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') sendMessage()
  }

  const startListening = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SpeechRecognition) {
      alert("Speech recognition not supported in this browser.")
      return
    }

    const recognition = new SpeechRecognition()
    recognition.lang = 'en-US'
    recognition.interimResults = false
    recognition.maxAlternatives = 1

    recognition.onresult = (event: any) => {
      const spokenText = event.results[0][0].transcript
      setInput(spokenText)
      sendMessage()
    }

    recognition.onerror = (event: any) => {
      console.error("Speech recognition error:", event.error)
    }

    recognition.start()
  }

  return (
    <main className="flex h-screen overflow-hidden relative font-sans text-white">
      {/* Animated background */}
      <div className="absolute inset-0 bg-gradient-to-br from-[#0f0024] via-[#2c015f] to-[#3e007e] overflow-hidden">
        <motion.div
          className="absolute w-[150%] h-[150%] bg-[radial-gradient(circle_at_center,_#ffffff0a_1px,_transparent_1px)]"
          animate={{ backgroundPosition: ['0% 0%', '100% 100%'] }}
          transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
        />
        <motion.div
          className="absolute inset-0 bg-gradient-to-t from-[#ff0080]/10 via-transparent to-[#00f0ff]/10"
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 8, repeat: Infinity }}
        />
        {/* Animated Stars */}
        <div className="stars">
          <div className="star" />
          <div className="star" />
          <div className="star" />
          <div className="star" />
          <div className="star" />
          <div className="star" />
          <div className="star" />
          <div className="star" />
        </div>
      </div>

      {/* Sidebar */}
      <aside className={`fixed z-40 h-full w-64 bg-white/10 backdrop-blur-lg shadow-2xl border-r border-white/20 p-5 transition-transform duration-300 rounded-r-3xl ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <h2 className="text-3xl font-bold mb-8 bg-gradient-to-r from-cyan-300 to-purple-400 text-transparent bg-clip-text animate-pulse">
          AI Nexus
        </h2>
        <ul className="space-y-4 text-lg">
          {['🏠 Home', '👤 Profile', '⚙️ Settings', '❓ Help'].map((item, i) => (
            <motion.li
              key={i}
              whileHover={{ scale: 1.05, x: 5 }}
              className="hover:bg-white/20 p-2 rounded-lg transition-all duration-200 cursor-pointer"
            >
              {item}
            </motion.li>
          ))}
        </ul>
        <div className="mt-auto text-sm text-white/60 pt-10">
          &copy; {new Date().getFullYear()} AI-ChatBOT. All rights reserved.
        </div>
      </aside>

      {/* Main */}
      <div className={`flex flex-col flex-1 transition-all duration-300 relative z-10 ${sidebarOpen ? 'ml-64' : 'ml-0'}`}>
        {/* Header */}
        <header className="flex items-center justify-between px-4 py-3 bg-white/10 backdrop-blur-lg border-b border-white/20 shadow-md">
          <motion.button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            whileTap={{ scale: 0.9 }}
            whileHover={{ rotate: 90 }}
            className="p-2 hover:bg-white/15 rounded-full transition"
          >
            <Menu className="text-blue-300 w-6 h-6" />
          </motion.button>
          <motion.h1
            className="text-3xl font-extrabold bg-gradient-to-r from-blue-300 to-pink-300 text-transparent bg-clip-text"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 1 }}
          >
            AI-ChatBOT 🚀
          </motion.h1>
          <div className="w-6 h-6" />
        </header>

        {/* Chat area */}
        <div className="flex-1 overflow-y-auto px-6 py-8 relative">
          <div className="space-y-5 max-w-2xl mx-auto relative z-10">
            <AnimatePresence>
              {messages.map((msg, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.3 }}
                  className={`flex gap-3 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {msg.sender === 'bot' && (
                    <motion.div
                      initial={{ rotate: -10 }}
                      animate={{ rotate: 0 }}
                      className="w-10 h-10 bg-gradient-to-br from-blue-400 to-purple-600 rounded-full flex items-center justify-center shadow-lg text-lg"
                    >
                      🤖
                    </motion.div>
                  )}
                  <motion.div
                    initial={{ scale: 0.8 }}
                    animate={{ scale: 1 }}
                    transition={{ type: 'spring', stiffness: 300 }}
                    className={`px-4 py-2 rounded-xl text-white max-w-[80%] shadow-lg ${msg.sender === 'user' ? 'bg-blue-600 rounded-br-none' : 'bg-white/10 border border-white/10 rounded-bl-none'}`}
                  >
                    {msg.text}
                  </motion.div>
                  {msg.sender === 'user' && (
                    <motion.div
                      initial={{ rotate: 10 }}
                      animate={{ rotate: 0 }}
                      className="w-10 h-10 bg-gradient-to-br from-green-400 to-teal-500 rounded-full flex items-center justify-center shadow-lg text-lg"
                    >
                      🧑
                    </motion.div>
                  )}
                </motion.div>
              ))}
            </AnimatePresence>
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input */}
        <footer className="p-4 bg-white/5 border-t border-white/10 backdrop-blur-md">
          <div className="max-w-2xl mx-auto flex gap-3">
            <input
              ref={inputRef}
              type="text"
              placeholder={awaitingAction ? `Awaiting ${awaitingAction.type.replace('_', ' ')}` : "Type your message..."}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
              className="flex-1 bg-white/10 text-white placeholder-gray-300 px-4 py-2.5 rounded-xl border border-white/20 focus:outline-none focus:ring-2 focus:ring-blue-400 transition"
            />
            <motion.button
              onClick={startListening}
              whileTap={{ scale: 0.9 }}
              whileHover={{ rotate: -10 }}
              className="bg-gradient-to-r from-yellow-400 to-orange-500 hover:from-yellow-500 hover:to-orange-600 text-white font-semibold px-4 py-2.5 rounded-xl shadow-lg transition-all duration-200"
            >
              🎙
            </motion.button>
            <motion.button
              onClick={speakLastBotMessage}
              whileTap={{ scale: 0.8 }}
              whileHover={{ rotate: 10 }}
              className="bg-gradient-to-r from-yellow-400 to-orange-500 hover:from-yellow-500 hover:to-orange-600 text-white font-semibold px-4 py-2.5 rounded-xl shadow-lg transition-all duration-200"
            >
              🔊
            </motion.button>
            <motion.button
              onClick={sendMessage}
              disabled={loading}
              whileTap={{ scale: 0.9 }}
              whileHover={{ rotate: 5 }}
              className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white font-semibold px-5 py-2.5 rounded-xl shadow-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "Sending..." : <>Send ➡️</>}
            </motion.button>
          </div>
        </footer>
      </div>
    </main>
  )
}
