/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        campus: {
          sidebar: "#090d16",
          primary: "#4f46e5",
          "primary-hover": "#4338ca",
          "primary-light": "#eef2ff",
          canvas: "#f8fafc",
          card: "#ffffff",
          border: "#e2e8f0",
          "border-dark": "rgba(255, 255, 255, 0.08)",
          text: "#0f172a",
          muted: "#64748b",
          light: "#94a3b8",
          success: "#10b981",
          warning: "#f59e0b",
          danger: "#ef4444",
        },
      },
      fontFamily: {
        sans: ['Manrope', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
