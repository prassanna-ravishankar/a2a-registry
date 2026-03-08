import { clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs) {
  return twMerge(clsx(inputs))
}

export function safeExternalUrl(value) {
  if (!value) return null

  try {
    const url = new URL(value)
    if (url.protocol === "http:" || url.protocol === "https:") {
      return url.toString()
    }
  } catch {
    return null
  }

  return null
}
