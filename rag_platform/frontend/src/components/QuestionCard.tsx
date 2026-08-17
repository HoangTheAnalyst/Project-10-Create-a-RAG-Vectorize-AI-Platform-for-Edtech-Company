import { CheckCircle2, XCircle, ChevronDown, HelpCircle } from "lucide-react";
import { useState } from "react";

interface QuestionProps {
  idx: number;
  stem: string;
  options: string[];
  rawAnswer: string;
  correctChar: string | null;
  userAnswer?: string;
  isSubmitted: boolean;
  onSelectOption: (option: string) => void;
}

export default function QuestionCard({
  idx,
  stem,
  options,
  rawAnswer,
  correctChar,
  userAnswer,
  isSubmitted,
  onSelectOption,
}: QuestionProps) {
  const [showDetail, setShowDetail] = useState(false);
  const isCorrect = userAnswer?.startsWith(correctChar || "NONE");

  return (
    <div className="rounded-2xl bg-amber-50/70 border border-amber-200/80 p-6 shadow-xs transition hover:border-amber-400 space-y-4">
      {/* Question Header */}
      <div className="flex items-start gap-3">
        <span className="px-2.5 py-1 rounded-lg bg-amber-200 text-amber-950 border border-amber-300 text-xs font-bold font-mono">
          Q{idx}
        </span>
        <h3 className="font-bold text-amber-950 text-base leading-relaxed flex-1">{stem}</h3>
      </div>

      {/* Options List */}
      <div className="grid gap-2.5 pt-1">
        {options.map((opt) => {
          const isSelected = userAnswer === opt;
          return (
            <button
              key={opt}
              type="button"
              disabled={isSubmitted}
              onClick={() => onSelectOption(opt)}
              className={`w-full flex items-center justify-between p-3.5 rounded-xl text-sm font-medium border text-left transition-all duration-150 ${
                isSelected
                  ? "bg-amber-200/80 border-orange-400 text-amber-950 shadow-xs font-bold"
                  : "bg-amber-100/30 border-amber-200/70 text-amber-900 hover:bg-amber-100/70"
              }`}
            >
              <span>{opt}</span>
              <div
                className={`w-4 h-4 rounded-full border flex items-center justify-center transition ${
                  isSelected ? "border-orange-500 bg-orange-500" : "border-amber-300"
                }`}
              >
                {isSelected && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
              </div>
            </button>
          );
        })}
      </div>

      {/* Explanation Details */}
      {isSubmitted && (
        <div className="mt-4 pt-4 border-t border-amber-200/60 space-y-3">
          <div className="flex items-center justify-between">
            <div>
              {isCorrect ? (
                <span className="flex items-center gap-1.5 text-xs font-bold text-emerald-800 px-3 py-1 bg-emerald-100 border border-emerald-300 rounded-full">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> Correct Answer
                </span>
              ) : (
                <span className="flex items-center gap-1.5 text-xs font-bold text-rose-800 px-3 py-1 bg-rose-100 border border-rose-300 rounded-full">
                  <XCircle className="w-3.5 h-3.5 text-rose-600" /> Incorrect (Correct Key: {correctChar})
                </span>
              )}
            </div>

            <button
              onClick={() => setShowDetail(!showDetail)}
              className="flex items-center gap-1 text-xs font-bold text-amber-800 hover:text-orange-600 transition"
            >
              <HelpCircle className="w-3.5 h-3.5" />
              {showDetail ? "Hide Explanation" : "View Step-by-Step Explanation"}
              <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showDetail ? "rotate-180" : ""}`} />
            </button>
          </div>

          {showDetail && (
            <div className="p-4 rounded-xl bg-amber-100/60 border border-amber-300/80 text-xs text-amber-950 leading-relaxed whitespace-pre-wrap">
              {rawAnswer}
            </div>
          )}
        </div>
      )}
    </div>
  );
}