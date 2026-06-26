import React from 'react';
import { cn } from '../../utils/cn';

type ButtonVariant = 'primary' | 'ghost' | 'success' | 'danger';
type ButtonSize = 'sm' | 'md' | 'lg';

type Props = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
};

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    'bg-[#4F46E5] text-white border border-[#4F46E5] hover:bg-[#4338CA] hover:border-[#4338CA]',
  ghost:
    'bg-transparent text-[#6B7280] border border-[#E5E7EB] hover:text-[#111827] hover:border-[#D1D5DB] hover:bg-[#F3F5F9]',
  success:
    'bg-green-50 text-green-600 border border-green-200 hover:bg-green-100',
  danger:
    'bg-red-50 text-red-600 border border-red-200 hover:bg-red-100',
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-xs rounded-lg',
  md: 'h-10 px-4 text-sm rounded-xl',
  lg: 'h-12 px-5 text-base rounded-2xl',
};

export function Button({
  variant = 'primary',
  size = 'md',
  className,
  type,
  disabled,
  ...rest
}: Props) {
  return (
    <button
      type={type ?? 'button'}
      disabled={disabled}
      className={cn(
        'inline-flex items-center justify-center gap-2 font-medium transition-all duration-150 select-none',
        'focus:outline-none focus:ring-2 focus:ring-[#4F46E5]/60 focus:ring-offset-0',
        disabled && 'opacity-60 cursor-not-allowed',
        variantClasses[variant],
        sizeClasses[size],
        className
      )}
      {...rest}
    />
  );
}