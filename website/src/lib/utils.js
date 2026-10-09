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

const escapeHtml = (text) => text.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

// Maintainer notes are part system-written, part human; render only `code` and
// **bold** after escaping, never links or HTML.
export function renderNote(text) {
  return escapeHtml(String(text ?? ''))
    .replace(/`([^`\n]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>');
}
