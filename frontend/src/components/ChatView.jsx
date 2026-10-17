import React, { useState, useEffect, useRef } from 'react';
import { 
  Send, 
  Mic, 
  MicOff, 
  Volume2, 
  VolumeX, 
  ExternalLink, 
  Stethoscope, 
  Info,
  Loader2
} from 'lucide-react';
import { sendChatMessage } from '../api';

const LANGUAGE_SPEECH_MAP = {
  en: 'en-IN',
  hi: 'hi-IN',
  or: 'or-IN',
  bn: 'bn-IN',
  ta: 'ta-IN',
  te: 'te-IN',
  mr: 'mr-IN',
};

export default function ChatView({ detectedCondition, language = 'en', uiStrings = {} }) {
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      sender: 'assistant',
      text: detectedCondition
        ? `Hello! I have loaded context for ${detectedCondition.replace(/_/g, ' ')}. You can ask follow-up questions like 'Is it contagious?', 'What should I avoid?', or 'When to see a doctor?'.`
        : "Hello! Ask me any question about skin conditions, symptoms, first aid, or precautions. All answers are strictly grounded in verified clinical guidance from WHO, NHS, and AAD.",
      sources: [],
      grounded: true,
    }
  ]);
  const [inputText, setInputText] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [speakingId, setSpeakingId] = useState(null);
  const [voiceNotice, setVoiceNotice] = useState(null);
  const [activeContext, setActiveContext] = useState(detectedCondition);

  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);
  const msgCounterRef = useRef(1);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Web Speech API Voice Input Initialization
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = LANGUAGE_SPEECH_MAP[language] || 'en-IN';

      recognition.onstart = () => setIsListening(true);
      recognition.onend = () => setIsListening(false);
      recognition.onerror = (e) => {
        console.warn('Speech recognition error:', e);
        setIsListening(false);
      };
      recognition.onresult = (e) => {
        const transcript = e.results[0][0].transcript;
        if (transcript) {
          setInputText(transcript);
        }
      };
      recognitionRef.current = recognition;
    }
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
    };
  }, [language]);

  const toggleVoiceInput = () => {
    if (!recognitionRef.current) {
      setVoiceNotice("Speech recognition is not supported in this browser. Please type your question.");
      setTimeout(() => setVoiceNotice(null), 4000);
      return;
    }
    if (isListening) {
      recognitionRef.current.stop();
    } else {
      try {
        recognitionRef.current.lang = LANGUAGE_SPEECH_MAP[language] || 'en-IN';
        recognitionRef.current.start();
      } catch (e) {
        console.warn('Could not start speech recognition:', e);
      }
    }
  };

  // Web Speech API Read Aloud
  const speakText = (text, msgId) => {
    if (!window.speechSynthesis) {
      setVoiceNotice("Speech synthesis is not supported on this browser.");
      setTimeout(() => setVoiceNotice(null), 4000);
      return;
    }

    if (speakingId === msgId) {
      window.speechSynthesis.cancel();
      setSpeakingId(null);
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    const targetLang = LANGUAGE_SPEECH_MAP[language] || 'en-IN';
    utterance.lang = targetLang;

    // Check available voices
    const voices = window.speechSynthesis.getVoices();
    const matchedVoice = voices.find((v) => v.lang.startsWith(targetLang) || v.lang.startsWith(language));
    if (matchedVoice) {
      utterance.voice = matchedVoice;
    } else if (language !== 'en') {
      setVoiceNotice(uiStrings.chat_voice_missing || "Regional voice is not installed on this browser. Playing in default available voice.");
      setTimeout(() => setVoiceNotice(null), 4000);
    }

    utterance.onend = () => setSpeakingId(null);
    utterance.onerror = () => setSpeakingId(null);

    setSpeakingId(msgId);
    window.speechSynthesis.speak(utterance);
  };

  const handleSend = async (textToSend) => {
    const q = (textToSend || inputText).trim();
    if (!q || isSending) return;

    msgCounterRef.current += 1;
    const userMsg = { id: `u-${msgCounterRef.current}`, sender: 'user', text: q };
    setMessages((prev) => [...prev, userMsg]);
    setInputText('');
    setIsSending(true);

    try {
      const res = await sendChatMessage(q, activeContext, language);
      msgCounterRef.current += 1;
      const assistantMsg = {
        id: `a-${msgCounterRef.current}`,
        sender: 'assistant',
        text: res.answer,
        sources: res.sources || [],
        grounded: res.grounded,
        confidence: res.confidence,
        matchedCondition: res.matched_condition,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      msgCounterRef.current += 1;
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${msgCounterRef.current}`,
          sender: 'assistant',
          text: "I was unable to retrieve guidance right now. Please consult a qualified doctor for any medical questions.",
          sources: [],
          grounded: false,
        }
      ]);
    } finally {
      setIsSending(false);
    }
  };

  const quickPrompts = [
    activeContext ? `Is ${activeContext.replace(/_/g, ' ')} contagious?` : "Is ringworm contagious?",
    "What should I strictly avoid?",
    "What are the red flag warning signs?",
    "When should I see a doctor?",
  ];

  return (
    <div className="max-w-4xl mx-auto py-4 px-4 space-y-4 flex flex-col h-[82vh]">
      {/* Header bar */}
      <div className="bg-white border border-slate-200 rounded-3xl p-4 sm:p-5 shadow-sm flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-100 text-blue-700 rounded-2xl flex items-center justify-center font-bold">
            <Stethoscope className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-lg sm:text-xl font-bold text-slate-900">
              {uiStrings.chat_title || "Skin Health Assistant"}
            </h1>
            <p className="text-xs text-slate-500">
              {uiStrings.chat_subtitle || "Grounded strictly in WHO, NHS, and AAD medical guidance"}
            </p>
          </div>
        </div>

        {/* Active Context Badge */}
        {activeContext && (
          <div className="flex items-center gap-2 bg-blue-50 border border-blue-200 text-blue-900 px-3 py-1.5 rounded-xl text-xs font-semibold">
            <span>Context: {activeContext.replace(/_/g, ' ').toUpperCase()}</span>
            <button
              onClick={() => setActiveContext(null)}
              className="text-blue-600 hover:text-blue-900 font-bold ml-1 cursor-pointer"
              title="Clear photo context"
            >
              ✕
            </button>
          </div>
        )}
      </div>

      {/* Voice Warning Banner */}
      {voiceNotice && (
        <div 
          role="status" 
          aria-live="polite"
          className="bg-amber-100 border border-amber-300 text-amber-950 px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2"
        >
          <Info className="w-4 h-4 shrink-0 text-amber-700" />
          <span>{voiceNotice}</span>
        </div>
      )}

      {/* Machine translation note */}
      <div className="text-[11px] text-center text-slate-500 bg-slate-100 py-1 px-3 rounded-full border border-slate-200 w-fit mx-auto">
        ℹ️ {uiStrings.translation_badge || "Translations are machine-generated and need human review."}
      </div>

      {/* Message History Container */}
      <div 
        className="flex-1 overflow-y-auto bg-white border border-slate-200 rounded-3xl p-4 sm:p-6 space-y-4 shadow-sm"
        role="log"
        aria-label="Chat messages history"
      >
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex flex-col ${m.sender === 'user' ? 'items-end' : 'items-start'}`}
          >
            <div
              className={`max-w-[85%] sm:max-w-[75%] rounded-2xl p-4 text-sm sm:text-base leading-relaxed ${
                m.sender === 'user'
                  ? 'bg-blue-600 text-white rounded-br-none shadow-sm font-medium'
                  : 'bg-slate-50 border border-slate-200 text-slate-900 rounded-bl-none shadow-sm'
              }`}
            >
              <p>{m.text}</p>

              {/* Citations for grounded answers */}
              {m.sources && m.sources.length > 0 && (
                <div className="mt-3 pt-3 border-t border-slate-200/80 space-y-1.5">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">
                    Verified Citations:
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {m.sources.map((s, idx) => (
                      <a
                        key={idx}
                        href={s.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-[11px] font-bold bg-white text-blue-700 border border-blue-200 hover:bg-blue-50 px-2 py-0.5 rounded-lg"
                      >
                        <span>{s.title}</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    ))}
                  </div>
                </div>
              )}

              {/* Read Aloud Button for Assistant Messages */}
              {m.sender === 'assistant' && (
                <div className="mt-2.5 pt-2 flex items-center justify-between text-xs text-slate-500">
                  <button
                    onClick={() => speakText(m.text, m.id)}
                    className="inline-flex items-center gap-1.5 text-blue-600 hover:text-blue-800 font-bold bg-blue-50 hover:bg-blue-100 px-2.5 py-1 rounded-lg transition cursor-pointer"
                    aria-label={speakingId === m.id ? "Stop reading" : "Read aloud"}
                  >
                    {speakingId === m.id ? (
                      <>
                        <VolumeX className="w-3.5 h-3.5 text-red-600" />
                        <span className="text-red-600">Stop Voice</span>
                      </>
                    ) : (
                      <>
                        <Volume2 className="w-3.5 h-3.5" />
                        <span>{uiStrings.chat_read_aloud || "Read Aloud"}</span>
                      </>
                    )}
                  </button>
                  <span className="text-[10px] text-slate-400">
                    {m.grounded ? "✓ Verified RAG Match" : "Out of scope"}
                  </span>
                </div>
              )}
            </div>
          </div>
        ))}

        {isSending && (
          <div className="flex items-center gap-2 text-slate-500 text-xs sm:text-sm italic pl-2">
            <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
            <span>Searching verified clinical knowledge base...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick Prompts Pills */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
        {quickPrompts.map((p, idx) => (
          <button
            key={idx}
            onClick={() => handleSend(p)}
            className="whitespace-nowrap bg-white hover:bg-blue-50 border border-slate-200 hover:border-blue-300 text-slate-700 px-3 py-1.5 rounded-xl font-medium shadow-2xs transition cursor-pointer"
          >
            {p}
          </button>
        ))}
      </div>

      {/* Input Box with Voice & Send */}
      <div className="bg-white border border-slate-200 rounded-3xl p-2 sm:p-3 shadow-md flex items-center gap-2">
        <button
          type="button"
          onClick={toggleVoiceInput}
          className={`p-3 rounded-2xl transition cursor-pointer ${
            isListening
              ? 'bg-red-600 text-white animate-pulse'
              : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
          }`}
          aria-label={isListening ? "Stop listening" : "Start voice input"}
          title={isListening ? "Listening... click to stop" : "Speak your question"}
        >
          {isListening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
        </button>

        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder={
            isListening
              ? (uiStrings.chat_listening || "Listening... Speak now")
              : (uiStrings.chat_input_placeholder || "Ask a skin question (e.g. 'Is it contagious?')...")
          }
          className="flex-1 bg-transparent px-3 py-2 text-sm sm:text-base text-slate-900 focus:outline-none placeholder:text-slate-400"
          aria-label="Type your skin health question"
        />

        <button
          type="button"
          onClick={() => handleSend()}
          disabled={!inputText.trim() || isSending}
          className={`px-5 py-3 rounded-2xl font-bold flex items-center gap-2 transition ${
            !inputText.trim() || isSending
              ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700 text-white shadow-md cursor-pointer'
          }`}
          aria-label="Send message"
        >
          <span>{uiStrings.chat_send || "Send"}</span>
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
