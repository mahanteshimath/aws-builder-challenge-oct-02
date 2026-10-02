import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded-md text-xs font-semibold transition-colors disabled:pointer-events-none disabled:opacity-45 focus-visible:outline-none',
  {
    variants: {
      variant: {
        primary: 'bg-cyan text-ink hover:bg-cyan/85 shadow-glow',
        secondary: 'bg-panel2 text-text border border-line2 hover:border-cyan/60 hover:text-cyan',
        ghost: 'text-muted hover:bg-panel2 hover:text-text',
        danger: 'bg-bad/15 text-bad border border-bad/40 hover:bg-bad/25',
        success: 'bg-ok/15 text-ok border border-ok/40 hover:bg-ok/25',
      },
      size: { sm: 'h-7 px-2.5', md: 'h-8 px-3', lg: 'h-9 px-4 text-sm', icon: 'h-8 w-8' },
    },
    defaultVariants: { variant: 'secondary', size: 'md' },
  },
)
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> { asChild?: boolean }
export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(({ className, variant, size, asChild, ...p }, ref) => {
  const C = asChild ? Slot : 'button'
  return <C ref={ref} className={cn(buttonVariants({ variant, size }), className)} {...p} />
})
Button.displayName = 'Button'
