/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          900: '#0F172A',
          800: '#1E293B',
          700: '#334155',
        },
        gov: {
          blue: '#2563EB',
          indigo: '#312E81',
          green: '#16A34A',
          amber: '#D97706',
          red: '#DC2626',
        }
      }
    },
  },
  plugins: [],
}
