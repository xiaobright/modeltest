import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { appendSyntheticToolResults, sendTurn } from './probe.mjs'
import {
  buildMinimalTools,
  MINIMAL_SYSTEM,
  PARAPHRASED_SYSTEM,
  USER_PROMPT,
} from './scaffolds.mjs'

function option(name, fallback) {
  const index = process.argv.indexOf(name)
  return index < 0 ? fallback : process.argv[index + 1]
}

async function loadTools(path, fallback) {
  if (!path) return fallback
  const parsed = JSON.parse(await readFile(resolve(path), 'utf8'))
  if (!Array.isArray(parsed)) throw new Error(`${path} must contain a JSON tool array`)
  return parsed
}

function summary(result) {
  return {
    classification: result.classification,
    finishReason: result.finishReason,
    toolNames: result.toolNames,
    usage: result.usage,
  }
}

const run = process.argv.includes('--run')
const promotePath = option('--promote-tools', '')
const initialTools = await loadTools(option('--tools', ''), buildMinimalTools())
const promotedTools = await loadTools(promotePath, initialTools)
const system = option('--system', 'minimal') === 'paraphrased'
  ? PARAPHRASED_SYSTEM
  : MINIMAL_SYSTEM
const model = option('--model', process.env.DEEPSEEK_MODEL || 'deepseek-v4-flash')
const baseUrl = process.env.DEEPSEEK_BASE_URL || 'https://api.deepseek.com'
const maxTokens = Number(process.env.PROBE_MAX_TOKENS || '1024')
const timeoutMs = Number(process.env.PROBE_TIMEOUT_MS || '180000')
const initialMessages = [
  { role: 'system', content: system },
  { role: 'user', content: USER_PROMPT },
]

if (!run) {
  console.log(JSON.stringify({
    dryRun: true,
    endpoint: `${baseUrl.replace(/\/$/, '')}/chat/completions`,
    model,
    system,
    initialToolNames: initialTools.map(tool => tool.function?.name),
    promotedToolNames: promotedTools.map(tool => tool.function?.name),
    note: 'No request sent. Add --run to opt in to paid API calls.',
  }, null, 2))
  process.exit(0)
}

const apiKey = process.env.DEEPSEEK_API_KEY
if (!apiKey) throw new Error('DEEPSEEK_API_KEY is empty')

const first = await sendTurn({
  apiKey, baseUrl, maxTokens, messages: initialMessages, model, timeoutMs, tools: initialTools,
})
const output = { schemaVersion: 1, model, first: summary(first) }

if (promotePath && first.message.tool_calls?.length) {
  const continuedMessages = appendSyntheticToolResults(initialMessages, first.message)
  const second = await sendTurn({
    apiKey,
    baseUrl,
    maxTokens,
    messages: continuedMessages,
    model,
    timeoutMs,
    tools: promotedTools,
  })
  output.promoted = summary(second)
  output.raw = { first: first.message, promoted: second.message }
} else {
  output.raw = { first: first.message }
}

const outputDir = resolve('results')
await mkdir(outputDir, { recursive: true })
const outputPath = resolve(outputDir, `${new Date().toISOString().replaceAll(':', '-')}.json`)
await writeFile(outputPath, `${JSON.stringify(output, null, 2)}\n`, 'utf8')
console.log(JSON.stringify({ saved: outputPath, ...summary(first), promoted: output.promoted }, null, 2))
