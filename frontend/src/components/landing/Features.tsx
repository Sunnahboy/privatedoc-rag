"use client";

export function Features() {
  return (
    <div className="py-24 bg-surface flex flex-col gap-32">
      {/* SECTION 2 - THE PROBLEM */}
      <section className="max-w-4xl mx-auto px-6 text-center">
        <h2 className="font-serif text-3xl md:text-5xl mb-6 text-foreground font-medium">
          Some documents are meant to be read. <br className="hidden md:block" />
          <span className="text-muted">Others are meant to be understood.</span>
        </h2>
        <p className="text-lg md:text-xl text-muted font-sans max-w-2xl mx-auto leading-relaxed">
          Long PDFs, dense research papers, and complex documentation shouldn&apos;t feel like a barrier. PrivateDoc transforms static pages into an interactive workspace.
        </p>
      </section>

      {/* SECTION 3 - READ */}
      <section id="read" className="max-w-[1200px] mx-auto px-6 grid md:grid-cols-2 gap-16 items-center">
        <div className="order-2 md:order-1 bg-reader-surface rounded-2xl p-8 border border-outline-variant/30 shadow-sm min-h-[400px] flex items-center justify-center relative overflow-hidden">
           <div className="absolute inset-0 opacity-20 bg-[radial-gradient(circle_at_center,var(--primary)_1px,transparent_1px)] bg-[size:24px_24px]"></div>
           <div className="bg-surface-elevated w-full max-w-sm rounded-lg shadow-xl border border-outline-variant/40 p-6 z-10 font-serif transform transition-transform hover:scale-[1.02] duration-500">
              <h3 className="text-xl font-bold mb-4">Focus Mode</h3>
              <p className="text-muted leading-relaxed mb-4">
                Distraction-free reading environment that respects your eyes with native theme support.
              </p>
              <div className="h-2 bg-surface-container rounded w-full mb-2"></div>
              <div className="h-2 bg-surface-container rounded w-5/6 mb-2"></div>
              <div className="h-2 bg-surface-container rounded w-4/6"></div>
           </div>
        </div>
        <div className="order-1 md:order-2">
          <h2 className="text-sm font-bold tracking-widest text-primary uppercase mb-3 font-sans">Read</h2>
          <h3 className="font-serif text-4xl md:text-5xl font-semibold mb-6 text-foreground">
            Read without leaving the document.
          </h3>
          <p className="text-lg text-muted font-sans leading-relaxed">
            Experience a premium reading environment. Fluidly switch between full document view, focused reading mode, and side-by-side chat without losing your place.
          </p>
        </div>
      </section>

      {/* SECTION 4 - ASK */}
      <section id="ask" className="max-w-[1200px] mx-auto px-6 grid md:grid-cols-2 gap-16 items-center">
        <div>
          <h2 className="text-sm font-bold tracking-widest text-primary uppercase mb-3 font-sans">Ask</h2>
          <h3 className="font-serif text-4xl md:text-5xl font-semibold mb-6 text-foreground">
            Ask the document.
          </h3>
          <p className="text-lg text-muted font-sans leading-relaxed">
            Stop Cmd+F searching. Ask complex questions and get precise answers backed by exact citations. Click any source to jump instantly to the highlighted paragraph in the original file.
          </p>
        </div>
        <div className="bg-chat-surface rounded-2xl p-8 border border-outline-variant/30 shadow-sm min-h-[400px] flex items-center justify-center relative">
          <div className="w-full max-w-sm space-y-4 z-10">
            <div className="flex justify-end">
              <div className="bg-primary text-on-primary px-4 py-3 rounded-2xl rounded-tr-sm text-sm">
                What is the main conclusion?
              </div>
            </div>
            <div className="flex justify-start">
              <div className="bg-surface-elevated border border-outline-variant/30 px-4 py-3 rounded-2xl rounded-tl-sm text-sm shadow-sm">
                <p className="mb-3 text-foreground leading-relaxed">The study concludes that localized retrieval significantly reduces hallucination rates in specialized domains.</p>
                <div className="flex items-center gap-1.5 bg-surface-container-low px-2 py-1 rounded border border-outline-variant/30 text-xs text-muted w-fit cursor-pointer hover:bg-surface-container transition-colors">
                  <span className="material-symbols-outlined text-[14px]">find_in_page</span>
                  Page 12
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 5 - CONNECT & SECTION 6 - CONVERSATIONS */}
      <section className="max-w-[1200px] mx-auto px-6">
        <div className="grid md:grid-cols-2 gap-8">
          {/* CONNECT */}
          <div id="connect" className="bg-surface-container-low rounded-3xl p-10 border border-outline-variant/30">
            <h2 className="text-sm font-bold tracking-widest text-primary uppercase mb-3 font-sans">Connect</h2>
            <h3 className="font-serif text-3xl font-semibold mb-4 text-foreground">One question.<br/>Multiple documents.</h3>
            <p className="text-muted font-sans mb-8">
              Select an entire folder or your whole library. PrivateDoc retrieves evidence across multiple files, synthesizing answers from diverse sources.
            </p>
            <div className="flex gap-2 flex-wrap">
              <span className="px-3 py-1.5 bg-surface-elevated border border-outline-variant/40 rounded-lg text-xs font-medium shadow-sm flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[14px] text-primary">description</span> Q1 Report.pdf
              </span>
              <span className="px-3 py-1.5 bg-surface-elevated border border-outline-variant/40 rounded-lg text-xs font-medium shadow-sm flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[14px] text-primary">description</span> User Research.md
              </span>
              <span className="px-3 py-1.5 bg-surface-elevated border border-outline-variant/40 rounded-lg text-xs font-medium shadow-sm flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[14px] text-primary">description</span> Competitor Analysis.pdf
              </span>
            </div>
          </div>

          {/* CONVERSATIONS */}
          <div id="memory" className="bg-surface-container-low rounded-3xl p-10 border border-outline-variant/30">
            <h2 className="text-sm font-bold tracking-widest text-primary uppercase mb-3 font-sans">Memory</h2>
            <h3 className="font-serif text-3xl font-semibold mb-4 text-foreground">Your research has <br/>a memory.</h3>
            <p className="text-muted font-sans mb-8">
              Every chat is saved as a persistent conversation thread. Pick up where you left off, switch contexts instantly, and never lose your train of thought.
            </p>
            <div className="space-y-2">
              <div className="p-3 bg-surface-elevated border border-outline-variant/40 rounded-xl shadow-sm text-sm font-medium flex justify-between items-center">
                <span>Analysis of Q1 Trends</span>
                <span className="text-xs text-muted font-normal">2d ago</span>
              </div>
              <div className="p-3 bg-surface-elevated/50 border border-outline-variant/20 rounded-xl text-sm font-medium flex justify-between items-center text-muted">
                <span>Literature Review: Transformers</span>
                <span className="text-xs font-normal">5d ago</span>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

