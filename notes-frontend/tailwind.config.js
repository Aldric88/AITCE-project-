/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        background: "#ffffff",
        foreground: "#000000",
        primary: "#000000",
        "primary-foreground": "#ffffff",
        muted: "#f3f4f6",
        "muted-foreground": "#6b7280",
        border: "#e5e7eb",
        ring: "#000000",
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
