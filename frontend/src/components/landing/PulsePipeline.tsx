"use client";

import { motion, useAnimationControls } from "framer-motion";
import { useEffect } from "react";

export function PulsePipeline() {
  const card1 = useAnimationControls();
  const card2 = useAnimationControls();
  const card3 = useAnimationControls();
  const arrow1 = useAnimationControls();
  const arrow2 = useAnimationControls();
  const icon3 = useAnimationControls();

  useEffect(() => {
    let isActive = true;

    const sequence = async () => {
      // Initialize state to dims
      if (!isActive) return;
      card1.set({ opacity: 0.4, borderColor: "var(--outline-variant)" });
      card2.set({ opacity: 0.4, borderColor: "var(--outline-variant)" });
      card3.set({ opacity: 0.4, borderColor: "var(--outline-variant)" });
      arrow1.set({ opacity: 0.4, color: "var(--outline-variant)" });
      arrow2.set({ opacity: 0.4, color: "var(--outline-variant)" });
      icon3.set({ scale: 1 });

      while (isActive) {
        // Step 1: Ingestion (0s to 1s)
        card1.start({ opacity: 1, borderColor: "var(--primary)", transition: { duration: 0.4 } });
        arrow1.start({ opacity: 1, color: "var(--primary)", transition: { duration: 0.4 } });
        await new Promise((r) => setTimeout(r, 1000));
        if (!isActive) break;

        // Step 2: Retrieval (1s to 2s)
        card1.start({ opacity: 0.4, borderColor: "var(--outline-variant)", transition: { duration: 0.4 } });
        card2.start({ 
          opacity: 1, 
          borderColor: ["var(--outline-variant)", "var(--primary)", "var(--outline-variant)", "var(--primary)", "var(--outline-variant)"], 
          transition: { duration: 1, ease: "easeInOut", times: [0, 0.25, 0.5, 0.75, 1] }
        });
        arrow1.start({ opacity: 0.4, color: "var(--outline-variant)", transition: { duration: 0.4 } });
        arrow2.start({ opacity: 1, color: "var(--primary)", transition: { duration: 0.4 } });
        await new Promise((r) => setTimeout(r, 1000));
        if (!isActive) break;

        // Step 3: Answer (2s to 3s)
        card2.start({ opacity: 0.4, borderColor: "var(--outline-variant)", transition: { duration: 0.4 } });
        card3.start({ opacity: 1, borderColor: "var(--primary)", transition: { duration: 0.4 } });
        arrow2.start({ opacity: 0.4, color: "var(--outline-variant)", transition: { duration: 0.4 } });
        icon3.start({ scale: 1.1, transition: { duration: 0.4, type: "spring", stiffness: 300 } });
        await new Promise((r) => setTimeout(r, 1000));
        if (!isActive) break;

        // Step 4: Reset (3s to 4s)
        card3.start({ opacity: 0.4, borderColor: "var(--outline-variant)", transition: { duration: 0.4 } });
        icon3.start({ scale: 1, transition: { duration: 0.4 } });
        await new Promise((r) => setTimeout(r, 1000));
      }
    };

    sequence();

    return () => {
      isActive = false;
    };
  }, [card1, card2, card3, arrow1, arrow2, icon3]);

  return (
    <div className="flex flex-col md:flex-row items-center justify-center gap-4 md:gap-8 max-w-4xl mx-auto w-full font-sans">
      {/* Step 1 */}
      <motion.div 
        animate={card1}
        className="flex-1 flex flex-col items-center p-6 bg-surface-elevated rounded-2xl border-2 border-outline-variant/30 w-full relative transition-colors shadow-sm"
      >
        <div className="w-12 h-12 bg-surface-container text-foreground rounded-xl flex items-center justify-center mb-4 shadow-sm">
          <span className="material-symbols-outlined">folder_open</span>
        </div>
        <h4 className="font-semibold text-foreground mb-2">Your Documents</h4>
        <p className="text-sm text-muted text-center">PDFs, MDs, TXTs</p>
      </motion.div>

      <motion.span 
        animate={arrow1} 
        className="material-symbols-outlined md:rotate-0 rotate-90 text-outline-variant"
      >
        arrow_forward
      </motion.span>

      {/* Step 2 */}
      <motion.div 
        animate={card2}
        className="flex-1 flex flex-col items-center p-6 bg-surface-elevated rounded-2xl border-2 border-outline-variant/30 w-full relative transition-colors shadow-sm"
      >
        <div className="absolute -top-3 px-3 py-1 bg-primary text-on-primary text-[10px] uppercase font-bold tracking-wider rounded-full shadow-sm z-10">
          PRIVATEDOC
        </div>
        <div className="w-12 h-12 bg-surface-container text-foreground rounded-xl flex items-center justify-center mb-4 mt-2 shadow-sm">
          <span className="material-symbols-outlined">database</span>
        </div>
        <h4 className="font-semibold text-foreground mb-2">Local Retrieval</h4>
        <p className="text-sm text-muted text-center">Vector search & indexing</p>
      </motion.div>

      <motion.span 
        animate={arrow2} 
        className="material-symbols-outlined md:rotate-0 rotate-90 text-outline-variant"
      >
        arrow_forward
      </motion.span>

      {/* Step 3 */}
      <motion.div 
        animate={card3}
        className="flex-1 flex flex-col items-center p-6 bg-surface-elevated rounded-2xl border-2 border-outline-variant/30 w-full relative transition-colors shadow-sm"
      >
        <motion.div 
          animate={icon3}
          className="w-12 h-12 bg-surface-container text-foreground rounded-xl flex items-center justify-center mb-4 shadow-sm"
        >
          <span className="material-symbols-outlined">shield</span>
        </motion.div>
        <h4 className="font-semibold text-foreground mb-2">Your Answer</h4>
        <p className="text-sm text-muted text-center">Secure & cited</p>
      </motion.div>
    </div>
  );
}
