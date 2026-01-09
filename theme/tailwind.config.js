/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./**/templates/**/*.html",
    "./static/**/*.js",
  ],
  theme: {
    extend: {
      borderRadius: {
        xl: "0.9rem",
        "2xl": "1.1rem",
      },
      boxShadow: {
        soft: "0 1px 2px rgba(0,0,0,0.06), 0 8px 24px rgba(0,0,0,0.06)",
      },
      colors: {
        ink: {
          50: "#F7F6F4",
          100: "#EEECE7",
          200: "#E1DED7",
          300: "#CFCBC2",
          400: "#9E9A92",
          500: "#6B6964",
          600: "#4F4D49",
          700: "#363433",
          800: "#1F1E1D",
          900: "#111418",
        },
        brand: {
          50: "#F7F8FB",
          100: "#EEF1F7",
          200: "#D9DEED",
          300: "#BAC5E0",
          400: "#8B98CA",
          DEFAULT: "#1F2A44",
          700: "#182035",
          800: "#14192B",
        },
        accent: {
          50: "#EDF8F4",
          100: "#D3F0E8",
          DEFAULT: "#1F7A5A",
          700: "#176047",
        },
        success: {
          DEFAULT: "#1F9D55",
        },
        warning: {
          DEFAULT: "#D97706",
        },
        danger: {
          DEFAULT: "#DC2626",
          700: "#B91C1C",
        },
        surface: {
          DEFAULT: "#FFFFFF",
          muted: "#F6F5F2",
        },
      },
    },
  },
  plugins: [],
};
