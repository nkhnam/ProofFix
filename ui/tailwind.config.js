/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["-apple-system", "Segoe UI", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "Consolas", "monospace"],
      },
      colors: {
        bg: "#0d0f12",
        surface: "#141720",
        "surface-2": "#1c2030",
        border: "#252a38",
        "border-2": "#2e3448",
        text: "#e2e8f0",
        muted: "#64748b",
        accent: "#3b82f6",
        "accent-dim": "#1d4ed8",
        success: "#22c55e",
        "success-dim": "#16a34a",
        danger: "#ef4444",
        "danger-dim": "#dc2626",
        warning: "#f59e0b",
        purple: "#a78bfa",
      },
    },
  },
  plugins: [],
};
