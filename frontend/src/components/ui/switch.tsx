import * as SwitchPrimitive from '@radix-ui/react-switch'
import * as React from 'react'
import { cn } from '@/lib/utils'

export const Switch = React.forwardRef<HTMLButtonElement, React.ComponentPropsWithoutRef<typeof SwitchPrimitive.Root>>(({ className, ...p }, ref) => (
  <SwitchPrimitive.Root ref={ref} className={cn('peer inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full border border-line2 bg-panel2 transition-colors data-[state=checked]:border-cyan data-[state=checked]:bg-cyan/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan disabled:opacity-50', className)} {...p}>
    <SwitchPrimitive.Thumb className="pointer-events-none block h-3.5 w-3.5 translate-x-0.5 rounded-full bg-muted shadow transition-transform data-[state=checked]:translate-x-[18px] data-[state=checked]:bg-cyan" />
  </SwitchPrimitive.Root>
))
Switch.displayName = 'Switch'
