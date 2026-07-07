// ─── TNT Premium Design System — Typography ──────────────────────────

const typography = {
  // Font Families (configurable for each platform)
  fontFamily: {
    regular: undefined, // Platform default (SF Pro / Roboto)
    medium: undefined,
    semibold: undefined,
    bold: undefined,
  },

  // Font Sizes
  fontSize: {
    display1: 40,
    display2: 34,
    h1: 28,
    h2: 24,
    h3: 20,
    h4: 18,
    body: 16,
    bodySmall: 14,
    caption: 12,
    tiny: 10,
    micro: 8,
  },

  // Font Weights
  fontWeight: {
    regular: '400' as const,
    medium: '500' as const,
    semibold: '600' as const,
    bold: '700' as const,
    heavy: '800' as const,
  },

  // Line Heights
  lineHeight: {
    tight: 1.15,
    normal: 1.4,
    relaxed: 1.6,
    loose: 1.8,
  },

  // Letter Spacing
  letterSpacing: {
    tight: -0.5,
    normal: 0,
    wide: 0.5,
    wider: 1,
    uppercase: 1.5,
  },

  // Text Presets — common patterns
  preset: {
    display: {
      fontSize: 40,
      fontWeight: '700' as const,
      letterSpacing: -0.5,
      lineHeight: 46,
    },
    h1: {
      fontSize: 28,
      fontWeight: '700' as const,
      letterSpacing: -0.3,
      lineHeight: 34,
    },
    h2: {
      fontSize: 24,
      fontWeight: '700' as const,
      letterSpacing: -0.2,
      lineHeight: 30,
    },
    h3: {
      fontSize: 20,
      fontWeight: '600' as const,
      letterSpacing: 0,
      lineHeight: 26,
    },
    h4: {
      fontSize: 18,
      fontWeight: '600' as const,
      letterSpacing: 0,
      lineHeight: 24,
    },
    body: {
      fontSize: 16,
      fontWeight: '400' as const,
      letterSpacing: 0,
      lineHeight: 22,
    },
    bodySmall: {
      fontSize: 14,
      fontWeight: '400' as const,
      letterSpacing: 0,
      lineHeight: 20,
    },
    caption: {
      fontSize: 12,
      fontWeight: '500' as const,
      letterSpacing: 0,
      lineHeight: 16,
    },
    tiny: {
      fontSize: 10,
      fontWeight: '500' as const,
      letterSpacing: 0.3,
      lineHeight: 14,
    },
    button: {
      fontSize: 16,
      fontWeight: '600' as const,
      letterSpacing: 0.3,
      lineHeight: 20,
    },
    buttonSmall: {
      fontSize: 14,
      fontWeight: '600' as const,
      letterSpacing: 0.3,
      lineHeight: 18,
    },
    uppercase: {
      fontSize: 12,
      fontWeight: '600' as const,
      letterSpacing: 1.5,
      lineHeight: 16,
      textTransform: 'uppercase' as const,
    },
    metric: {
      fontSize: 32,
      fontWeight: '700' as const,
      letterSpacing: -0.5,
      lineHeight: 36,
    },
    metricSmall: {
      fontSize: 24,
      fontWeight: '700' as const,
      letterSpacing: -0.3,
      lineHeight: 28,
    },
  },
} as const;

export type TypographyPreset = keyof typeof typography.preset;
export default typography;
