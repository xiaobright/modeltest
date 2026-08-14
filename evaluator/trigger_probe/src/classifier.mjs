function count(text, regex) {
  return [...text.matchAll(regex)].length
}

export function classifyReasoning(reasoning, visibleBeforeTool = false) {
  const text = reasoning.trim()
  const firstLine = text.split(/\r?\n/, 1)[0] ?? ''
  const metrics = {
    firstLine,
    chars: text.length,
    we: count(text, /\bwe\b/gi),
    letMe: count(text, /\blet me\b/gi),
    i: count(text, /\bi\b/gi),
    markerFirstLine: /^(good|great|excellent)\.?$/i.test(firstLine.trim()),
    visibleBeforeTool,
  }

  let score = 0
  if (/^we need\b/i.test(firstLine)) score += 3
  if (/^let me\b/i.test(firstLine)) score -= 3
  if (metrics.we > 0 && metrics.letMe === 0) score += 2
  if (metrics.letMe > 0) score -= 2
  if (metrics.markerFirstLine) score += 1
  if (visibleBeforeTool) score -= 1

  return {
    label: score >= 4 ? 'minimal-like' : score <= -4 ? 'standard-like' : 'ambiguous',
    score,
    metrics,
  }
}
