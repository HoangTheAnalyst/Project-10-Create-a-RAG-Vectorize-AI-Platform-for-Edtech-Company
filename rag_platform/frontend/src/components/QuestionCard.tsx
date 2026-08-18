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
    <div className="rounded-2xl bg-amber-50/70 border border-amber-200/80 p-4 sm:p-6 shadow-xs transition hover:border-amber-400 space-y-3.5 sm:space-y-4">
      {/* Question Header */}
      <div className="flex items-start gap-2.5 sm:gap-3">
        <span className="px-2 sm:px-2.5 py-0.5 sm:py-1 rounded-lg bg-amber-200 text-amber-950 border border-amber-300 text-[11px] sm:text-xs font-bold font-mono flex-shrink-0 mt-0.5">
          Q{idx}
        </span>
        <h3 className="font-bold text-amber-950 text-sm sm:text-base leading-relaxed flex-1">
          {stem}
        </h3>
      </div>

      {/* Options List */}
      <div className="grid gap-2 sm:gap-2.5 pt-1">
        {options.map((opt) => {
          const isSelected = userAnswer === opt;
          return (
            <button
              key={opt}
              type="button"
              disabled={isSubmitted}
              onClick={() => onSelectOption(opt)}
              className={`w-full flex items-center justify-between p-3 sm:p-3.5 rounded-xl text-xs sm:text-sm font-medium border text-left transition-all duration-150 ${
                isSelected
                  ? "bg-amber-200/80 border-orange-400 text-amber-950 shadow-xs font-bold"
                  : "bg-amber-100/30 border-amber-200/70 text-amber-900 hover:bg-amber-100/70"
              }`}
            >
              <span className="break-words pr-2 flex-1">{opt}</span>
              <div
                className={`w-4 h-4 rounded-full border flex items-center justify-center flex-shrink-0 transition ${
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
        <div className="mt-3.5 sm:mt-4 pt-3.5 sm:pt-4 border-t border-amber-200/60 space-y-3">
          {/* Status & Toggle: Stack on Mobile, Flex Row on Tablet/Desktop */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
            <div>
              {isCorrect ? (
                <span className="inline-flex items-center gap-1.5 text-[11px] sm:text-xs font-bold text-emerald-800 px-2.5 sm:px-3 py-1 bg-emerald-100 border border-emerald-300 rounded-full">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" /> Correct Answer
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 text-[11px] sm:text-xs font-bold text-rose-800 px-2.5 sm:px-3 py-1 bg-rose-100 border border-rose-300 rounded-full">
                  <XCircle className="w-3.5 h-3.5 text-rose-600 flex-shrink-0" /> Incorrect (Correct Key: {correctChar})
                </span>
              )}
            </div>

            <button
              onClick={() => setShowDetail(!showDetail)}
              className="flex items-center gap-1 text-[11px] sm:text-xs font-bold text-amber-800 hover:text-orange-600 transition self-start sm:self-auto"
            >
              <HelpCircle className="w-3.5 h-3.5 flex-shrink-0" />
              <span>{showDetail ? "Hide Explanation" : "View Step-by-Step Explanation"}</span>
              <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 flex-shrink-0 ${showDetail ? "rotate-180" : ""}`} />
            </button>
          </div>

          {showDetail && (
            <div className="p-3.5 sm:p-4 rounded-xl bg-amber-100/60 border border-amber-300/80 text-xs text-amber-950 leading-relaxed whitespace-pre-wrap">
              {rawAnswer}
            </div>
          )}
        </div>
      )}
    </div>
  );
}