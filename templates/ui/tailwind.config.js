/** tailwind.config.js — AIDD Design System を Tailwind に当てる（React + Vite 向け）
 * 真実源: skills/design-system/SKILL.md ／ 実物: templates/tokens.css
 * 値はここに書かない。tokens.css の CSS 変数を参照する形で登録し、Tailwind 既定パレット（blue-500 等）は使わない。
 * 使い方: src/styles/tokens.css を main.tsx で最初に import し、このファイルをプロジェクト直下に置く。
 *   <button class="bg-primary text-on-primary rounded-md px-4 min-h-tap">保存する</button>
 * 注意: 色が var() なので `bg-primary/50` のような透明度修飾子は効かない（必要なら *-bg 系の淡色トークンを使う）。
 */
module.exports = {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx,vue,svelte}'],
  theme: {
    extend: {
      colors: {
        primary: { DEFAULT: 'var(--color-primary)', light: 'var(--color-primary-light)', dark: 'var(--color-primary-dark)' },
        'on-primary': 'var(--color-on-primary)',
        bg: 'var(--color-bg)',
        surface: { DEFAULT: 'var(--color-surface)', 2: 'var(--color-surface-2)', 3: 'var(--color-surface-3)' },
        border: { DEFAULT: 'var(--color-border)', strong: 'var(--color-border-strong)' },
        divider: 'var(--color-divider)',
        text: { DEFAULT: 'var(--color-text)', secondary: 'var(--color-text-secondary)', disabled: 'var(--color-text-disabled)' },
        /* severity（ISTQB）。色名でなく重大度で呼ぶ */
        critical: { DEFAULT: 'var(--color-critical)', bg: 'var(--color-critical-bg)', border: 'var(--color-critical-border)' },
        high:     { DEFAULT: 'var(--color-high)',     bg: 'var(--color-high-bg)',     border: 'var(--color-high-border)' },
        medium:   { DEFAULT: 'var(--color-medium)',   bg: 'var(--color-medium-bg)',   border: 'var(--color-medium-border)', text: 'var(--color-medium-text)' },
        low:      { DEFAULT: 'var(--color-low)',      bg: 'var(--color-low-bg)',      border: 'var(--color-low-border)' },
        info:     { DEFAULT: 'var(--color-info)',     bg: 'var(--color-info-bg)',     border: 'var(--color-info-border)' },
        scrim: 'var(--color-scrim)',
        tooltip: { bg: 'var(--color-tooltip-bg)', text: 'var(--color-tooltip-text)' },
      },
      spacing: {
        1: 'var(--space-1)', 2: 'var(--space-2)', 3: 'var(--space-3)', 4: 'var(--space-4)',
        5: 'var(--space-5)', 6: 'var(--space-6)', 8: 'var(--space-8)', 12: 'var(--space-12)',
      },
      borderRadius: { sm: 'var(--radius-sm)', md: 'var(--radius-md)', lg: 'var(--radius-lg)', xl: 'var(--radius-xl)', full: 'var(--radius-full)' },
      fontFamily: { sans: ['var(--font-main)'], mono: ['var(--font-mono)'] },
      fontSize: {
        xs: 'var(--text-xs)', sm: 'var(--text-sm)', base: 'var(--text-base)', md: 'var(--text-md)',
        lg: 'var(--text-lg)', xl: 'var(--text-xl)', '2xl': 'var(--text-2xl)',
      },
      lineHeight: { tight: 'var(--leading-tight)', normal: 'var(--leading-normal)', loose: 'var(--leading-loose)' },
      boxShadow: { sm: 'var(--shadow-sm)', md: 'var(--shadow-md)', lg: 'var(--shadow-lg)', pop: 'var(--shadow-pop)' },
      transitionDuration: { fast: 'var(--motion-fast)', normal: 'var(--motion-normal)', slow: 'var(--motion-slow)' },
      maxWidth: { measure: 'var(--text-measure)' },
      minHeight: { tap: 'var(--tap-min)' },
      minWidth: { tap: 'var(--tap-min)' },
    },
  },
  plugins: [],
};
