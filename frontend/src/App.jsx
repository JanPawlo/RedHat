import React, { useState } from 'react';
import { ArrowLeft, ArrowRight, ArrowUp, ArrowDown, Sparkles, RotateCcw, Loader2, Bot } from 'lucide-react';

const CARD_FACTS = {
  counterparty: 'Młyn Nowak',
  category: 'FLOUR SUPPLIER · PAYABLES',
  question_title: 'Pay invoice 21 days early to get a 4% discount?',
  invoice_number: 'FV/11/0412',
  invoice_amount: '14,800 PLN',
  due_date: '11 Dec',
  days_early: 21,
  discount_percent: '4%',
  amount_saved: '592 PLN',
  amount_to_pay_today: '14,208 PLN',
  safety_buffer: '150,000 PLN',
  cash_stays_above_buffer: true,
  ai_recommendation: "I'd swipe right",
  ai_confidence: '86%',
};

const SYSTEM_PROMPT =
  'You are an Autonomous CFO assistant for small and medium-sized business owners. ' +
  'Explain financial recommendations in simple, friendly, plain language without corporate jargon. ' +
  'STRICT RULE: Never invent or calculate any numbers yourself. Use ONLY the exact numbers provided in FACTS. ' +
  'Keep your explanation concise (3-4 short sentences).';

export default function App() {
  const [isFlipped, setIsFlipped] = useState(false);
  const [loading, setLoading] = useState(false);
  const [explanation, setExplanation] = useState('');
  const [modelName, setModelName] = useState('llama-32-3b-instruct');
  const [errorMsg, setErrorMsg] = useState('');

  const fetchExplanation = async () => {
    setLoading(true);
    setErrorMsg('');
    const question =
      'Why do you recommend paying invoice FV/11/0412 from Młyn Nowak 21 days early for a 4% discount, and is our 150k PLN safety buffer safe?';

    try {
      // 1. Try FastAPI backend endpoint (/api/v1/ai/explain)
      const res = await fetch('/api/v1/ai/explain', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ facts: CARD_FACTS, question }),
      });

      if (res.ok) {
        const data = await res.json();
        setExplanation(data.answer);
        if (data.model) setModelName(data.model);
        setLoading(false);
        return;
      }
    } catch {
      // Fall through to direct vLLM proxy if FastAPI backend container isn't running
    }

    try {
      // 2. Fallback: talk directly to local oc port-forward vLLM (/vllm/v1/chat/completions)
      const vllmRes = await fetch('/vllm/v1/chat/completions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'llama-32-3b-instruct',
          temperature: 0.2,
          max_tokens: 250,
          messages: [
            { role: 'system', content: SYSTEM_PROMPT },
            {
              role: 'user',
              content: `FACTS:\n${JSON.stringify(CARD_FACTS)}\n\nQUESTION:\n${question}`,
            },
          ],
        }),
      });

      if (!vllmRes.ok) {
        throw new Error(`HTTP ${vllmRes.status}`);
      }
      const vllmData = await vllmRes.json();
      setExplanation(vllmData.choices?.[0]?.message?.content?.trim() || 'No response received.');
      setModelName('llama-32-3b-instruct');
    } catch (err) {
      setErrorMsg(
        'Could not reach RHOAI model (llama-32-3b-instruct). Make sure oc port-forward on port 8080 is running.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleAskWhy = () => {
    const nextFlipped = !isFlipped;
    setIsFlipped(nextFlipped);
    if (nextFlipped && !explanation && !loading) {
      fetchExplanation();
    }
  };

  return (
    <div className="min-h-screen bg-[#F4F0E6] flex flex-col items-center justify-center px-4 py-10 select-none">
      {/* Top Progress Bar */}
      <div className="flex items-center gap-4 mb-7">
        <div className="flex items-center gap-2">
          <span className="w-[18px] h-[6px] rounded-full bg-[#1C1A17]" />
          <span className="w-[18px] h-[6px] rounded-full bg-[#1C1A17]" />
          <span className="w-[36px] h-[6px] rounded-full bg-[#D92D2D]" />
          <span className="w-[18px] h-[6px] rounded-full bg-[#DFDBD0]" />
          <span className="w-[18px] h-[6px] rounded-full bg-[#DFDBD0]" />
          <span className="w-[18px] h-[6px] rounded-full bg-[#DFDBD0]" />
          <span className="w-[18px] h-[6px] rounded-full bg-[#DFDBD0]" />
        </div>
        <span className="text-[15px] text-[#6B665E] font-normal tracking-tight">
          Card 3 of 7 &middot; about 2 min left
        </span>
      </div>

      {/* Card Stack + 3D Flip Container */}
      <div className="relative w-full max-w-[430px] perspective-1200">
        {/* Background stacked deck layers */}
        <div
          aria-hidden="true"
          className="absolute inset-0 rounded-[32px] bg-[#E7E2D5] -rotate-[4.2deg] translate-y-2.5 -translate-x-1.5 scale-[0.97] pointer-events-none"
        />
        <div
          aria-hidden="true"
          className="absolute inset-0 rounded-[32px] bg-[#FAF8F3] border border-[#E5E0D4] -rotate-[1.6deg] translate-y-1 pointer-events-none shadow-sm"
        />

        {/* Flipping Card */}
        <div
          className={`relative w-full transition-transform duration-700 ease-out preserve-3d ${
            isFlipped ? 'rotate-y-180' : ''
          }`}
        >
          {/* ================= FRONT FACE ================= */}
          <div className="w-full rounded-[32px] overflow-hidden bg-white shadow-[0_18px_45px_rgba(28,25,23,0.11)] border border-[#ECE8DF] backface-hidden">
            {/* Dark Top Header */}
            <div className="bg-[#1C1A17] pt-8 pb-7 px-6 flex flex-col items-center text-center">
              <div className="w-[104px] h-[104px] rounded-full bg-[#D38B28] border-[3.5px] border-white flex items-center justify-center shadow-md mb-4">
                <span className="text-white text-[34px] font-bold tracking-wide">MN</span>
              </div>
              <h2 className="text-white text-[22px] font-medium tracking-tight">Młyn Nowak</h2>
              <p className="text-[#A39E96] text-[12px] font-medium tracking-[0.14em] uppercase mt-1.5">
                FLOUR SUPPLIER &middot; PAYABLES
              </p>
            </div>

            {/* White Body */}
            <div className="bg-white px-8 pt-7 pb-8">
              <h1 className="text-[#1C1A17] text-[29px] leading-[1.2] font-bold tracking-[-0.02em]">
                Pay invoice 21 days early to get a 4% discount?
              </h1>

              <p className="mt-4 text-[#706B63] text-[17.5px] leading-[1.55] font-normal">
                Invoice FV/11/0412 &middot; 14,800 PLN due 11 Dec. Paying today saves 592 PLN. Cash
                stays above your 150k safety buffer.
              </p>

              {/* Green AI Recommendation Badge */}
              <div className="mt-5 inline-flex items-center gap-2 bg-[#DFF3E8] text-[#1D7A4C] px-4 py-2 rounded-full text-[15px] font-medium">
                <Sparkles className="w-4 h-4 fill-[#1D7A4C] text-[#1D7A4C]" />
                <span>I&apos;d swipe right &middot; 86% confident</span>
              </div>

              {/* Inner Choice Pills (non-interactive per request) */}
              <div className="mt-7 grid grid-cols-2 gap-3.5">
                <button
                  type="button"
                  onClick={() => {}}
                  className="bg-[#FCE8E8] text-[#D93838] rounded-2xl py-3.5 px-4 flex items-center justify-center gap-2 text-[15px] font-medium cursor-default"
                >
                  <ArrowLeft className="w-4 h-4 stroke-[2.2]" />
                  <span>Pay on due date</span>
                </button>
                <button
                  type="button"
                  onClick={() => {}}
                  className="bg-[#DFF3E8] text-[#1D7A4C] rounded-2xl py-3.5 px-4 flex items-center justify-center gap-2 text-[15px] font-medium cursor-default"
                >
                  <span>Pay early, take 4%</span>
                  <ArrowRight className="w-4 h-4 stroke-[2.2]" />
                </button>
              </div>
            </div>
          </div>

          {/* ================= BACK FACE (LLM EXPLANATION) ================= */}
          <div className="absolute inset-0 w-full h-full rounded-[32px] overflow-hidden bg-white shadow-[0_18px_45px_rgba(28,25,23,0.11)] border border-[#ECE8DF] backface-hidden rotate-y-180 flex flex-col justify-between">
            {/* Dark Header on Back */}
            <div className="bg-[#1C1A17] px-7 py-5 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 rounded-full bg-[#D38B28] border-2 border-white flex items-center justify-center">
                  <span className="text-white text-sm font-bold">MN</span>
                </div>
                <div>
                  <h3 className="text-white text-base font-medium leading-tight">Młyn Nowak</h3>
                  <p className="text-[#A39E96] text-[11px] tracking-[0.12em] uppercase mt-0.5">
                    WHY THIS RECOMMENDATION
                  </p>
                </div>
              </div>
              <span className="inline-flex items-center gap-1.5 bg-[#2B2824] text-[#DFF3E8] border border-[#3B3731] px-3 py-1 rounded-full text-xs font-medium">
                <Bot className="w-3.5 h-3.5 text-[#38B275]" />
                {modelName}
              </span>
            </div>

            {/* LLM Explanation Body */}
            <div className="px-8 py-6 flex-1 flex flex-col justify-between overflow-y-auto">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.12em] text-[#8C867B] mb-2.5">
                  Autonomous CFO Explanation (OpenShift AI)
                </div>

                {loading ? (
                  <div className="bg-[#F8F6F0] border border-[#E8E3D7] rounded-2xl p-6 flex flex-col items-center justify-center text-center min-h-[170px]">
                    <Loader2 className="w-7 h-7 text-[#1D7A4C] animate-spin mb-3" />
                    <p className="text-[#1C1A17] text-sm font-medium">
                      Asking {modelName} on Red Hat OpenShift AI...
                    </p>
                    <p className="text-[#8C867B] text-xs mt-1">
                      Explaining deterministic facts from Invoice FV/11/0412
                    </p>
                  </div>
                ) : errorMsg ? (
                  <div className="bg-[#FCE8E8] border border-[#F5C2C2] rounded-2xl p-5 text-[#B42318] text-sm leading-relaxed">
                    <p className="font-semibold mb-1">Model connection error</p>
                    <p>{errorMsg}</p>
                    <button
                      type="button"
                      onClick={fetchExplanation}
                      className="mt-3 inline-flex items-center gap-1.5 bg-white text-[#1C1A17] px-3.5 py-1.5 rounded-full text-xs font-medium shadow-sm border border-[#E2DDD2]"
                    >
                      Try again
                    </button>
                  </div>
                ) : (
                  <div className="bg-[#F8F6F0] border border-[#E8E3D7] rounded-2xl p-5 text-[#1C1A17] text-[16px] leading-[1.6] font-normal">
                    {explanation}
                  </div>
                )}

                {/* Engine Facts Summary */}
                <div className="mt-5 grid grid-cols-2 gap-2.5 text-xs">
                  <div className="bg-[#F8F6F0] rounded-xl px-3.5 py-2.5 border border-[#ECE8DF]">
                    <span className="text-[#8C867B] block">Invoice FV/11/0412</span>
                    <span className="text-[#1C1A17] font-semibold text-sm">14,800 PLN</span>
                  </div>
                  <div className="bg-[#DFF3E8]/60 rounded-xl px-3.5 py-2.5 border border-[#C6E9D6]">
                    <span className="text-[#1D7A4C] block">4% Early Discount</span>
                    <span className="text-[#1D7A4C] font-semibold text-sm">+592 PLN saved</span>
                  </div>
                  <div className="bg-[#F8F6F0] rounded-xl px-3.5 py-2.5 border border-[#ECE8DF]">
                    <span className="text-[#8C867B] block">Payment Timing</span>
                    <span className="text-[#1C1A17] font-semibold text-sm">21 days before 11 Dec</span>
                  </div>
                  <div className="bg-[#F8F6F0] rounded-xl px-3.5 py-2.5 border border-[#ECE8DF]">
                    <span className="text-[#8C867B] block">Safety Buffer</span>
                    <span className="text-[#1D7A4C] font-semibold text-sm">&gt; 150k PLN (Safe)</span>
                  </div>
                </div>
              </div>

              <button
                type="button"
                onClick={() => setIsFlipped(false)}
                className="mt-5 w-full bg-[#1C1A17] hover:bg-[#2E2B26] text-white rounded-2xl py-3.5 px-4 flex items-center justify-center gap-2 text-sm font-medium transition-colors"
              >
                <RotateCcw className="w-4 h-4" />
                <span>Flip back to decision card</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom 4 Action Buttons */}
      <div className="mt-8 flex items-center justify-center gap-3 flex-wrap">
        <button
          type="button"
          onClick={() => {}}
          className="bg-white border border-[#DFDBD0] rounded-full px-5 py-2.5 text-[15px] font-medium text-[#1C1A17] shadow-sm flex items-center gap-2 cursor-default"
        >
          <ArrowLeft className="w-4 h-4 text-[#D93838] stroke-[2.2]" />
          <span>Decline</span>
        </button>

        <button
          type="button"
          onClick={handleAskWhy}
          className={`border rounded-full px-5 py-2.5 text-[15px] font-medium shadow-sm flex items-center gap-2 transition-all cursor-pointer ${
            isFlipped
              ? 'bg-[#1C1A17] text-white border-[#1C1A17]'
              : 'bg-white hover:bg-[#FAF8F3] text-[#1C1A17] border-[#DFDBD0]'
          }`}
        >
          <ArrowUp className="w-4 h-4 stroke-[2.2]" />
          <span>Ask why</span>
        </button>

        <button
          type="button"
          onClick={() => {}}
          className="bg-white border border-[#DFDBD0] rounded-full px-5 py-2.5 text-[15px] font-medium text-[#1C1A17] shadow-sm flex items-center gap-2 cursor-default"
        >
          <ArrowDown className="w-4 h-4 text-[#1C1A17] stroke-[2.2]" />
          <span>Later</span>
        </button>

        <button
          type="button"
          onClick={() => {}}
          className="bg-white border border-[#DFDBD0] rounded-full px-5 py-2.5 text-[15px] font-medium text-[#1C1A17] shadow-sm flex items-center gap-2 cursor-default"
        >
          <ArrowRight className="w-4 h-4 text-[#1D7A4C] stroke-[2.2]" />
          <span>Approve</span>
        </button>
      </div>
    </div>
  );
}
