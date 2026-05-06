"use client";

interface Message {
  id: string;
  type: "user" | "assistant";
  content: string;
  timestamp: Date;
}

export default function ChatMessage({ message }: { message: Message }) {
  const isUser = message.type === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-md rounded-2xl px-4 py-3 ${
          isUser
            ? "rounded-br-sm bg-slate-950 text-white"
            : "rounded-bl-sm border border-slate-200 bg-white text-slate-900 shadow-sm"
        }`}
      >
        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        <span className={`mt-2 block text-xs ${isUser ? "text-slate-300" : "text-slate-500"}`}>
          {message.timestamp.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}
        </span>
      </div>
    </div>
  );
}
