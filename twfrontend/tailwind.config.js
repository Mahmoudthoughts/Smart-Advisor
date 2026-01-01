/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{html,ts}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Sora"', 'system-ui', 'sans-serif'],
        body: ['"Space Grotesk"', 'system-ui', 'sans-serif']
      },
      colors: {
        ink: {
          900: '#0b0f1a',
          800: '#101827',
          700: '#182135',
          600: '#222c43',
          500: '#2b3650',
          300: '#6b7a99',
          200: '#a6b1c6'
        },
        neon: {
          500: '#4de8c2',
          400: '#72f2da',
          300: '#9bf7e7'
        },
        ember: {
          500: '#ff8b5e',
          400: '#ffad8a'
        }
      },
      boxShadow: {
        glow: '0 20px 60px -30px rgba(77, 232, 194, 0.6)'
      }
    }
  },
  plugins: []
};
