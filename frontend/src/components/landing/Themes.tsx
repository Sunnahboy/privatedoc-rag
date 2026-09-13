"use client";

import { useState } from "react";

const themes = [
  { id: "light", label: "Paper", icon: "light_mode" },
  { id: "dark", label: "Dark", icon: "dark_mode" },
  { id: "oled", label: "OLED", icon: "contrast" },
  { id: "sepia", label: "Sepia", icon: "local_cafe" },
  { id: "matcha", label: "Matcha", icon: "eco" },
];

export function Themes() {
  const [activeTheme, setActiveTheme] = useState("sepia");

  return (
    <section id="themes" className="py-24 bg-surface">
      <div className="max-w-[1000px] mx-auto px-6">
        <div className="text-center mb-16">
          <h2 className="text-sm font-bold tracking-widest text-primary uppercase mb-3 font-sans">Themes</h2>
          <h3 className="font-serif text-4xl font-semibold mb-4 text-foreground">
            A reading environment for every mood.
          </h3>
          <p className="text-lg text-muted font-sans max-w-2xl mx-auto">
            Native support for carefully crafted themes to reduce eye strain and match your preferred aesthetic.
          </p>
        </div>

        {/* Theme Selector */}
        <div className="flex flex-wrap justify-center gap-3 mb-12">
          {themes.map((theme) => (
            <button
              key={theme.id}
              onClick={() => setActiveTheme(theme.id)}
              className={`px-5 py-2.5 rounded-full text-sm font-medium transition-all flex items-center gap-2 border ${
                activeTheme === theme.id
                  ? "bg-primary text-on-primary border-primary shadow-md scale-105"
                  : "bg-surface-elevated text-foreground border-outline-variant hover:bg-surface-container"
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">{theme.icon}</span>
              {theme.label}
            </button>
          ))}
        </div>

        {/* Theme Preview Container */}
        {/* We use data-theme here to locally scope the CSS variables from globals.css */}
        <div 
          data-theme={activeTheme !== "light" ? activeTheme : undefined}
          className="rounded-2xl overflow-hidden border border-outline-variant/30 shadow-2xl transition-colors duration-700 max-w-4xl mx-auto"
          style={{ backgroundColor: 'var(--background)' }}
        >
          <div className="p-4 border-b border-outline-variant/20 flex items-center gap-4" style={{ backgroundColor: 'var(--surface)' }}>
             <div className="flex gap-1.5">
               <div className="w-3 h-3 rounded-full bg-outline-variant/50"></div>
               <div className="w-3 h-3 rounded-full bg-outline-variant/50"></div>
               <div className="w-3 h-3 rounded-full bg-outline-variant/50"></div>
             </div>
             <div className="text-xs font-medium font-sans opacity-60" style={{ color: 'var(--foreground)' }}>Reading Mode</div>
          </div>
          <div className="p-10 md:p-16 transition-colors duration-700" style={{ backgroundColor: 'var(--reader-surface)', color: 'var(--foreground)' }}>
            <h2 className="font-serif text-3xl mb-6 font-semibold">The Philosophy of Focused Work</h2>
            <div className="space-y-4 font-serif text-lg leading-relaxed opacity-90">
              <p>
                In an age of continuous interruption, the ability to concentrate intensely on a single complex task is a rare and valuable skill.
              </p>
              <p>
                A well-designed tool should disappear, allowing the content itself to take center stage. Typography, spacing, and color all play a crucial role in cognitive load.
              </p>
              <div className="mt-8 p-4 rounded-xl border-l-4 transition-colors duration-700" style={{ backgroundColor: 'var(--surface-container)', borderColor: 'var(--primary)', color: 'var(--foreground)' }}>
                <p className="text-sm font-sans font-medium mb-1" style={{ color: 'var(--primary)' }}>Highlight</p>
                <p className="text-base italic">&quot;The interface is not the product. The understanding you gain is the product.&quot;</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

