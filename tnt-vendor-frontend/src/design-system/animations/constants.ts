// ─── TNT Animation System ────────────────────────────────────────────

export const ANIMATION_DURATION = {
  instant: 100,
  fast: 200,
  normal: 300,
  slow: 400,
  slower: 600,
  slowest: 800,
} as const;

export const ANIMATION_EASING = {
  // Standard
  easeInOut: {
    duration: 300,
    easing: (t: number) =>
      t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t,
  },
  // Spring-like
  spring: {
    damping: 12,
    stiffness: 200,
    mass: 0.5,
  },
  springLight: {
    damping: 15,
    stiffness: 150,
    mass: 0.3,
  },
  // Bouncy
  bouncy: {
    damping: 8,
    stiffness: 300,
    mass: 0.5,
  },
} as const;

export const ANIMATION_DELAY = {
  none: 0,
  short: 50,
  medium: 150,
  long: 300,
  staggered: 80, // between items
} as const;

// Preset animation configs for common use cases
export const SPRING_CONFIG = {
  // Card entrance
  cardEntrance: {
    friction: 8,
    tension: 60,
    useNativeDriver: true,
  },
  // Counter animation
  counter: {
    duration: 600,
    useNativeDriver: false,
  },
  // Status pulse
  pulse: {
    duration: 1500,
    useNativeDriver: true,
  },
  // Slide in from bottom
  slideUp: {
    duration: 400,
    useNativeDriver: true,
  },
  // Fade in
  fadeIn: {
    duration: 300,
    useNativeDriver: true,
  },
  // Scale in (for badges, icons)
  scaleIn: {
    friction: 6,
    tension: 100,
    useNativeDriver: true,
  },
} as const;

// Stagger delay helper
export const staggerDelay = (index: number, baseDelay: number = 80): number =>
  index * baseDelay;



