import React from 'react';
import { LucideIcon } from 'lucide-react';

interface CardProps {
  title?: string;
  icon?: LucideIcon;
  children: React.ReactNode;
  className?: string;
  iconClassName?: string;
  titleClassName?: string;
}

export function Card({ 
  title, 
  icon: Icon, 
  children, 
  className = '',
  iconClassName = 'text-teal-400',
  titleClassName = 'text-sm font-semibold tracking-wide text-white'
}: CardProps) {
  return (
    <div className={`bg-neutral-900 border border-white/[0.06] rounded-xl p-6 ${className}`}>
      {(title || Icon) && (
        <div className="flex items-center gap-3 mb-4">
          {Icon && <Icon size={18} className={iconClassName} />}
          {title && <h3 className={titleClassName}>{title}</h3>}
        </div>
      )}
      {children}
    </div>
  );
}
