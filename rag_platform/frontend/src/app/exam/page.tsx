"use client";
import { useState, useEffect, useRef } from "react";
import Sidebar from "@/components/Sidebar";
import QuestionCard from "@/components/QuestionCard";
import { Play, RotateCcw, Award, BookOpen, Layers, Hash, ChevronDown, Check } from "lucide-react";

const STORAGE_KEY_EXAM = "edugenius_active_exam_state";

export default function ExamPage() {
  const [isMounted, setIsMounted] = useState(false);
  const [metadata, setMetadata] = useState<Record<string, string[]>>({});

  // Initialize consistent state across server and client
  const [subject, setSubject] = useState<string>("");
  const [lesson, setLesson] = useState<string>("");
  const [limit, setLimit] = useState<number>(5);
  const [questions, setQuestions] = useState<any[]>([]);
  const [userAnswers, setUserAnswers] = useState<Record<number, string>>({});
  const [isSubmitted, setIsSubmitted] = useState<boolean>(false);
  const [loading, setLoading] = useState(false);

  const [openSubjectMenu, setOpenSubjectMenu] = useState(false);
  const [openLessonMenu, setOpenLessonMenu] = useState(false);
  const [openLimitMenu, setOpenLimitMenu] = useState(false);

  const subjectRef = useRef<HTMLDivElement>(null);
  const lessonRef = useRef<HTMLDivElement>(null);
  const limitRef = useRef<HTMLDivElement>(null);

  // Restore state from sessionStorage and fetch filter metadata on client mount
  useEffect(() => {
    setIsMounted(true);

    let savedSubject = "";
    const saved = sessionStorage.getItem(STORAGE_KEY_EXAM);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (parsed.subject) {
          setSubject(parsed.subject);
          savedSubject = parsed.subject;
        }
        if (parsed.lesson) setLesson(parsed.lesson);
        if (parsed.limit) setLimit(parsed.limit);
        if (parsed.questions) setQuestions(parsed.questions);
        if (parsed.userAnswers) setUserAnswers(parsed.userAnswers);
        if (parsed.isSubmitted !== undefined) setIsSubmitted(parsed.isSubmitted);
      } catch (e) {
        console.warn("Failed to parse saved exam state:", e);
      }
    }

    fetch("http://localhost:8000/api/metadata")
      .then((res) => (res.ok ? res.json() : {}))
      .then((data) => {
        setMetadata(data);
        if (!savedSubject) {
          const firstSubj = Object.keys(data)[0] || "";
          setSubject(firstSubj);
          setLesson(data[firstSubj]?.[0] || "");
        }
      })
      .catch((err) => console.warn("Failed to fetch filter metadata:", err));
  }, []);

  // Persist current quiz session to sessionStorage
  useEffect(() => {
    if (isMounted) {
      const stateToSave = {
        subject,
        lesson,
        limit,
        questions,
        userAnswers,
        isSubmitted,
      };
      sessionStorage.setItem(STORAGE_KEY_EXAM, JSON.stringify(stateToSave));
    }
  }, [subject, lesson, limit, questions, userAnswers, isSubmitted, isMounted]);

  // Close dropdown menus when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (subjectRef.current && !subjectRef.current.contains(event.target as Node)) {
        setOpenSubjectMenu(false);
      }
      if (lessonRef.current && !lessonRef.current.contains(event.target as Node)) {
        setOpenLessonMenu(false);
      }
      if (limitRef.current && !limitRef.current.contains(event.target as Node)) {
        setOpenLimitMenu(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const startQuiz = async () => {
    setLoading(true);
    setIsSubmitted(false);
    setUserAnswers({});
    try {
      const res = await fetch("http://localhost:8000/api/exam", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subject, lesson, limit }),
      });
      const data = await res.json();
      setQuestions(data.questions || []);
    } finally {
      setLoading(false);
    }
  };

  const calculateScore = () => {
    let correct = 0;
    questions.forEach((q, idx) => {
      if (userAnswers[idx]?.startsWith(q.correct_char || "NONE")) correct++;
    });
    return { correct, total: questions.length };
  };

  const availableLessons = subject ? metadata[subject] || [] : [];
  const questionCountOptions = Array.from({ length: 10 }, (_, i) => i + 1);

  if (!isMounted) {
    return (
      <div className="flex h-screen w-screen overflow-hidden bg-[#fdfbf7]">
        <Sidebar />
        <div className="flex-1 flex items-center justify-center text-slate-400 text-sm font-medium animate-pulse">
          Loading exam room...
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#fdfbf7]">
      <Sidebar />
      <div className="flex-1 overflow-y-auto min-w-0 max-w-4xl mx-auto px-8 py-8 space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-800">📝 Exam Practice & Quiz Room</h1>
          <p className="text-sm text-slate-500 mt-1">Practice Makes Perfect !</p>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-[#ece3d2] shadow-sm space-y-4">
          <div className="grid grid-cols-12 gap-4">
            {/* Subject Selector */}
            <div className="col-span-4 relative" ref={subjectRef}>
              <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1.5">Subject</label>
              <button
                type="button"
                onClick={() => {
                  setOpenSubjectMenu(!openSubjectMenu);
                  setOpenLessonMenu(false);
                  setOpenLimitMenu(false);
                }}
                className="w-full flex items-center justify-between gap-2 bg-[#fdfbf7] hover:bg-[#faf6ee] border border-[#ece3d2] hover:border-[#dfd3bc] px-3.5 py-2.5 rounded-xl text-xs text-slate-700 shadow-xs transition duration-150"
              >
                <div className="flex items-center gap-2 truncate">
                  <BookOpen className="w-3.5 h-3.5 text-amber-600 flex-shrink-0" />
                  <span className="font-bold text-slate-800 truncate">{subject || "Select Subject"}</span>
                </div>
                <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 flex-shrink-0 ${openSubjectMenu ? "rotate-180 text-amber-600" : ""}`} />
              </button>

              {openSubjectMenu && (
                <div className="absolute top-full mt-1.5 left-0 w-full bg-white border border-[#ece3d2] rounded-2xl shadow-xl p-1.5 z-30 space-y-0.5 max-h-60 overflow-y-auto">
                  {Object.keys(metadata).map((s) => (
                    <button
                      key={s}
                      onClick={() => {
                        setSubject(s);
                        setLesson(metadata[s]?.[0] || "");
                        setOpenSubjectMenu(false);
                      }}
                      className={`w-full flex items-center justify-between px-3 py-2 text-xs rounded-xl transition ${
                        subject === s ? "bg-[#f5ede0] text-amber-950 font-bold" : "text-slate-700 hover:bg-[#fbf7ee]"
                      }`}
                    >
                      <span className="truncate">{s}</span>
                      {subject === s && <Check className="w-3.5 h-3.5 text-amber-600" />}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Lesson Selector */}
            <div className="col-span-5 relative" ref={lessonRef}>
              <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1.5">Lesson</label>
              <button
                type="button"
                onClick={() => {
                  setOpenLessonMenu(!openLessonMenu);
                  setOpenSubjectMenu(false);
                  setOpenLimitMenu(false);
                }}
                className="w-full flex items-center justify-between gap-2 bg-[#fdfbf7] hover:bg-[#faf6ee] border border-[#ece3d2] hover:border-[#dfd3bc] px-3.5 py-2.5 rounded-xl text-xs text-slate-700 shadow-xs transition duration-150"
              >
                <div className="flex items-center gap-2 truncate">
                  <Layers className="w-3.5 h-3.5 text-amber-600 flex-shrink-0" />
                  <span className="font-bold text-slate-800 truncate">{lesson || "Select Lesson"}</span>
                </div>
                <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 flex-shrink-0 ${openLessonMenu ? "rotate-180 text-amber-600" : ""}`} />
              </button>

              {openLessonMenu && (
                <div className="absolute top-full mt-1.5 left-0 w-full bg-white border border-[#ece3d2] rounded-2xl shadow-xl p-1.5 z-30 space-y-0.5 max-h-64 overflow-y-auto">
                  {availableLessons.map((l) => (
                    <button
                      key={l}
                      onClick={() => {
                        setLesson(l);
                        setOpenLessonMenu(false);
                      }}
                      className={`w-full flex items-center justify-between px-3 py-2 text-xs rounded-xl transition text-left ${
                        lesson === l ? "bg-[#f5ede0] text-amber-950 font-bold" : "text-slate-700 hover:bg-[#fbf7ee]"
                      }`}
                    >
                      <span className="truncate pr-2">{l}</span>
                      {lesson === l && <Check className="w-3.5 h-3.5 text-amber-600 flex-shrink-0" />}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Question Count Selector (1 - 10) */}
            <div className="col-span-3 relative" ref={limitRef}>
              <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1.5">Questions</label>
              <button
                type="button"
                onClick={() => {
                  setOpenLimitMenu(!openLimitMenu);
                  setOpenSubjectMenu(false);
                  setOpenLessonMenu(false);
                }}
                className="w-full flex items-center justify-between gap-2 bg-[#fdfbf7] hover:bg-[#faf6ee] border border-[#ece3d2] hover:border-[#dfd3bc] px-3.5 py-2.5 rounded-xl text-xs text-slate-700 shadow-xs transition duration-150"
              >
                <div className="flex items-center gap-2 truncate">
                  <Hash className="w-3.5 h-3.5 text-amber-600 flex-shrink-0" />
                  <span className="font-bold text-slate-800">{limit} Questions</span>
                </div>
                <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 flex-shrink-0 ${openLimitMenu ? "rotate-180 text-amber-600" : ""}`} />
              </button>

              {openLimitMenu && (
                <div className="absolute top-full mt-1.5 left-0 w-full bg-white border border-[#ece3d2] rounded-2xl shadow-xl p-1.5 z-30 space-y-0.5 max-h-60 overflow-y-auto">
                  {questionCountOptions.map((cnt) => (
                    <button
                      key={cnt}
                      onClick={() => {
                        setLimit(cnt);
                        setOpenLimitMenu(false);
                      }}
                      className={`w-full flex items-center justify-between px-3 py-2 text-xs rounded-xl transition ${
                        limit === cnt ? "bg-[#f5ede0] text-amber-950 font-bold" : "text-slate-700 hover:bg-[#fbf7ee]"
                      }`}
                    >
                      <span>{cnt} {cnt === 1 ? "Question" : "Questions"}</span>
                      {limit === cnt && <Check className="w-3.5 h-3.5 text-amber-600" />}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="pt-1">
            <button
              onClick={startQuiz}
              disabled={loading}
              className="w-full py-3 rounded-xl bg-amber-500 hover:bg-amber-600 font-bold text-xs text-white transition flex items-center justify-center gap-2 shadow-sm shadow-amber-500/20 disabled:opacity-40"
            >
              <Play className="w-4 h-4 fill-white" /> {loading ? "Generating Quiz..." : "Start Quiz"}
            </button>
          </div>
        </div>

        {/* Questions Feed */}
        <div className="space-y-5">
          {questions.map((q, idx) => (
            <QuestionCard
              key={idx}
              idx={idx + 1}
              stem={q.stem}
              options={q.options}
              rawAnswer={q.raw_answer}
              correctChar={q.correct_char}
              userAnswer={userAnswers[idx]}
              isSubmitted={isSubmitted}
              onSelectOption={(val) => setUserAnswers({ ...userAnswers, [idx]: val })}
            />
          ))}
        </div>

        {/* Quiz Submission Action */}
        {questions.length > 0 && !isSubmitted && (
          <button
            onClick={() => setIsSubmitted(true)}
            className="w-full py-3.5 rounded-2xl bg-amber-500 hover:bg-amber-600 font-bold text-sm text-white transition shadow-md shadow-amber-500/20"
          >
            Submit & Grade Quiz
          </button>
        )}

        {/* Scoring & Review Summary Card */}
        {isSubmitted && (
          <div className="p-6 rounded-2xl bg-white border border-[#ece3d2] shadow-sm flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-2xl bg-[#f5ede0] border border-[#e5d5b3] text-amber-700">
                <Award className="w-7 h-7" />
              </div>
              <div>
                <div className="text-xl font-bold text-slate-800">
                  {calculateScore().correct} / {calculateScore().total} Questions Correct
                </div>
                <p className="text-xs text-slate-500 font-medium mt-0.5">
                  Accuracy Score: {((calculateScore().correct / calculateScore().total) * 100).toFixed(1)}%
                </p>
              </div>
            </div>
            <button
              onClick={startQuiz}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#fdfbf7] border border-[#ece3d2] hover:bg-[#faf6ee] text-slate-700 text-xs font-bold transition shadow-xs"
            >
              <RotateCcw className="w-3.5 h-3.5 text-amber-600" /> Retake New Quiz
            </button>
          </div>
        )}
      </div>
    </div>
  );
}