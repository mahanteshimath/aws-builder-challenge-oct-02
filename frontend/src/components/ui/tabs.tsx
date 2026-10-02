import * as TabsPrimitive from '@radix-ui/react-tabs'
import * as React from 'react'
import { cn } from '@/lib/utils'

export const Tabs = TabsPrimitive.Root
export const TabsList = React.forwardRef<HTMLDivElement, React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>>(({ className, ...p }, ref) => (
  <TabsPrimitive.List ref={ref} className={cn('flex items-center gap-1 overflow-x-auto', className)} {...p} />
))
TabsList.displayName = 'TabsList'
export const TabsTrigger = React.forwardRef<HTMLButtonElement, React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>>(({ className, ...p }, ref) => (
  <TabsPrimitive.Trigger ref={ref} className={cn('whitespace-nowrap rounded-md px-3 py-1.5 text-xs font-semibold text-muted transition-colors hover:text-text data-[state=active]:bg-cyan/15 data-[state=active]:text-cyan data-[state=active]:shadow-glow', className)} {...p} />
))
TabsTrigger.displayName = 'TabsTrigger'
export const TabsContent = React.forwardRef<HTMLDivElement, React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>>(({ className, ...p }, ref) => (
  <TabsPrimitive.Content ref={ref} className={cn('focus-visible:outline-none', className)} {...p} />
))
TabsContent.displayName = 'TabsContent'
