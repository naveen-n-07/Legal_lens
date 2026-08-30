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
          900: '#0B1325',
          800: '#152238',
          700: '#1E293B',
        },
        gov: {
          crimson: '#D32F2F',
          red: '#C62828',
          darkred: '#B71C1C',
          saffron: '#FF9933',
          green: '#138808',
          navy: '#1A365D',
          blue: '#1E40AF',
          lightbg: '#F8FAFC',
        }
      }
    },
  },
  plugins: [],
}
