"use client";
import { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkBreaks from "remark-breaks";
import Sidebar from "@/components/Sidebar";
import { Send, Bot, User, BookOpen, Layers, ChevronDown, Check } from "lucide-react";
import Image from "next/image";

interface Message {
  role: string;
  content: string;
}

interface Conversation {
  id: string;
  name: string;
  messages: Message[];
  subject: string;
  lesson: string;
}

const STORAGE_KEY_CONVS = "edugenius_active_conversations";
const STORAGE_KEY_ACTIVE_ID = "edugenius_active_conv_id";

const DEFAULT_CONVERSATIONS: Conversation[] = [
  {
    id: "init-conv-1",
    name: "New Study Session",
    messages: [],
    subject: "All",
    lesson: "All",
  },
];

export default function ChatPage() {
  const [isMounted, setIsMounted] = useState(false);
  const [metadata, setMetadata] = useState<Record<string, string[]>>({});
  const [subject, setSubject] = useState("All");
  const [lesson, setLesson] = useState("All");
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const [openSubjectMenu, setOpenSubjectMenu] = useState(false);
  const [openLessonMenu, setOpenLessonMenu] = useState(false);

  // Initialize consistent state across server and client to prevent hydration mismatches
  const [conversations, setConversations] = useState<Conversation[]>(DEFAULT_CONVERSATIONS);
  const [activeConvId, setActiveConvId] = useState<string>("init-conv-1");

  const chatEndRef = useRef<HTMLDivElement>(null);
  const subjectRef = useRef<HTMLDivElement>(null);
  const lessonRef = useRef<HTMLDivElement>(null);

  // Load saved session history and fetch metadata on client mount
  useEffect(() => {
    setIsMounted(true);

    const savedConvs = sessionStorage.getItem(STORAGE_KEY_CONVS);
    const savedActiveId = sessionStorage.getItem(STORAGE_KEY_ACTIVE_ID);

    if (savedConvs) {
      try {
        const parsed = JSON.parse(savedConvs);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setConversations(parsed);
          if (savedActiveId) {
            setActiveConvId(savedActiveId);
            const active = parsed.find((c) => c.id === savedActiveId) || parsed[0];
            setSubject(active.subject || "All");
            setLesson(active.lesson || "All");
          }
        }
      } catch (e) {
        console.warn("Failed to parse saved sessions:", e);
      }
    }

    fetch("http://localhost:8000/api/metadata")
      .then((res) => (res.ok ? res.json() : {}))
      .then((data) => setMetadata(data))
      .catch((err) => console.warn("Failed to fetch filter metadata:", err));
  }, []);

  const activeConv = conversations.find((c) => c.id === activeConvId) || conversations[0];

  // Persist conversation updates to sessionStorage
  useEffect(() => {
    if (isMounted) {
      sessionStorage.setItem(STORAGE_KEY_CONVS, JSON.stringify(conversations));
      sessionStorage.setItem(STORAGE_KEY_ACTIVE_ID, activeConvId);
    }
  }, [conversations, activeConvId, isMounted]);

  // Handle outside clicks to close dropdown menus
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (subjectRef.current && !subjectRef.current.contains(event.target as Node)) {
        setOpenSubjectMenu(false);
      }
      if (lessonRef.current && !lessonRef.current.contains(event.target as Node)) {
        setOpenLessonMenu(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Auto-scroll to the latest message
  useEffect(() => {
    if (activeConv?.messages?.length > 0) {
      chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [activeConv?.messages, loading]);

  const handleNewChat = () => {
    const newId = "conv-" + Date.now();
    const newConv: Conversation = {
      id: newId,
      name: "New Study Session",
      messages: [],
      subject: "All",
      lesson: "All",
    };
    setConversations((prev) => [newConv, ...prev]);
    setActiveConvId(newId);
    setSubject("All");
    setLesson("All");
  };

  const handleSelectConv = (id: string) => {
    setActiveConvId(id);
    const target = conversations.find((c) => c.id === id);
    if (target) {
      setSubject(target.subject || "All");
      setLesson(target.lesson || "All");
    }
  };

  const handleDeleteConv = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const updated = conversations.filter((c) => c.id !== id);
    if (updated.length === 0) {
      const fallbackId = "conv-" + Date.now();
      const fallbackConv = {
        id: fallbackId,
        name: "New Study Session",
        messages: [],
        subject: "All",
        lesson: "All",
      };
      setConversations([fallbackConv]);
      setActiveConvId(fallbackId);
    } else {
      setConversations(updated);
      if (activeConvId === id) {
        setActiveConvId(updated[0].id);
      }
    }
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userQuery = input.trim();
    const isFirstMessage = activeConv.messages.length === 0;
    const newTitle = isFirstMessage
      ? userQuery.slice(0, 30) + (userQuery.length > 30 ? "..." : "")
      : activeConv.name;

    const userMsg: Message = { role: "user", content: userQuery };
    const updatedMessages = [...activeConv.messages, userMsg];

    setConversations((prev) =>
      prev.map((c) =>
        c.id === activeConvId
          ? { ...c, name: newTitle, messages: updatedMessages, subject, lesson }
          : c
      )
    );

    setInput("");
    setLoading(true);

    try {
      const res = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: "client-sess-01",
          conv_id: activeConvId,
          conv_name: newTitle,
          query: userQuery,
          subject,
          lesson,
          threshold: 0.45,
          history: activeConv.messages,
        }),
      });

      const data = await res.json();
      const assistantMsg: Message = { role: "assistant", content: data.reply };

      setConversations((prev) =>
        prev.map((c) =>
          c.id === activeConvId
            ? { ...c, messages: [...updatedMessages, assistantMsg] }
            : c
        )
      );
    } catch (err: any) {
      const errorMsg: Message = {
        role: "assistant",
        content: `⚠️ Failed to connect to AI Tutor service: ${err.message}`,
      };
      setConversations((prev) =>
        prev.map((c) =>
          c.id === activeConvId
            ? { ...c, messages: [...updatedMessages, errorMsg] }
            : c
        )
      );
    } finally {
      setLoading(false);
    }
  };

  const availableLessons = subject === "All" ? [] : metadata[subject] || [];

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#fdfbf7]">
      <Sidebar
        conversations={conversations}
        activeConvId={activeConvId}
        onSelectConv={handleSelectConv}
        onNewChat={handleNewChat}
        onDeleteConv={handleDeleteConv}
      />

      <div className="flex-1 flex flex-col h-full min-w-0 max-w-4xl mx-auto px-6 py-4 overflow-hidden">
        {/* Messages Feed Container */}
        <div className="flex-1 min-h-0 overflow-y-auto space-y-5 pr-2">
          {activeConv.messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center text-slate-500 space-y-4 py-6">
              <div className="p-3.5 rounded-2xl bg-white border border-[#ece3d2] shadow-sm">
                <Image src="/LogoHTA.png" alt="Platform Logo" width={60} height={60} />
              </div>
              <h2 className="text-slate-800 font-bold text-xl tracking-tight">
                What can I help you with today?
              </h2>
              <p className="text-sm max-w-md text-slate-500">
                Feel free to ask the AI Tutor any academic questions or request practice exercises.
              </p>
            </div>
          ) : (
            <>
              {activeConv.messages.map((m, idx) => (
                <div
                  key={idx}
                  className={`flex gap-3.5 ${m.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  {m.role !== "user" && (
                    <div className="w-8 h-8 rounded-xl bg-[#f5ede0] border border-[#e5d5b3] flex items-center justify-center text-amber-700 flex-shrink-0 mt-1 shadow-xs">
                      <Bot className="w-4 h-4" />
                    </div>
                  )}
                  <div
                    className={`p-4 rounded-2xl max-w-[85%] text-sm leading-relaxed ${
                      m.role === "user"
                        ? "bg-amber-500 text-white rounded-br-none shadow-md shadow-amber-500/20 font-medium"
                        : "bg-white border border-[#ece3d2] text-slate-800 rounded-bl-none shadow-xs"
                    }`}
                  >
                    <ReactMarkdown
                      remarkPlugins={[remarkBreaks]}
                      className="prose prose-slate max-w-none text-sm leading-relaxed"
                    >
                      {m.content}
                    </ReactMarkdown>
                  </div>
                  {m.role === "user" && (
                    <div className="w-8 h-8 rounded-xl bg-slate-800 text-white flex items-center justify-center flex-shrink-0 mt-1 shadow-xs">
                      <User className="w-4 h-4" />
                    </div>
                  )}
                </div>
              ))}

              {loading && (
                <div className="flex gap-3.5 items-center text-slate-500 text-xs animate-pulse">
                  <div className="w-8 h-8 rounded-xl bg-[#f5ede0] border border-[#e5d5b3] flex items-center justify-center text-amber-600">
                    <Bot className="w-4 h-4 animate-spin" />
                  </div>
                  <span>Generating contextual explanation...</span>
                </div>
              )}
              <div ref={chatEndRef} />
            </>
          )}
        </div>

        {/* Knowledge Selectors & Input Dock */}
        <div className="mt-3 pt-2 space-y-2 flex-shrink-0">
          <div className="flex items-center gap-3 px-1">
            {/* Subject Slicer */}
            <div className="relative min-w-[200px]" ref={subjectRef}>
              <button
                type="button"
                onClick={() => {
                  setOpenSubjectMenu(!openSubjectMenu);
                  setOpenLessonMenu(false);
                }}
                className="w-full flex items-center justify-between gap-2 bg-white hover:bg-[#faf6ee] border border-[#ece3d2] hover:border-[#dfd3bc] px-3.5 py-2 rounded-xl text-xs text-slate-700 shadow-xs transition duration-150"
              >
                <div className="flex items-center gap-2 truncate">
                  <BookOpen className="w-3.5 h-3.5 text-amber-600 flex-shrink-0" />
                  <span className="text-slate-400 font-medium">Subject:</span>
                  <span className="font-bold text-slate-800 truncate">
                    {subject === "All" ? "All Subjects" : subject}
                  </span>
                </div>
                <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 flex-shrink-0 ${openSubjectMenu ? "rotate-180 text-amber-600" : ""}`} />
              </button>

              {openSubjectMenu && (
                <div className="absolute bottom-full mb-2 left-0 w-full min-w-[220px] bg-white border border-[#ece3d2] rounded-2xl shadow-xl p-1.5 z-30 space-y-0.5 max-h-60 overflow-y-auto">
                  <button
                    onClick={() => {
                      setSubject("All");
                      setLesson("All");
                      setOpenSubjectMenu(false);
                    }}
                    className={`w-full flex items-center justify-between px-3 py-2 text-xs rounded-xl transition ${
                      subject === "All"
                        ? "bg-[#f5ede0] text-amber-950 font-bold"
                        : "text-slate-700 hover:bg-[#fbf7ee]"
                    }`}
                  >
                    <span>All Subjects</span>
                    {subject === "All" && <Check className="w-3.5 h-3.5 text-amber-600" />}
                  </button>
                  {Object.keys(metadata).map((s) => (
                    <button
                      key={s}
                      onClick={() => {
                        setSubject(s);
                        setLesson("All");
                        setOpenSubjectMenu(false);
                      }}
                      className={`w-full flex items-center justify-between px-3 py-2 text-xs rounded-xl transition ${
                        subject === s
                          ? "bg-[#f5ede0] text-amber-950 font-bold"
                          : "text-slate-700 hover:bg-[#fbf7ee]"
                      }`}
                    >
                      <span className="truncate">{s}</span>
                      {subject === s && <Check className="w-3.5 h-3.5 text-amber-600" />}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Lesson Slicer */}
            <div className="relative flex-1" ref={lessonRef}>
              <button
                type="button"
                onClick={() => {
                  setOpenLessonMenu(!openLessonMenu);
                  setOpenSubjectMenu(false);
                }}
                className="w-full flex items-center justify-between gap-2 bg-white hover:bg-[#faf6ee] border border-[#ece3d2] hover:border-[#dfd3bc] px-3.5 py-2 rounded-xl text-xs text-slate-700 shadow-xs transition duration-150"
              >
                <div className="flex items-center gap-2 truncate">
                  <Layers className="w-3.5 h-3.5 text-amber-600 flex-shrink-0" />
                  <span className="text-slate-400 font-medium">Lesson:</span>
                  <span className="font-bold text-slate-800 truncate">
                    {lesson === "All" ? "All Lessons" : lesson}
                  </span>
                </div>
                <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 flex-shrink-0 ${openLessonMenu ? "rotate-180 text-amber-600" : ""}`} />
              </button>

              {openLessonMenu && (
                <div className="absolute bottom-full mb-2 left-0 w-full bg-white border border-[#ece3d2] rounded-2xl shadow-xl p-1.5 z-30 space-y-0.5 max-h-64 overflow-y-auto">
                  <button
                    onClick={() => {
                      setLesson("All");
                      setOpenLessonMenu(false);
                    }}
                    className={`w-full flex items-center justify-between px-3 py-2 text-xs rounded-xl transition ${
                      lesson === "All"
                        ? "bg-[#f5ede0] text-amber-950 font-bold"
                        : "text-slate-700 hover:bg-[#fbf7ee]"
                    }`}
                  >
                    <span>All Lessons</span>
                    {lesson === "All" && <Check className="w-3.5 h-3.5 text-amber-600" />}
                  </button>
                  {availableLessons.map((l) => (
                    <button
                      key={l}
                      onClick={() => {
                        setLesson(l);
                        setOpenLessonMenu(false);
                      }}
                      className={`w-full flex items-center justify-between px-3 py-2 text-xs rounded-xl transition text-left ${
                        lesson === l
                          ? "bg-[#f5ede0] text-amber-950 font-bold"
                          : "text-slate-700 hover:bg-[#fbf7ee]"
                      }`}
                    >
                      <span className="truncate pr-2">{l}</span>
                      {lesson === l && <Check className="w-3.5 h-3.5 text-amber-600 flex-shrink-0" />}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* User Input Field */}
          <div className="relative flex items-center">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder="Ask an academic question or request practice problems..."
              className="w-full bg-white border border-[#ece3d2] rounded-2xl pl-5 pr-14 py-3 text-sm text-slate-800 focus:outline-none focus:border-amber-500 focus:ring-2 focus:ring-amber-200/50 shadow-sm placeholder:text-slate-400"
            />
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className="absolute right-2 p-2.5 rounded-xl bg-amber-500 hover:bg-amber-600 disabled:opacity-40 text-white transition shadow-sm shadow-amber-500/20"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}