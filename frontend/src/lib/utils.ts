import { format, formatDistanceToNow } from 'date-fns'
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function relativeTime(value: string) {
  return formatDistanceToNow(new Date(value), { addSuffix: true })
}

export function fullDate(value: string) {
  return format(new Date(value), 'MMM d, yyyy h:mm a')
}

export const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ?? 'http://localhost:8000/api'
