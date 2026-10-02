import * as TooltipPrimitive from '@radix-ui/react-tooltip'
import * as React from 'react'
import { cn } from '@/lib/utils'

export const TooltipProvider = TooltipPrimitive.Provider
export const Tooltip = TooltipPrimitive.Root
export const TooltipTrigger = TooltipPrimitive.Trigger
export const TooltipContent = React.forwardRef<HTMLDivElement, React.ComponentPropsWithoutRef<typeof TooltipPrimitive.Content>>(({ className, sideOffset = 6, ...p }, ref) => (
  <TooltipPrimitive.Portal>
    <TooltipPrimitive.Content ref={ref} sideOffset={sideOffset} className={cn('z-50 max-w-xs rounded-md border border-line2 bg-panel px-2.5 py-1.5 text-[11px] leading-snug text-text shadow-xl', className)} {...p} />
  </TooltipPrimitive.Portal>
))
TooltipContent.displayName = 'TooltipContent'
