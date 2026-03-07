'use client'

import { cn } from '@/lib/utils'

export function TypingIndicator() {
  return (
    <div className="flex items-center gap-2 px-4 py-3 max-w-[70%]">
      <div className="flex items-center gap-1 bg-gray-100 rounded-2xl px-4 py-3">
        <div
          className={cn(
            'w-2 h-2 bg-gray-500 rounded-full',
            'animate-bounce',
            '[animation-delay:0ms]'
          )}
        />
        <div
          className={cn(
            'w-2 h-2 bg-gray-500 rounded-full',
            'animate-bounce',
            '[animation-delay:150ms]'
          )}
        />
        <div
          className={cn(
            'w-2 h-2 bg-gray-500 rounded-full',
            'animate-bounce',
            '[animation-delay:300ms]'
          )}
        />
      </div>
    </div>
  )
}
