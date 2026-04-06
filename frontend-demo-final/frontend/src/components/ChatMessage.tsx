import { BrainCircuit, User } from "lucide-react";
interface Props { role: "user" | "assistant"; content: string; timestamp?: string; }
export default function ChatMessage({ role, content, timestamp }: Props) {
  const u = role === "user";
  return <div className={`flex gap-3 ${u ? "flex-row-reverse" : ""}`}>
    <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${u ? "bg-indigo-100 text-indigo-600" : "bg-gray-100 text-gray-600"}`}>
      {u ? <User className="h-4 w-4" /> : <BrainCircuit className="h-4 w-4" />}
    </div>
    <div className={`max-w-[75%] ${u ? "text-right" : ""}`}>
      <div className={`inline-block px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${u ? "bg-indigo-600 text-white rounded-br-md" : "bg-gray-100 text-gray-800 rounded-bl-md"}`}>{content}</div>
      {timestamp && <p className="text-[10px] text-gray-400 mt-1 px-1">{timestamp}</p>}
    </div>
  </div>;
}
