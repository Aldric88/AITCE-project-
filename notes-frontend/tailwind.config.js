/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        background: "var(--color-background)",
        foreground: "var(--color-foreground)",
        primary: "#000000",
        "primary-foreground": "#ffffff",
        muted: "var(--color-muted)",
        "muted-foreground": "var(--color-muted-foreground)",
        border: "var(--color-border)",
        ring: "#000000",
        surface: "var(--color-surface)",
        "surface-raised": "var(--color-surface-raised)",
      },
      borderRadius: {
        lg: "0px",
        md: "0px",
        sm: "0px",
        default: "0px",
        none: "0px",
      },
    },
  },
  plugins: [],
};
