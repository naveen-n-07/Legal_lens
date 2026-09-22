/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Fira Code"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
        display: ['"Plus Jakarta Sans"', 'Inter', 'sans-serif'],
      },
      fontSize: {
        '2xs': ['0.75rem', { lineHeight: '1rem', letterSpacing: '0.01em' }],     // 12px (Micro-metadata / Footers)
        'xs': ['0.8125rem', { lineHeight: '1.125rem', letterSpacing: '0.01em' }], // 13px (Secondary / Badges)
        'sm': ['0.875rem', { lineHeight: '1.25rem' }],                            // 14px (Standard Body / Table text)
        'base': ['1rem', { lineHeight: '1.5rem' }],                               // 16px (Comfortable body / Input labels)
        'md': ['1.0625rem', { lineHeight: '1.5rem' }],                            // 17px (Subheaders)
        'lg': ['1.125rem', { lineHeight: '1.75rem' }],                            // 18px (Card Titles)
        'xl': ['1.25rem', { lineHeight: '1.75rem', letterSpacing: '-0.01em' }],   // 20px (Section Headings)
        '2xl': ['1.5rem', { lineHeight: '2rem', letterSpacing: '-0.02em' }],      // 24px (Page Sub-titles)
        '3xl': ['1.875rem', { lineHeight: '2.25rem', letterSpacing: '-0.025em' }],// 30px (Main Page Headings)
        '4xl': ['2.25rem', { lineHeight: '2.5rem', letterSpacing: '-0.03em' }],   // 36px (Hero / National Portal Headers)
      },
      colors: {
        // "Bharat Executive" Color System
        brand: {
          deep: '#5E1212',     // Imperial Maroon Header / Base Accent
          primary: '#7A1C1C',  // Primary Statutory Crimson
          hover: '#631515',    // Interactive Hover State
          tint: '#FDF2F2',     // Soft Highlight Background
          light: '#9E2A2B',    // Accent Bright Maroon
        },
        gov: {
          navy: '#0F2744',     // Sovereign Navy (Command Text & Dark Panels)
          slate: '#1E3A5F',    // Secondary Authority Slate
          saffron: '#FF9933',  // National Saffron Accent
          green: '#138808',    // National India Green Accent
          lightbg: '#F8FAFC',  // Anti-Glare Canvas Base
          border: '#E2E8F0',   // Crisp Divider Line
        },
        status: {
          compliant: '#059669', // Section 7A (Emerald Conforming)
          violation: '#DC2626', // Section 7B (Crimson Violation)
          pending: '#D97706',   // Adjudication Pending (Warm Saffron / Ochre)
        }
      },
      boxShadow: {
        'card': '0 1px 3px 0 rgba(15, 23, 42, 0.06), 0 1px 2px -1px rgba(15, 23, 42, 0.04)',
        'card-hover': '0 10px 15px -3px rgba(15, 23, 42, 0.08), 0 4px 6px -4px rgba(15, 23, 42, 0.04)',
        'elevated': '0 20px 25px -5px rgba(15, 23, 42, 0.1), 0 8px 10px -6px rgba(15, 23, 42, 0.06)',
      }
    },
  },
  plugins: [],
}
