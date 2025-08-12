'use client';

import { useState, useRef } from 'react';


declare global {
  interface Window {
    webkitSpeechRecognition: any;
    SpeechRecognition: any;
  }
}

type CustomRecognitionEvent = Event & {
  results: SpeechRecognitionResultList;
};

type CustomRecognitionErrorEvent = Event & {
  error: string;
};

export default function ChatComponent() {
  const [input, setInput] = useState('');
  const [response, setResponse] = useState('');
  const recognitionRef = useRef<any>(null);

  const speak = (text: string) => {
    const utterance = new SpeechSynthesisUtterance(text);
    speechSynthesis.speak(utterance);
  };

  const sendMessage = async () => {
    const res = await fetch('http://127.0.0.1:8000/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message: input }),
    });

    const data = await res.json();
    setResponse(data.response);
    speak(data.response);
  };

  const startListening = () => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert('Speech Recognition is not supported in this browser.');
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event: CustomRecognitionEvent) => {
      const transcript = event.results[0][0].transcript;
      setInput(transcript); // Automatically fill input
    };

    recognition.onerror = (event: CustomRecognitionErrorEvent) => {
      console.error('Speech recognition error:', event.error);
    };

    recognition.start();
    recognitionRef.current = recognition;
  };

  return (
    <div className="p-4">
      <div className="flex space-x-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          className="border px-2 py-1 flex-grow"
          placeholder="Ask something..."
        />
        <button
          onClick={startListening}
          className="bg-green-500 text-white px-3 py-1"
          title="Speak"
        >
          🎤
        </button>
        <button
          onClick={sendMessage}
          className="bg-blue-500 text-white px-4 py-1"
          title="Send"
        >
          Send
        </button>
      </div>

      <div className="mt-4">
        <strong>Bot:</strong> {response}
      </div>
    </div>
  );
}
