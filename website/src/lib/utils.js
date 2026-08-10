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

export function agentProvider(agent) {
  const provider = agent?.provider?.organization?.trim()
  if (provider) return provider

  const author = agent?.author?.trim()
  if (author && author.toLowerCase() !== "unknown") return author

  return "Unknown"
}

export function formatVersion(value) {
  const version = String(value ?? "").trim()
  if (!version) return null
  return /^v/i.test(version) ? version : `v${version}`
}
