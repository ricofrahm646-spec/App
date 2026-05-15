import { cn } from '@/lib/utils';
import React from 'react';

const variantStyles = {
  default: 'border-slate-700/50 bg-slate-800/50',
  success: 'border-emerald-500/30 bg-emerald-950/20',
  danger: 'border-red-500/30 bg-red-950/20',
  warning: 'border-amber-500/30 bg-amber-950/20',
};

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: keyof typeof variantStyles;
}

export function Card({ className, variant = 'default', ...props }: CardProps) {
  return (
    <div
      className={cn(
        'rounded-xl border backdrop-blur-sm transition-all duration-200',
        variantStyles[variant],
        className
      )}
      {...props}
    />
  );
}

export function CardHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('flex flex-col space-y-1.5 p-5', className)} {...props} />;
}

export function CardTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cn('text-sm font-medium text-slate-400', className)} {...props} />;
}

export function CardContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('p-5 pt-0', className)} {...props} />;
}

export function CardFooter({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('flex items-center p-5 pt-0', className)} {...props} />;
}
