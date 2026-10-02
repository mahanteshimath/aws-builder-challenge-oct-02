import * as SliderPrimitive from '@radix-ui/react-slider'
import * as React from 'react'
import { cn } from '@/lib/utils'

export const Slider = React.forwardRef<HTMLSpanElement, React.ComponentPropsWithoutRef<typeof SliderPrimitive.Root>>(({ className, ...p }, ref) => (
  <SliderPrimitive.Root ref={ref} className={cn('relative flex h-5 w-full touch-none select-none items-center', className)} {...p}>
    <SliderPrimitive.Track className="relative h-1.5 w-full grow overflow-hidden rounded-full bg-line2">
      <SliderPrimitive.Range className="absolute h-full bg-cyan" />
    </SliderPrimitive.Track>
    <SliderPrimitive.Thumb className="block h-4 w-4 rounded-full border-2 border-cyan bg-ink shadow-glow transition-transform hover:scale-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan" />
  </SliderPrimitive.Root>
))
Slider.displayName = 'Slider'
