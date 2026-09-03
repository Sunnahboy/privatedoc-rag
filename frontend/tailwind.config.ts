import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        primary: "var(--primary)",
        "on-primary": "var(--on-primary)",
        surface: "var(--surface)",
        "surface-container": "var(--surface-container)",
        "surface-container-low": "var(--surface-container-low)",
        "surface-elevated": "var(--surface-elevated)",
        "reader-surface": "var(--reader-surface)",
        "chat-surface": "var(--chat-surface)",
        "chat-focus": "var(--chat-focus)",
        "chat-input": "var(--chat-input)",
        muted: "var(--muted)",
        outline: "var(--outline)",
        "outline-variant": "var(--outline-variant)",
        error: "var(--error)",
      },
    },
  },
  plugins: [],
};

export default config;
