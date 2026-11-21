/** @type {import('tailwindcss').Config} */
// Design tokens mirror the Figma collection "RedCaps v2 · Green".
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas: '#E9E8E3',
        surface: '#FFFFFF',
        subtle: '#F5F4F0',
        ink: '#1F2A24',
        line: '#E6E4DE',
        text: { DEFAULT: '#1C2420', muted: '#6B716C' },
        green: {
          900: '#23382B',
          700: '#3F5E4A',
          500: '#6F8F78',
          200: '#CADBCD',
          100: '#E7EFE8',
        },
        brandred: '#D7262E',
        status: {
          red: '#C8463C',
          'red-soft': '#FBE7E4',
          amber: '#C98118',
          'amber-soft': '#FBF0DD',
          blue: '#3E63C2',
          'blue-soft': '#E6ECFA',
          green: '#2F8A57',
          'green-soft': '#E1F2E7',
        },
        heat: { 1: '#D9574B', 2: '#EFA99F', 3: '#F3E9CF', 4: '#B8D3BE', 5: '#4E8A62' },
      },
      fontFamily: {
        // Font is not final yet: change these three lines to switch the whole app.
        display: ['"Red Hat Display"', 'system-ui', 'sans-serif'],
        sans: ['"Red Hat Text"', 'system-ui', 'sans-serif'],
        mono: ['"Red Hat Mono"', 'ui-monospace', 'monospace'],
      },
      borderRadius: {
        card: '28px',
        tile: '24px',
        panel: '32px',
      },
      boxShadow: {
        card: '0 24px 48px -24px rgba(31, 42, 36, 0.28), 0 2px 6px rgba(31, 42, 36, 0.06)',
        soft: '0 10px 28px -14px rgba(31, 42, 36, 0.22)',
      },
    },
  },
  plugins: [],
};
