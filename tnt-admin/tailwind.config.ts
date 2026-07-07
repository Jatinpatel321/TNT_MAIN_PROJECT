import type { Config } from 'tailwindcss';
import formsPlugin from '@tailwindcss/forms';

const config: Config = {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // TNT Brand
        'tnt-orange': '#E85D24',
        'tnt-orange-light': '#F97316',

        // Light theme backgrounds
        'bg-base': '#F7F8FC',
        'bg-surface': '#FFFFFF',
        'bg-elevated': '#F3F5F9',

        // Borders
        'border-dim': '#E5E7EB',

        // Text
        'text-primary': '#111827',
        'text-secondary': '#4B5563',
        'text-tertiary': '#9CA3AF',

        // Brand
        'brand-primary': '#4F46E5',

        // Status
        success: '#22C55E',
        warning: '#F59E0B',
        danger: '#EF4444',
        info: '#2563EB',

        // Chart palette
        'chart-1': '#4F46E5',
        'chart-2': '#2563EB',
        'chart-3': '#22C55E',
        'chart-4': '#F59E0B',
        'chart-5': '#EF4444',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      borderRadius: {
        'xl': '0.75rem',
        '2xl': '1rem',
        '3xl': '1.5rem',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 3s linear infinite',
        'fade-in': 'fadeIn 0.15s ease-out',
        'slide-in-right': 'slideInRight 0.2s ease-out',
        'slide-in-up': 'slideInUp 0.2s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(-4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideInRight: {
          '0%': { opacity: '0', transform: 'translateX(16px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        slideInUp: {
          '0%': { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      boxShadow: {
        'glow-orange': '0 0 20px rgba(232, 93, 36, 0.3)',
        'glow-success': '0 0 20px rgba(34, 197, 94, 0.3)',
        'glow-danger': '0 0 20px rgba(239, 68, 68, 0.3)',
        'card': '0 1px 2px rgba(0,0,0,0.03), 0 8px 24px rgba(0,0,0,0.04)',
        'card-hover': '0 2px 4px rgba(0,0,0,0.04), 0 12px 32px rgba(0,0,0,0.06)',
      },
      transitionDuration: {
        '150': '150ms',
      },
    },
  },
  plugins: [formsPlugin],
};

export default config;