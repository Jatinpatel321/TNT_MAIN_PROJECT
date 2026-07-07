import React from 'react';

type Props = {
  children: React.ReactNode;
  fallback?: React.ReactNode;
};

type State = {
  hasError: boolean;
  error: unknown;
};

export class ErrorBoundary extends React.Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  static getDerivedStateFromError(error: unknown) {
    return { hasError: true, error };
  }

  componentDidCatch(error: unknown) {
    // eslint-disable-next-line no-console
    console.error('UI crashed:', error);
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <div className="min-h-screen bg-[#0F0F1A] flex items-center justify-center p-6">
            <div className="tnt-card max-w-xl w-full text-center">
              <div className="text-4xl mb-3">💥</div>
              <h2 className="text-xl font-bold text-[#F1F0FF] mb-2">Something went wrong</h2>
              <p className="text-sm text-[#9B9BC4] break-words">
                {this.state.error instanceof Error ? this.state.error.message : 'Unknown error'}
              </p>
              <div className="mt-4 text-left text-xs text-[#9B9BC4]">
                Open DevTools console to see the full stack trace.
              </div>
            </div>
          </div>
        )
      );
    }

    return this.props.children;
  }
}

