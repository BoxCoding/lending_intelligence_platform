"use client";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Send } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense, useRef, useState } from "react";
import { api, ChatTurn } from "@/lib/api";
import { Spinner } from "@/components/ui";

export default function ChatPage() {
  return (
    <Suspense fallback={<Spinner />}>
      <Chat />
    </Suspense>
  );
}

function Chat() {
  const params = useSearchParams();
  const [customerId, setCustomerId] = useState(params.get("customer") ?? "");
  const [messages, setMessages] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState("");
  const [suggestions, setSuggestions] = useState<string[]>([
    "Explain the income estimation", "What loan products fit best?", "Any fraud indicators?",
  ]);
  const bottomRef = useRef<HTMLDivElement>(null);

  const { data: dash } = useQuery({ queryKey: ["dashboard"], queryFn: api.dashboard });

  const mutation = useMutation({
    mutationFn: (message: string) => api.chat(message, customerId || undefined, messages),
    onSuccess: (res) => {
      setMessages((m) => [...m, { role: "model", content: res.reply }]);
      if (res.suggestions?.length) setSuggestions(res.suggestions);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    },
    onError: (e: Error) =>
      setMessages((m) => [...m, { role: "model", content: `⚠️ ${e.message}` }]),
  });

  const send = (text: string) => {
    if (!text.trim() || mutation.isPending) return;
    setMessages((m) => [...m, { role: "user", content: text }]);
    mutation.mutate(text);
    setInput("");
  };

  return (
    <div className="mx-auto flex h-[calc(100vh-8rem)] max-w-3xl flex-col">
      <div className="mb-3 flex items-center gap-3">
        <h1 className="text-xl font-bold">AI Financial Advisor</h1>
        <select value={customerId} onChange={(e) => { setCustomerId(e.target.value); setMessages([]); }}
          className="ml-auto rounded-lg border border-border bg-surface px-3 py-1.5 text-sm outline-none focus:border-primary">
          <option value="">No customer context</option>
          {dash?.leads.map((l) => (
            <option key={l.customer_id} value={l.customer_id}>{l.name} ({l.customer_id})</option>
          ))}
        </select>
      </div>

      <div className="card flex-1 space-y-4 overflow-y-auto">
        {messages.length === 0 && (
          <p className="py-10 text-center text-sm text-muted">
            Ask about income estimation, repayment capacity, lead scores, risk, or loan recommendations.
            {customerId ? ` Context: ${customerId}` : " Select a customer for grounded answers."}
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`max-w-[85%] whitespace-pre-wrap rounded-xl px-4 py-3 text-sm leading-relaxed ${
            m.role === "user" ? "ml-auto bg-primary/20" : "bg-surface"
          }`}>
            {m.content}
          </div>
        ))}
        {mutation.isPending && <p className="animate-pulse text-sm text-muted">Advisor is thinking…</p>}
        <div ref={bottomRef} />
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {suggestions.map((s) => (
          <button key={s} onClick={() => send(s)}
            className="rounded-full border border-border px-3 py-1 text-xs text-muted transition hover:border-primary hover:text-zinc-100">
            {s}
          </button>
        ))}
      </div>

      <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="mt-3 flex gap-2">
        <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask the advisor…"
          className="flex-1 rounded-lg border border-border bg-surface px-4 py-3 text-sm outline-none focus:border-primary" />
        <button type="submit" disabled={mutation.isPending}
          className="rounded-lg bg-primary px-4 font-semibold transition hover:bg-primary/85 disabled:opacity-50">
          <Send size={18} />
        </button>
      </form>
    </div>
  );
}
