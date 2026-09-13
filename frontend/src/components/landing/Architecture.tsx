"use client";

import { motion } from "framer-motion";
import { PulsePipeline } from "./PulsePipeline";

export function Architecture() {
  return (
    <section id="privacy" className="py-24 bg-background border-t border-b border-outline-variant/20 overflow-hidden text-foreground">
      <div className="max-w-[1000px] mx-auto px-6 text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
        >
          <h2 className="text-sm font-bold tracking-widest text-primary uppercase mb-3 font-sans">Private</h2>
          <h3 className="font-serif text-4xl md:text-5xl font-semibold mb-6 text-foreground">
            Your documents.<br />Your workspace.
          </h3>
          <p className="text-lg text-muted font-sans max-w-2xl mx-auto leading-relaxed mb-16">
            PrivateDoc is designed for privacy. Your documents stay within your environment. No training on your data, no unauthorized external access. Just local retrieval and secure intelligence.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          <PulsePipeline />
        </motion.div>
      </div>
    </section>
  );
}
