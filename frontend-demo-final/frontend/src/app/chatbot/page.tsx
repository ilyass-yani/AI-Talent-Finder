"use client";
import { useState } from "react";
import Layout from "@/components/Layout";
import ChatMessage from "@/components/ChatMessage";
import { Send } from "lucide-react";
interface Msg { role: "user"|"assistant"; content: string; timestamp: string; }
const now = () => new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
export default function ChatbotPage() {
  const [msgs, setMsgs] = useState<Msg[]>([{ role: "assistant", content: "Bonjour ! Je suis l'assistant IA. Posez-moi des questions sur vos candidats, demandez des comparaisons ou décrivez le profil idéal.", timestamp: now() }]);
  const [input, setInput] = useState(""); const [loading, setLoading] = useState(false);
  const send = async () => {
    if (!input.trim()||loading) return; setMsgs(p => [...p, { role: "user", content: input.trim(), timestamp: now() }]); setInput(""); setLoading(true);
    setTimeout(() => { setMsgs(p => [...p, { role: "assistant", content: "Cette fonctionnalité sera connectée au backend FastAPI et à l'API LLM. Le frontend est prêt à recevoir les réponses.", timestamp: now() }]); setLoading(false); }, 1000);
  };
  return <Layout><div className="max-w-3xl mx-auto flex flex-col h-[calc(100vh-8rem)]">
    <div className="mb-4"><h1 className="text-2xl font-bold text-gray-900">Chatbot IA</h1><p className="text-sm text-gray-500 mt-1">Posez des questions, comparez des candidats ou générez un profil idéal</p></div>
    <div className="flex-1 overflow-y-auto space-y-4 bg-white rounded-xl border border-gray-200 p-6 mb-4">
      {msgs.map((m, i) => <ChatMessage key={i} {...m} />)}
      {loading && <div className="flex gap-3"><div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center"><div className="flex gap-1"><span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{animationDelay:"0ms"}} /><span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{animationDelay:"150ms"}} /><span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{animationDelay:"300ms"}} /></div></div></div>}
    </div>
    <div className="flex items-center gap-2 bg-white border border-gray-300 rounded-xl px-4 py-3">
      <input type="text" value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key==="Enter" && send()} placeholder="Ex: Compare Ahmed et Sara, Qui maîtrise Python ?" className="flex-1 text-sm outline-none" />
      <button onClick={send} disabled={!input.trim()||loading} className="p-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"><Send className="h-4 w-4" /></button>
    </div>
  </div></Layout>;
}
