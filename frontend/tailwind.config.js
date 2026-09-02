/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontSize: {
        '2xs': ['0.75rem', { lineHeight: '1.125rem' }], // 12px
        'xs': ['0.875rem', { lineHeight: '1.25rem' }],   // 14px (comfortably readable secondary)
        'sm': ['0.9375rem', { lineHeight: '1.375rem' }], // 15px (medium body/controls)
        'base': ['1rem', { lineHeight: '1.5rem' }],       // 16px (standard baseline)
        'md': ['1.0625rem', { lineHeight: '1.5rem' }],    // 17px
        'lg': ['1.125rem', { lineHeight: '1.75rem' }],    // 18px (card titles/emphasis)
        'xl': ['1.25rem', { lineHeight: '1.75rem' }],     // 20px (H3)
        '2xl': ['1.5rem', { lineHeight: '2rem' }],        // 24px (H2)
        '3xl': ['1.875rem', { lineHeight: '2.25rem' }],   // 30px (H1)
        '4xl': ['2.25rem', { lineHeight: '2.5rem' }],     // 36px
      },
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
