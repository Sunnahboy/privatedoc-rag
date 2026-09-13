"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";

// ─────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────


// ─────────────────────────────────────────────
// Main HeroPreview
// ─────────────────────────────────────────────

export function HeroPreview() {
  const router = useRouter();
  const [phase, setPhase] = useState<0 | 1 | 2 | 3 | 4 | 5>(1);
  const [typedQuestion, setTypedQuestion] = useState("");
  const [typedAnswer, setTypedAnswer] = useState("");
  const [typedSearch, setTypedSearch] = useState("");
  const [isFadingOut, setIsFadingOut] = useState(false);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  const QUESTION_TEXT = "Explain this page";
  const ANSWER_TEXT =
    "The indexing pipeline is decoupled from the retrieval API. This isolation ensures ingestion spikes don't block user queries.";
  const SEARCH_TEXT = "pipeline isolation";


  const handleSignupRedirect = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    router.push('/signup');
  };

  useEffect(() => {
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    setPrefersReducedMotion(prefersReduced);

    if (prefersReduced) {
      const t = setTimeout(() => {
        setPhase(4);
        setTypedQuestion(QUESTION_TEXT);
        setTypedAnswer(ANSWER_TEXT);
      }, 0);
      return () => clearTimeout(t);
    }
  }, []);

  // Typing effect runner bound to phase state
  useEffect(() => {
    let isMounted = true;
    let timeouts: NodeJS.Timeout[] = [];
    
    const typeText = async (
      text: string, 
      setter: React.Dispatch<React.SetStateAction<string>>, 
      delayMs: number
    ) => {
      setter("");
      for (let i = 1; i <= text.length; i++) {
        if (!isMounted) break;
        setter(text.substring(0, i));
        await new Promise((r) => {
          const t = setTimeout(r, delayMs);
          timeouts.push(t);
        });
      }
    };

    if (phase === 1) {
      setTypedQuestion("");
      setTypedAnswer("");
      setTypedSearch("");
      setIsFadingOut(false);
      // 0.4 * 2.5s = 1.0s for cursor to arrive. Start typing at 1.1s.
      const t1 = setTimeout(() => {
        void typeText(SEARCH_TEXT, setTypedSearch, 40);
      }, 1100);
      timeouts.push(t1);
    } else if (phase === 3) {
      // 0.4 * 2.0s = 0.8s for cursor to arrive. Click at 0.9s.
      const t2 = setTimeout(() => {
        setTypedQuestion(QUESTION_TEXT);
        setTypedAnswer("");
      }, 900);
      timeouts.push(t2);
    } else if (phase === 4) {
      // Type answer instantly upon entering phase 4
      void typeText(ANSWER_TEXT, setTypedAnswer, 15);
    }

    return () => {
      isMounted = false;
      timeouts.forEach(clearTimeout);
    };
  }, [phase]);

  return (
    <div
      className="w-full relative min-h-[500px] md:min-h-[680px] flex items-center justify-center overflow-hidden bg-transparent"
    >

      {/* ── PHASE 1-5: WORKSPACE TIMELINE SEQUENCER ────────────────────── */}
      {phase >= 1 && !isFadingOut && (
        <motion.div
          initial="phase0"
          animate={`phase${phase}`}
          variants={{
            phase0: { opacity: 0.99 },
            phase1: { opacity: 1, transition: { duration: 2.5 } }, // Search Interaction
            phase2: { opacity: 0.99, transition: { duration: 2.0 } }, // Tab Switching
            phase3: { opacity: 1, transition: { duration: 2.0 } }, // Action Execution
            phase4: { opacity: 0.99, transition: { duration: 4.0 } }, // Evidence Reveal
            phase5: { opacity: 1, transition: { duration: 0.5 } }, // Hold & Reset
          }}
          onAnimationComplete={(v) => {
            if (v === "phase1") setPhase(2);
            else if (v === "phase2") setPhase(3);
            else if (v === "phase3") setPhase(4);
            else if (v === "phase4") setPhase(5);
            else if (v === "phase5") {
              setIsFadingOut(true);
              setTimeout(() => setPhase(1), 800); // Trigger loop reset
            }
          }}
        />
      )}

      {/* ── PHASE 1-5: WORKSPACE UI ──────────────────────────────────────── */}
      <motion.div
        className="w-full max-w-6xl h-full bg-surface-elevated rounded-2xl shadow-[0_20px_60px_-15px_rgba(0,0,0,0.25)] border border-outline-variant/30 flex flex-col relative z-10 text-left overflow-hidden"
        initial={{ opacity: 0, y: 16, scale: 0.97 }}
        animate={{
          opacity: phase >= 1 && !isFadingOut ? 1 : 0,
          y: phase >= 1 && !isFadingOut ? 0 : 16,
          scale: phase >= 1 && !isFadingOut ? 1 : 0.97,
        }}
        transition={{ duration: 0.6, ease: [0.2, 0, 0, 1] }}
      >
        {/* Animated Software Cursor */}
        <motion.div
          className="absolute z-[100] pointer-events-none drop-shadow-md hidden md:block"
          initial={{ opacity: 0, left: "90%", top: "90%" }}
          animate={{
            opacity: (phase >= 1 && phase <= 3 && !prefersReducedMotion) ? 1 : 0,
            left: phase === 1 ? ["90%", "44%", "44%"] : phase === 2 ? ["44%", "50%", "50%"] : phase === 3 ? ["50%", "78%", "78%"] : "90%",
            top: phase === 1 ? ["90%", "13%", "13%"] : phase === 2 ? ["13%", "4%", "4%"] : phase === 3 ? ["4%", "60%", "60%"] : "90%",
            scale: phase === 1 ? [1, 1, 0.8, 1] : phase === 2 ? [1, 1, 0.8, 1] : phase === 3 ? [1, 1, 0.8, 1] : 1,
          }}
          transition={{
            duration: phase === 1 ? 2.5 : phase === 2 ? 2.0 : phase === 3 ? 2.0 : 1.0,
            times: phase === 1 ? [0, 0.4, 0.45, 1] : phase === 2 ? [0, 0.4, 0.45, 1] : phase === 3 ? [0, 0.4, 0.45, 1] : [0, 0.5, 1],
            ease: "easeInOut"
          }}
        >
          {/* Improved macOS-style pointer cursor SVG */}
          <svg width="28" height="28" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M8 2L24 16.5L16 18L19.5 26.5L16 28L12.5 19.5L5 24.5V2Z" fill="black" stroke="white" strokeWidth="2" strokeLinejoin="round" className="dark:fill-white dark:stroke-black" />
          </svg>
        </motion.div>

        {/* Top Header Bar */}
        <div className="h-14 border-b border-outline-variant/20 flex items-center justify-between px-4 bg-surface/50 backdrop-blur-md shrink-0">
          {/* Left: Back to Library */}
          <div className="flex items-center gap-2 text-muted hover:text-foreground cursor-pointer transition-colors text-sm font-medium w-64 hover:bg-black/5 dark:hover:bg-white/5 px-2 py-1.5 rounded-md">
            <span className="material-symbols-outlined text-[18px]">arrow_back</span>
            Back to Library
          </div>
          
          {/* Center: Segmented Control */}
          <div className="hidden md:flex bg-surface-container-low rounded-lg p-1 border border-outline-variant/30 text-xs font-medium">
            <div className={`px-4 py-1.5 cursor-pointer rounded-md transition-colors ${phase < 2 ? 'bg-surface-elevated text-primary shadow-sm' : 'text-muted hover:bg-black/5 dark:hover:bg-white/5'}`}>Full View</div>
            <div className={`px-4 py-1.5 cursor-pointer rounded-md transition-colors ${phase >= 2 ? 'bg-surface-elevated text-primary shadow-sm' : 'text-muted hover:bg-black/5 dark:hover:bg-white/5'}`}>Document Focus</div>
            <div className="px-4 py-1.5 text-muted hover:text-foreground cursor-pointer rounded-md transition-colors hover:bg-black/5 dark:hover:bg-white/5">Chat Focus</div>
          </div>

          {/* Right: Actions */}
          <div className="flex items-center justify-end gap-3 w-64">
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-outline-variant/30 text-xs font-medium text-muted cursor-pointer transition-colors hover:bg-black/5 dark:hover:bg-white/5">
              <div className="w-2.5 h-2.5 rounded-full bg-[#8A9A5B]"></div>
              Matcha
              <span className="material-symbols-outlined text-[14px]">expand_more</span>
            </div>
            <div className="px-3 py-1.5 rounded-full border border-outline-variant/30 text-xs font-medium text-muted cursor-pointer transition-colors hover:bg-black/5 dark:hover:bg-white/5">
              Hide RAG Chat
            </div>
            <div className="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center cursor-pointer transition-colors hover:bg-primary/20">
              <span className="material-symbols-outlined text-[16px]">logout</span>
            </div>
          </div>
        </div>

        <div className="flex flex-1 relative min-h-0 bg-surface">
          {/* LEFT SIDEBAR (~250px) - Collapses in Phase 2 */}
          <motion.div 
            className="hidden lg:flex border-r border-outline-variant/30 flex-col bg-surface-container-low/50 shrink-0 z-10"
            initial={{ width: 260, opacity: 1 }}
            animate={{ width: phase >= 2 ? 0 : 260, opacity: phase >= 2 ? 0 : 1 }}
            transition={{ duration: 0.5, ease: "easeInOut", delay: phase === 2 ? 0.9 : 0 }}
            style={{ overflow: 'hidden' }}
          >
            <div className="w-[260px] flex-1 flex flex-col">
              <div className="p-5 border-b border-outline-variant/20 shrink-0">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-foreground font-semibold text-xs tracking-wider uppercase">Contents</span>
                </div>
                <p className="text-[11px] text-muted leading-relaxed">Navigate by chapter, section, or starting page.</p>
              </div>
              <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
                <span className="material-symbols-outlined text-[32px] text-muted/30 mb-3">format_list_bulleted</span>
                <p className="text-[12px] text-muted/60 max-w-[180px] leading-relaxed">
                  No Table of Contents embedded in this document.
                </p>
              </div>
            </div>
          </motion.div>

          {/* CENTER CANVAS & RIGHT SIDEBAR WRAPPER */}
          <div className="flex-1 flex relative perspective-[2000px]">
            {/* DOCUMENT COLUMN */}
            <div
              className={`absolute inset-0 transition-all duration-700 ease-in-out overflow-hidden flex flex-col bg-reader-surface ${
                phase >= 1 ? "right-1/2 md:right-[400px] border-r border-outline-variant/20" : "right-0"
              }`}
            >
              {/* Document Header */}
              <div className="h-12 border-b border-outline-variant/10 flex items-center justify-between px-5 shrink-0 bg-reader-surface/90 backdrop-blur z-20">
                <div className="text-xs font-medium text-muted bg-surface-container/50 px-3 py-1 rounded-full whitespace-nowrap">
                  Page 2 of 27
                </div>
                
                {/* Search Bar Pill */}
                <div 
                  className={`flex-1 max-w-[240px] mx-4 flex items-center bg-surface border rounded-full px-3 py-1.5 cursor-pointer transition-all ${phase === 1 ? 'border-primary ring-1 ring-primary/50' : 'border-outline-variant/40 hover:border-gray-400'} relative`}
                  onClick={handleSignupRedirect}
                >
                  <span className="material-symbols-outlined text-[14px] text-muted mr-2">search</span>
                  <span className={`text-[11px] flex-1 truncate ${typedSearch ? 'text-foreground' : 'text-muted'}`}>
                    {typedSearch || "Search document..."}
                  </span>
                  <span className="text-[9px] font-mono bg-surface-container text-muted px-1.5 py-0.5 rounded border border-outline-variant/30 ml-2">⌘K</span>
                  
                  {/* Inline Match Badge */}
                  <AnimatePresence>
                    {typedSearch === SEARCH_TEXT && (
                      <motion.div
                        initial={{ opacity: 0, y: 5 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        className="absolute top-full mt-2 left-0 right-0 bg-surface-elevated border border-outline-variant/30 shadow-lg rounded-md px-3 py-2 text-[10px] text-primary font-medium text-center z-50"
                      >
                        Found in §1.2
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>

                <div className="flex items-center gap-1 text-xs font-medium text-primary cursor-pointer hover:opacity-80 transition-opacity whitespace-nowrap">
                  <span className="material-symbols-outlined text-[16px]">tune</span>
                  <span className="hidden xl:inline">Expand reader controls</span>
                </div>
              </div>

              {/* Document Body */}
              <div className="flex-1 relative overflow-y-auto p-8 md:p-12 custom-scrollbar">
                <div className="max-w-2xl mx-auto">
                  <h2 className="font-serif text-2xl font-semibold mb-6 text-foreground">
                    1. System Architecture
                  </h2>
                  <div className="space-y-5 font-serif text-[15px] leading-relaxed text-foreground/85">
                    <p>
                      The system is designed with a strict separation of concerns to maintain high availability and robust performance during peak loads.
                    </p>

                    {/* Highlighted paragraph with annotation pin */}
                    <div className="relative pl-16 inline-block w-full">
                      {/* Pin (Appears sliding in Phase 4) */}
                      <motion.div
                        className="absolute left-0 top-1"
                        initial={{ opacity: 0, x: -10 }}
                        animate={{
                          opacity: (phase === 4 && typedAnswer.length === ANSWER_TEXT.length) ? 1 : 0,
                          x: (phase === 4 && typedAnswer.length === ANSWER_TEXT.length) ? 0 : -10,
                        }}
                        transition={{ duration: 0.5, ease: "easeOut" }}
                      >
                        <div className="flex items-center gap-1 bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300 border border-amber-300/60 dark:border-amber-700/50 px-1.5 py-0.5 rounded shadow-sm text-[10px] font-bold tracking-wide">
                          <span className="material-symbols-outlined text-[12px]">keep</span>
                          #1.2
                        </div>
                      </motion.div>

                      {/* Highlighted text (Wipes left-to-right in Phase 4) */}
                      <div className="relative rounded px-2 py-1 -mx-2 inline-block">
                        <motion.div
                          className="absolute inset-0 bg-amber-400/25 dark:bg-amber-400/20 rounded origin-left"
                          initial={{ scaleX: 0 }}
                          animate={{ scaleX: (phase === 4 && typedAnswer.length === ANSWER_TEXT.length) ? 1 : 0 }}
                          transition={ prefersReducedMotion ? { duration: 0.3 } : { duration: 0.8, ease: "easeOut" } }
                        />
                        <span className="relative z-10">The indexing pipeline operates asynchronously, distinct from the retrieval API. This isolation prevents ingestion spikes from impacting query latency.</span>
                      </div>
                    </div>

                    <p>
                      This ensures that during massive ingestion jobs, user queries remain performant and unaffected by background processing constraints.
                    </p>
                    <div className="h-32 bg-surface-container/30 border border-outline-variant/20 rounded-xl flex items-center justify-center text-muted text-sm mt-8">
                      [ Architecture Diagram ]
                    </div>
                  </div>
                </div>
              </div>

              {/* CSS 3D Page Flip Animation */}
              <div
                className="absolute inset-y-0 right-0 w-full bg-reader-surface origin-left shadow-[-15px_0_30px_rgba(0,0,0,0.08)] border-l border-outline-variant/10 overflow-hidden"
                style={{
                  transform: `rotateY(${phase === 0 ? "0deg" : "-180deg"})`,
                  transition: "transform 1.2s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.4s 1.0s",
                  opacity: phase >= 2 ? 0 : 1, // Hide after flip
                  backfaceVisibility: "hidden",
                  zIndex: 30
                }}
              >
                <div className="p-12 opacity-60">
                  <div className="h-6 bg-outline-variant/20 rounded w-1/3 mb-8"></div>
                  <div className="space-y-4">
                    <div className="h-4 bg-outline-variant/20 rounded w-full"></div>
                    <div className="h-4 bg-outline-variant/20 rounded w-5/6"></div>
                    <div className="h-4 bg-outline-variant/20 rounded w-4/6"></div>
                  </div>
                </div>
              </div>
            </div>

            {/* RIGHT SIDEBAR (CHAT) */}
            <motion.div
              className="absolute inset-y-0 right-0 w-1/2 md:w-[400px] bg-chat-surface flex flex-col z-20"
              initial={{ x: "100%" }}
              animate={{ x: phase >= 1 ? "0%" : "100%" }}
              transition={{ duration: 0.6, ease: [0.2, 0, 0, 1] }}
            >
              {/* Chat Header */}
              <div className="h-14 border-b border-outline-variant/20 flex items-center justify-between px-5 shrink-0 bg-surface">
                <div className="font-semibold text-foreground flex items-center gap-2">
                  <span className="material-symbols-outlined text-[18px] text-primary">chat_bubble</span>
                  RAG Chat
                </div>
                <div className="flex gap-2">
                  <div className="w-8 h-8 rounded-md hover:bg-surface-container flex items-center justify-center text-muted cursor-pointer transition-colors">
                    <span className="material-symbols-outlined text-[18px]">open_in_full</span>
                  </div>
                  <div className="w-8 h-8 rounded-md hover:bg-surface-container flex items-center justify-center text-muted cursor-pointer transition-colors">
                    <span className="material-symbols-outlined text-[18px]">delete_sweep</span>
                  </div>
                </div>
              </div>

              {/* Chat Body */}
              <div className="flex-1 flex flex-col relative overflow-hidden">
                
                {/* Empty State / Scope Toggles */}
                <motion.div 
                  className="absolute inset-0 p-5 flex flex-col"
                  animate={{ opacity: phase >= 4 ? 0 : 1 }}
                  style={{ pointerEvents: phase >= 4 ? 'none' : 'auto' }}
                >
                  <div className="mb-6">
                    <div className="text-[11px] font-semibold text-muted uppercase tracking-wider mb-3">Search Scope</div>
                    <div className="flex flex-col gap-2">
                      <div className="flex items-center justify-between p-3 rounded-lg border-2 border-primary bg-primary/5 cursor-pointer">
                        <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                          <span className="material-symbols-outlined text-[16px] text-primary">description</span>
                          This document
                        </div>
                        <div className="w-4 h-4 rounded-full border-4 border-primary"></div>
                      </div>
                      <div className="flex items-center justify-between p-3 rounded-lg border border-outline-variant/40 hover:bg-surface-container-low cursor-pointer transition-colors">
                        <div className="flex items-center gap-2 text-sm font-medium text-muted">
                          <span className="material-symbols-outlined text-[16px]">library_books</span>
                          Selected documents
                        </div>
                        <div className="w-4 h-4 rounded-full border-2 border-outline-variant"></div>
                      </div>
                      <div className="flex items-center justify-between p-3 rounded-lg border border-outline-variant/40 hover:bg-surface-container-low cursor-pointer transition-colors">
                        <div className="flex items-center gap-2 text-sm font-medium text-muted">
                          <span className="material-symbols-outlined text-[16px]">all_inclusive</span>
                          All documents
                        </div>
                        <div className="w-4 h-4 rounded-full border-2 border-outline-variant"></div>
                      </div>
                    </div>
                  </div>

                  <div className="flex-1">
                    <div className="text-[11px] font-semibold text-muted uppercase tracking-wider mb-3">Suggested Actions</div>
                    <div className="flex flex-wrap gap-2">
                      <div 
                        className="px-3 py-1.5 rounded-full border border-outline-variant/40 text-xs text-muted hover:bg-gray-50 dark:hover:bg-white/5 hover:border-gray-400 cursor-pointer transition-colors bg-surface"
                        onClick={handleSignupRedirect}
                      >
                        Ask about this book
                      </div>
                      <div 
                        className={`px-3 py-1.5 rounded-full border text-xs text-muted cursor-pointer transition-all bg-surface relative ${phase === 3 ? 'ring-1 ring-primary/50 border-primary bg-gray-50 dark:bg-white/5' : 'border-outline-variant/40 hover:bg-gray-50 dark:hover:bg-white/5 hover:border-gray-400'}`}
                        onClick={handleSignupRedirect}
                      >
                        Explain this page
                      </div>
                      <div 
                        className="px-3 py-1.5 rounded-full border border-outline-variant/40 text-xs text-muted hover:bg-gray-50 dark:hover:bg-white/5 hover:border-gray-400 cursor-pointer transition-colors bg-surface"
                        onClick={handleSignupRedirect}
                      >
                        Summarize this section
                      </div>
                    </div>
                  </div>
                </motion.div>

                {/* Chat Stream Area */}
                <div className="absolute inset-0 p-5 overflow-y-auto flex flex-col gap-6" style={{ pointerEvents: phase >= 4 ? 'auto' : 'none' }}>
                  <AnimatePresence>
                    {phase >= 4 && (
                      <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, transition: { duration: 0.2 } }}
                        className="flex justify-end"
                      >
                        <div className="bg-primary text-on-primary px-4 py-3 rounded-2xl rounded-tr-sm max-w-[85%] text-[13px] shadow-sm leading-relaxed">
                          {typedQuestion}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  <AnimatePresence>
                    {phase >= 4 && typedAnswer.length > 0 && (
                      <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, transition: { duration: 0.2 } }}
                        className="flex justify-start"
                      >
                        <div className="bg-surface-elevated border border-outline-variant/30 p-4 rounded-2xl rounded-tl-sm max-w-[95%] text-[13px] leading-relaxed shadow-sm">
                          <p className="text-foreground/90">
                            {typedAnswer}
                            {typedAnswer.length < ANSWER_TEXT.length && (
                              <span className="inline-block w-1.5 h-3.5 bg-primary ml-1 animate-pulse align-middle" />
                            )}
                          </p>
                          
                          {/* Citation Pulse */}
                          <motion.div
                            animate={{ opacity: (phase === 4 && typedAnswer.length === ANSWER_TEXT.length) ? 1 : 0 }}
                            className="mt-3 pt-3 border-t border-outline-variant/20 flex gap-2"
                          >
                            <motion.div 
                              className="inline-flex items-center gap-1.5 bg-surface-container text-muted px-2.5 py-1.5 rounded-md border border-outline-variant/30 text-[10px] font-semibold tracking-wide cursor-pointer hover:bg-gray-50 dark:hover:bg-white/5 transition-colors"
                              animate={ (phase === 4 && typedAnswer.length === ANSWER_TEXT.length) ? { 
                                scale: [1, 1.05, 1], 
                                boxShadow: ["0px 0px 0px rgba(245,158,11,0)", "0px 0px 12px rgba(245,158,11,0.5)", "0px 0px 0px rgba(245,158,11,0)"] 
                              } : {}}
                              transition={{ duration: 1.0, ease: "easeInOut", repeat: Infinity, repeatType: "reverse" }}
                            >
                              <span className="material-symbols-outlined text-[13px]">description</span>
                              Doc 1 · Page 2
                            </motion.div>
                          </motion.div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>

              </div>

              {/* Bottom Input Area */}
              <div className="p-4 border-t border-outline-variant/20 bg-surface shrink-0">
                <div 
                  className="relative flex items-center bg-surface-container-low border border-outline-variant/40 rounded-xl overflow-hidden focus-within:border-primary/50 transition-colors hover:border-gray-400 cursor-text"
                  onClick={handleSignupRedirect}
                >
                  <div className="pl-3 pr-2 text-muted hover:text-foreground cursor-pointer transition-colors">
                    <span className="material-symbols-outlined text-[20px]">mic</span>
                  </div>
                  <input 
                    type="text" 
                    placeholder="Ask a question..."
                    className="flex-1 bg-transparent py-3 text-sm focus:outline-none text-foreground placeholder:text-muted/60 pointer-events-none"
                    readOnly
                  />
                  <div className="pr-2">
                    <div 
                      className="w-8 h-8 rounded-lg bg-primary text-on-primary flex items-center justify-center cursor-pointer hover:opacity-90 transition-opacity"
                      onClick={handleSignupRedirect}
                    >
                      <span className="material-symbols-outlined text-[18px]">arrow_upward</span>
                    </div>
                  </div>
                </div>
                <div className="text-center text-[10px] text-muted/50 mt-2">
                  AI can make mistakes. Verify important information.
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </motion.div>

      {/* Keyframes */}
      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes pulse-slow {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.7; }
        }
        .animate-pulse-slow { animation: pulse-slow 2.5s ease-in-out infinite; }
      ` }} />
    </div>
  );
}
