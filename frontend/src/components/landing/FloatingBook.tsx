"use client";

import { motion } from "framer-motion";

export function FloatingBook({ position, delay = 0 }: { position: "left" | "right", delay?: number }) {
  const isLeft = position === "left";
  
  return (
    <motion.div
      className={`absolute top-[40%] z-0 hidden lg:block opacity-60 blur-[2px] hover:blur-none hover:opacity-100 transition-all duration-700 ${
        isLeft ? "left-[-8%] xl:left-0" : "right-[-8%] xl:right-0"
      }`}
      style={{ perspective: "1500px", y: "-50%" }}
    >
      <motion.div
        className="relative w-32 h-48 xl:w-40 xl:h-56"
        style={{ 
          transformStyle: "preserve-3d",
          rotateY: isLeft ? 35 : -35,
          rotateX: 15,
          rotateZ: isLeft ? -10 : 10,
        }}
      >
        {/* Back Cover */}
        <div className="absolute inset-0 bg-surface-elevated border border-outline-variant/40 rounded-r-xl shadow-2xl" />
        
        {/* Pages */}
        {[...Array(8)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute inset-y-[3px] left-[3px] right-2 bg-reader-surface border border-outline-variant/20 rounded-r-lg origin-left shadow-sm"
            style={{ 
              transformStyle: "preserve-3d",
              rotateY: isLeft ? -10 - (i * 2) : 10 + (i * 2),
            }}
          >
             <div className="absolute inset-6 space-y-3 opacity-30">
               <div className="h-1 bg-outline-variant rounded w-full"></div>
               <div className="h-1 bg-outline-variant rounded w-5/6"></div>
               <div className="h-1 bg-outline-variant rounded w-4/6"></div>
               <div className="h-1 bg-outline-variant rounded w-5/6 mt-6"></div>
             </div>
          </motion.div>
        ))}

        {/* Front Cover */}
        <motion.div
          className="absolute inset-0 bg-surface-elevated border border-outline-variant/40 rounded-r-xl shadow-xl origin-left flex items-center justify-center overflow-hidden"
          style={{ 
            transformStyle: "preserve-3d",
            rotateY: isLeft ? -30 : 30,
          }}
        >
          {/* Spine shadow for depth */}
          <div className="w-8 h-full absolute left-0 bg-gradient-to-r from-black/20 dark:from-black/40 to-transparent" />
          <div className="w-full h-full bg-gradient-to-tr from-transparent to-white/5 dark:to-white/10" />
          
          {/* Cover Design */}
          <div className="absolute inset-6 border border-outline-variant/30 rounded-md flex flex-col items-center justify-center bg-surface-container/30">
            <div className="w-10 h-10 rounded-full border border-outline-variant/40 flex items-center justify-center mb-3 bg-surface">
              <span className="text-foreground text-sm font-serif italic">P</span>
            </div>
            <div className="h-1 bg-outline-variant/50 rounded w-1/2"></div>
          </div>
        </motion.div>
      </motion.div>
    </motion.div>
  );
}

