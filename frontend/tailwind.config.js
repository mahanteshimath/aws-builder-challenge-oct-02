/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: { sans: ['"Inter Variable"', 'Inter', 'system-ui', 'sans-serif'], mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'] },
      colors: {
        ink: '#050a14', panel: '#0b1324', panel2: '#101b32', line: '#1d2b48', line2: '#2a3d63',
        cyan: { DEFAULT: '#22d3ee', dim: '#0e7490' }, text: '#e6edf7', muted: '#8ca2c4',
        ok: '#34d399', warn: '#fbbf24', orange: '#fb923c', bad: '#f87171', deep: '#b91c1c',
      },
      boxShadow: { glow: '0 0 0 1px rgba(34,211,238,.35), 0 0 18px rgba(34,211,238,.15)' },
    },
  },
  plugins: [],
}
