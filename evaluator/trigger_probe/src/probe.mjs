import { classifyReasoning } from './classifier.mjs'

function endpoint(baseUrl) {
  return `${baseUrl.replace(/\/$/, '')}/chat/completions`
}

export async function sendTurn({ apiKey, baseUrl, maxTokens, messages, model, timeoutMs, tools }) {
  const response = await fetch(endpoint(baseUrl), {
    method: 'POST',
    headers: {
      authorization: `Bearer ${apiKey}`,
      'content-type': 'application/json',
    },
    body: JSON.stringify({
      model,
      messages,
      thinking: { type: 'enabled' },
      reasoning_effort: 'max',
      tools,
      max_tokens: maxTokens,
    }),
    signal: AbortSignal.timeout(timeoutMs),
  })

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${(await response.text()).slice(0, 1000)}`)
  }

  const payload = await response.json()
  const message = payload.choices?.[0]?.message ?? {}
  const reasoning = message.reasoning_content ?? message.reasoning ?? ''
  const toolCalls = message.tool_calls ?? []
  return {
    message,
    classification: classifyReasoning(reasoning, Boolean(message.content)),
    finishReason: payload.choices?.[0]?.finish_reason ?? null,
    usage: payload.usage ?? null,
    toolNames: toolCalls.map(call => call.function?.name).filter(Boolean),
  }
}

export function appendSyntheticToolResults(messages, assistantMessage) {
  const calls = assistantMessage.tool_calls ?? []
  return [
    ...messages,
    assistantMessage,
    ...calls.map(call => ({
      role: 'tool',
      tool_call_id: call.id,
      content: 'Probe fixture: repository structure inspected; README.md is available.',
    })),
  ]
}
