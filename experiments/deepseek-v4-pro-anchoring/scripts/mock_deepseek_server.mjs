import { createServer } from 'node:http';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const port = Number(process.env.MOCK_PORT ?? '32190');
const output = path.resolve(process.env.MOCK_OUTPUT ?? 'mock-requests.json');
const requests = [];

function sse(response, chunks) {
  response.writeHead(200, {
    'content-type': 'text/event-stream',
    'cache-control': 'no-cache',
    connection: 'keep-alive',
  });
  for (const chunk of chunks) response.write(`data: ${JSON.stringify(chunk)}\n\n`);
  response.end('data: [DONE]\n\n');
}

const server = createServer(async (request, response) => {
  if (request.method !== 'POST' || !request.url?.endsWith('/chat/completions')) {
    response.writeHead(404).end();
    return;
  }
  const body = [];
  for await (const chunk of request) body.push(chunk);
  const parsed = JSON.parse(Buffer.concat(body).toString('utf8'));
  requests.push(parsed);
  await mkdir(path.dirname(output), { recursive: true });
  await writeFile(output, `${JSON.stringify(requests, null, 2)}\n`, 'utf8');
  const id = `mock-${requests.length}`;
  const base = { id, object: 'chat.completion.chunk', created: 0, model: parsed.model };
  if (!Array.isArray(parsed.tools) || parsed.tools.length === 0) {
    sse(response, [
      { ...base, choices: [{ index: 0, delta: { role: 'assistant', content: 'Mock schema gate' }, finish_reason: null }] },
      { ...base, choices: [{ index: 0, delta: {}, finish_reason: 'stop' }], usage: { prompt_tokens: 5, completion_tokens: 3, prompt_cache_hit_tokens: 0, prompt_cache_miss_tokens: 5, completion_tokens_details: { reasoning_tokens: 0 } } },
    ]);
    return;
  }
  const hasToolResult = parsed.messages.some((message) => message.role === 'tool');
  if (!hasToolResult) {
    const shell = parsed.tools.find((tool) => ['pwsh', 'bash'].includes(tool.function?.name))?.function?.name;
    if (!shell) throw new Error('mock agent request 缺少 shell tool');
    const command = shell === 'pwsh' ? 'Get-Location' : 'pwd';
    sse(response, [
      { ...base, choices: [{ index: 0, delta: { role: 'assistant', reasoning_content: 'Inspect the workspace first.' }, finish_reason: null }] },
      { ...base, choices: [{ index: 0, delta: { tool_calls: [{ index: 0, id: 'mock_call_1', type: 'function', function: { name: shell, arguments: JSON.stringify({ command, description: 'Inspect current working directory' }) } }] }, finish_reason: null }] },
      { ...base, choices: [{ index: 0, delta: {}, finish_reason: 'tool_calls' }], usage: { prompt_tokens: 10, completion_tokens: 10, prompt_cache_hit_tokens: 0, prompt_cache_miss_tokens: 10, completion_tokens_details: { reasoning_tokens: 4 } } },
    ]);
  } else {
    sse(response, [
      { ...base, choices: [{ index: 0, delta: { role: 'assistant', reasoning_content: 'The schema transition is complete.' }, finish_reason: null }] },
      { ...base, choices: [{ index: 0, delta: { content: 'Mock validation complete.' }, finish_reason: null }] },
      { ...base, choices: [{ index: 0, delta: {}, finish_reason: 'stop' }], usage: { prompt_tokens: 20, completion_tokens: 8, prompt_cache_hit_tokens: 5, prompt_cache_miss_tokens: 15, completion_tokens_details: { reasoning_tokens: 3 } } },
    ]);
  }
});

server.listen(port, '127.0.0.1', () => process.stdout.write(`mock-listening:${port}\n`));
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => server.close(() => process.exit(0)));
