import { useState, useRef, useEffect, useCallback } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { AIQueryResponse, AIInsight } from "@/types";
import {
    Bot, Orbit, Send, User, Trash2, Lightbulb, Sparkles,
    AlertTriangle, CheckCircle2, Info, XCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface Message {
    role: "user" | "assistant";
    content: string;
    tokens?: number;
    streaming?: boolean;
}

const SUGGESTED_QUERIES = [
    "Care este situația financiară a firmei cu CUI 12345678?",
    "Compară firmele cu CUI 1234 și 5678 pe indicatori cheie",
    "Ce scor ESG are firma cu CUI 12345678?",
    "Arată dosarele judiciare pentru CUI 12345678",
    "Ce contracte publice are firma cu CUI 12345678?",
    "Curs BNR EUR astăzi?",
];

export default function AIAgentPage() {
    const [messages, setMessages] = useState<Message[]>([
        {
            role: "assistant",
            content:
                "Bună! Sunt agentul AI al platformei RomBiz. Pot căuta companii, analiza date financiare, scoruri de risc și ESG, dosare judiciare, contracte publice, asociați și cursuri BNR. Ce dorești să afli?",
        },
    ]);
    const [input, setInput] = useState("");
    const [isStreaming, setIsStreaming] = useState(false);
    const [useStreamMode, setUseStreamMode] = useState(false);
    const [insightCui, setInsightCui] = useState("");
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // 9.5: Proactive insights query
    const { data: insights } = useQuery<{ insights: AIInsight[] }>({
        queryKey: ["ai-insights", insightCui],
        queryFn: async () => {
            const { data } = await api.get(`/ai/insights/${insightCui}`);
            return data;
        },
        enabled: !!insightCui && insightCui.length >= 4,
    });

    // Non-streaming query
    const queryMutation = useMutation({
        mutationFn: async (query: string) => {
            const { data } = await api.post<AIQueryResponse>("/ai/query", null, {
                params: { question: query },
            });
            return data;
        },
        onSuccess: (data) => {
            setMessages((prev) => [
                ...prev,
                {
                    role: "assistant",
                    content: data.answer,
                    tokens: data.tokens_used,
                },
            ]);
        },
        onError: () => {
            setMessages((prev) => [
                ...prev,
                {
                    role: "assistant",
                    content: "Îmi pare rău, a apărut o eroare. Te rog să încerci din nou.",
                },
            ]);
        },
    });

    // 9.2: Streaming query
    const streamQuery = useCallback(async (query: string) => {
        setIsStreaming(true);
        setMessages((prev) => [
            ...prev,
            { role: "assistant", content: "", streaming: true },
        ]);

        try {
            const token = localStorage.getItem("access_token");
            const baseUrl = api.defaults.baseURL || "";
            const params = new URLSearchParams({ question: query });
            const res = await fetch(`${baseUrl}/ai/stream?${params}`, {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${token}`,
                    "Content-Type": "application/json",
                },
            });

            if (!res.ok) throw new Error("Stream failed");

            const reader = res.body?.getReader();
            const decoder = new TextDecoder();
            let accumulated = "";

            if (reader) {
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    const chunk = decoder.decode(value, { stream: true });
                    const lines = chunk.split("\n");
                    for (const line of lines) {
                        if (line.startsWith("data: ")) {
                            const payload = line.slice(6);
                            if (payload === "[DONE]") break;
                            try {
                                const parsed = JSON.parse(payload);
                                if (parsed.text) {
                                    accumulated += parsed.text;
                                    setMessages((prev) => {
                                        const copy = [...prev];
                                        const last = copy[copy.length - 1];
                                        if (last?.streaming) {
                                            copy[copy.length - 1] = {
                                                ...last,
                                                content: accumulated,
                                            };
                                        }
                                        return copy;
                                    });
                                }
                                if (parsed.status === "processing_tools") {
                                    accumulated += "\n\n🔧 _Se procesează datele..._\n\n";
                                }
                            } catch {
                                // skip invalid JSON lines
                            }
                        }
                    }
                }
            }

            // Finalize
            setMessages((prev) => {
                const copy = [...prev];
                const last = copy[copy.length - 1];
                if (last?.streaming) {
                    copy[copy.length - 1] = { ...last, streaming: false };
                }
                return copy;
            });
        } catch {
            setMessages((prev) => [
                ...prev.filter((m) => !m.streaming),
                {
                    role: "assistant",
                    content: "Eroare la streaming. Încearcă din nou.",
                },
            ]);
        } finally {
            setIsStreaming(false);
        }
    }, [messages.length]);

    const handleSend = (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim()) return;

        const userMessage = input.trim();
        setInput("");
        setMessages((prev) => [...prev, { role: "user", content: userMessage }]);

        if (useStreamMode) {
            streamQuery(userMessage);
        } else {
            queryMutation.mutate(userMessage);
        }
    };

    const handleSuggestion = (q: string) => {
        setInput(q);
    };

    // 9.3: Clear conversation
    const clearConversation = async () => {
        try {
            await api.delete("/ai/conversation");
        } catch {
            // ignore
        }
        setMessages([
            {
                role: "assistant",
                content: "Conversația a fost resetată. Cu ce te pot ajuta?",
            },
        ]);
    };

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const isBusy = queryMutation.isPending || isStreaming;

    const insightIcon = (type: AIInsight["type"]) => {
        switch (type) {
            case "positive": return <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
            case "warning": return <AlertTriangle className="h-4 w-4 text-amber-500" />;
            case "danger": return <XCircle className="h-4 w-4 text-red-500" />;
            default: return <Info className="h-4 w-4 text-blue-500" />;
        }
    };

    return (
        <div className="flex h-[calc(100vh-10rem)] flex-col">
            <div className="section-header mb-4 flex items-center justify-between">
                <div>
                    <h1 className="font-orbitron text-2xl font-bold tracking-wide text-nebula">AI Agent</h1>
                    <p className="mt-1 font-rajdhani text-sm uppercase tracking-wider text-slate-400">
                        Întreabă despre companii, date financiare, ESG, dosare sau contracte
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    <label className="flex items-center gap-2 text-xs text-slate-400">
                        <input
                            type="checkbox"
                            checked={useStreamMode}
                            onChange={(e) => setUseStreamMode(e.target.checked)}
                            className="rounded"
                        />
                        Streaming
                    </label>
                    <button
                        onClick={clearConversation}
                        className="flex items-center gap-1 rounded-lg border border-red-500/30 px-3 py-1.5 text-xs text-red-400 hover:bg-red-500/10"
                        title="Resetează conversația"
                    >
                        <Trash2 className="h-3.5 w-3.5" />
                        Reset
                    </button>
                </div>
            </div>

            <div className="flex flex-1 gap-4 overflow-hidden">
                {/* Messages */}
                <div className="card-cosmic flex-1 overflow-y-auto">
                    <div className="space-y-4">
                        {messages.map((msg, i) => (
                            <div
                                key={i}
                                className={cn(
                                    "flex gap-3",
                                    msg.role === "user" && "flex-row-reverse"
                                )}
                            >
                                <div
                                    className={cn(
                                        "flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full",
                                        msg.role === "assistant"
                                            ? "bg-nebula-gradient text-white"
                                            : "bg-dragon-gradient text-white"
                                    )}
                                >
                                    {msg.role === "assistant" ? (
                                        <Bot className="h-4 w-4" />
                                    ) : (
                                        <User className="h-4 w-4" />
                                    )}
                                </div>
                                <div
                                    className={cn(
                                        "max-w-[80%] rounded-xl px-4 py-2.5",
                                        msg.role === "assistant"
                                            ? "bg-nebula-50/60 border border-nebula-100"
                                            : "bg-nebula-gradient text-white"
                                    )}
                                >
                                    <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
                                    {msg.streaming && (
                                        <span className="inline-block h-4 w-1 animate-pulse bg-nebula-400 ml-0.5" />
                                    )}
                                    {msg.tokens && (
                                        <p className="mt-1 text-[10px] text-slate-400">
                                            {msg.tokens.toLocaleString()} tokens
                                        </p>
                                    )}
                                </div>
                            </div>
                        ))}

                        {queryMutation.isPending && !isStreaming && (
                            <div className="flex gap-3">
                                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-nebula-gradient text-white">
                                    <Bot className="h-4 w-4" />
                                </div>
                                <div className="rounded-xl bg-nebula-50/60 border border-nebula-100 px-4 py-2.5">
                                    <Orbit className="h-4 w-4 animate-pulse text-nebula-400" />
                                </div>
                            </div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>
                </div>

                {/* Sidebar: Suggestions + Insights */}
                <div className="hidden w-72 flex-col gap-4 lg:flex">
                    {/* Suggested queries */}
                    <div className="card-cosmic p-4">
                        <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-nebula">
                            <Sparkles className="h-4 w-4" />
                            Sugestii
                        </h3>
                        <div className="space-y-2">
                            {SUGGESTED_QUERIES.map((q, i) => (
                                <button
                                    key={i}
                                    onClick={() => handleSuggestion(q)}
                                    className="w-full rounded-lg border border-slate-200/50 px-3 py-2 text-left text-xs text-slate-600 transition hover:border-nebula-200 hover:bg-nebula-50/30"
                                >
                                    {q}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Insights */}
                    <div className="card-cosmic p-4">
                        <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-nebula">
                            <Lightbulb className="h-4 w-4" />
                            Insights rapide
                        </h3>
                        <div className="mb-3">
                            <input
                                type="text"
                                value={insightCui}
                                onChange={(e) => setInsightCui(e.target.value.replace(/\D/g, ""))}
                                placeholder="Introdu CUI..."
                                className="input-scifi w-full text-xs"
                            />
                        </div>
                        {insights?.insights?.length ? (
                            <div className="space-y-2">
                                {insights.insights.map((ins, i) => (
                                    <div key={i} className="flex items-start gap-2 rounded-lg border border-slate-200/50 p-2">
                                        {insightIcon(ins.type)}
                                        <div>
                                            <p className="text-xs font-semibold">{ins.title}</p>
                                            <p className="text-[11px] text-slate-500">{ins.text}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : insightCui.length >= 4 ? (
                            <p className="text-xs text-slate-400">Nu sunt insights disponibile.</p>
                        ) : null}
                    </div>
                </div>
            </div>

            {/* Input */}
            <form onSubmit={handleSend} className="mt-4 flex gap-2">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Întreabă ceva... (ex: Care este scorul de risc pentru CUI 12345678?)"
                    className="input-scifi flex-1"
                    disabled={isBusy}
                />
                <button
                    type="submit"
                    disabled={!input.trim() || isBusy}
                    className="btn-cosmic px-4 py-3 disabled:opacity-50"
                >
                    <Send className="h-5 w-5" />
                </button>
            </form>
        </div>
    );
}
