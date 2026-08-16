import { randomUUID } from 'node:crypto';
import { spawn } from 'node:child_process';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import net from 'node:net';
import os from 'node:os';
import path from 'node:path';

function parseArgs(argv) {
  const result = {};
  for (let i = 0; i < argv.length; i += 2) {
    const key = argv[i];
    if (!key?.startsWith('--') || argv[i + 1] === undefined) {
      throw new Error(`参数格式错误：${key ?? '<missing>'}`);
    }
    result[key.slice(2)] = argv[i + 1];
  }
  return result;
}

function required(args, key) {
  const value = args[key];
  if (!value) throw new Error(`缺少 --${key}`);
  return value;
}

async function freePort() {
  const server = net.createServer();
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  const address = server.address();
  const port = typeof address === 'object' && address ? address.port : undefined;
  await new Promise((resolve) => server.close(resolve));
  if (!port) throw new Error('未取得本地空闲端口');
  return port;
}

async function rpc(baseUrl, method, payload, timeoutMs = 30_000) {
  const rpcId = randomUUID();
  const response = await fetch(`${baseUrl}/api/${method}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ type: 'client-request', rpcId, method, payload }),
    signal: AbortSignal.timeout(timeoutMs),
  });
  if (!response.ok) throw new Error(`${method} HTTP ${response.status}`);
  const envelope = await response.json();
  if (envelope.rpcId !== rpcId) throw new Error(`${method} rpcId 不匹配`);
  if (!envelope.result?.ok) {
    throw new Error(`${method} 失败：${JSON.stringify(envelope.result?.error ?? envelope.result)}`);
  }
  return envelope.result.value;
}

async function waitReady(baseUrl, child, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  let lastError;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) throw new Error(`DSH Web 提前退出：${child.exitCode}`);
    try {
      await rpc(baseUrl, 'host.describe', {}, 2_000);
      return;
    } catch (error) {
      lastError = error;
      await new Promise((resolve) => setTimeout(resolve, 250));
    }
  }
  throw new Error(`DSH Web 启动超时：${lastError?.message ?? 'unknown'}`);
}

async function waitIdle(baseUrl, sessionId, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  let observedRunning = false;
  let observedNonBlank = false;
  while (Date.now() < deadline) {
    const { items } = await rpc(baseUrl, 'session.list', {}, 15_000);
    const current = items.find((item) => item.sessionId === sessionId);
    if (!current) throw new Error(`session.list 缺少 ${sessionId}`);
    observedRunning ||= current.running;
    observedNonBlank ||= !current.blank;
    if (observedNonBlank && !current.running) return current;
    await new Promise((resolve) => setTimeout(resolve, 1_000));
  }
  throw new Error(`DSH session ${sessionId} 超过 ${timeoutMs / 1000} 秒仍未 idle`);
}

async function readAllHistory(baseUrl, sessionId) {
  const bySeq = new Map();
  let beforeSeq;
  for (let page = 0; page < 1_000; page += 1) {
    const payload = { sessionId, maxMessages: 1_000 };
    if (beforeSeq !== undefined) payload.beforeSeq = beforeSeq;
    const value = await rpc(baseUrl, 'session.history', payload, 30_000);
    for (const entry of value.events) bySeq.set(entry.event.seq, entry.event);
    if (!value.hasMore || value.events.length === 0) break;
    beforeSeq = Math.min(...value.events.map((entry) => entry.event.seq));
  }
  return [...bySeq.values()].sort((a, b) => a.seq - b.seq);
}

async function terminate(child) {
  if (child.exitCode !== null) return;
  child.kill('SIGTERM');
  await Promise.race([
    new Promise((resolve) => child.once('exit', resolve)),
    new Promise((resolve) => setTimeout(resolve, 5_000)),
  ]);
  if (child.exitCode === null) child.kill('SIGKILL');
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const cwd = path.resolve(required(args, 'cwd'));
  const preset = required(args, 'preset');
  const promptFile = path.resolve(required(args, 'prompt-file'));
  const privateOutput = path.resolve(required(args, 'private-output'));
  const timeoutSeconds = Number(args['timeout-seconds'] ?? '4500');
  const provider = args.provider ?? 'deepseek-official';
  const model = args.model ?? 'deepseek-v4-pro';
  const reasoningEffort = args['reasoning-effort'] ?? 'max';
  const dshHome = process.env.DSH_HOME ?? path.join(os.homedir(), '.dsh');
  const dshBin = process.env.DSH_BIN ?? path.join(dshHome, 'profiles', 'node_modules', '@deepseek-ai', 'dsh', 'lib', 'bin.js');
  const port = await freePort();
  const baseUrl = `http://127.0.0.1:${port}`;
  await mkdir(privateOutput, { recursive: true });

  const stdout = [];
  const stderr = [];
  const childArgs = [dshBin, '--profile', 'web'];
  if (args.patch) childArgs.push('--patch', path.resolve(args.patch));
  childArgs.push('--host', '127.0.0.1', '--port', String(port));
  const child = spawn(process.execPath, childArgs, {
    cwd,
    env: { ...process.env, DSH_HOME: dshHome, DSH_TELEMETRY_DISABLED: '1' },
    windowsHide: true,
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  child.stdout.on('data', (chunk) => stdout.push(chunk));
  child.stderr.on('data', (chunk) => stderr.push(chunk));

  const startedAt = new Date().toISOString();
  let sessionId;
  try {
    await waitReady(baseUrl, child, 60_000);
    const presets = await rpc(baseUrl, 'agentPreset.list', {}, 30_000);
    if (!presets.presets.some((entry) => entry.id === preset)) {
      throw new Error(`DSH 未发现 preset ${preset}`);
    }
    const created = await rpc(baseUrl, 'session.create', { cwd, agentPreset: preset }, 30_000);
    sessionId = created.sessionId;
    await rpc(baseUrl, 'session.selectModel', {
      sessionId,
      provider,
      model,
      reasoningEffort,
    }, 30_000);
    const prompt = await readFile(promptFile, 'utf8');
    await rpc(baseUrl, 'session.prompt', {
      sessionId,
      mode: 'queue',
      content: [{ type: 'text', text: prompt }],
      clientTimeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    }, 30_000);
    const summary = await waitIdle(baseUrl, sessionId, timeoutSeconds * 1_000);
    const events = await readAllHistory(baseUrl, sessionId);
    await writeFile(path.join(privateOutput, 'session.jsonl'), `${events.map((event) => JSON.stringify(event)).join('\n')}\n`, 'utf8');
    await writeFile(path.join(privateOutput, 'session-meta.json'), `${JSON.stringify({
      sessionId,
      preset,
      provider,
      model,
      reasoningEffort,
      cwd,
      startedAt,
      endedAt: new Date().toISOString(),
      summary,
    }, null, 2)}\n`, 'utf8');
    process.stdout.write(`${JSON.stringify({ sessionId, eventCount: events.length, privateOutput })}\n`);
  } finally {
    await terminate(child);
    await writeFile(path.join(privateOutput, 'dsh-web.stdout.log'), Buffer.concat(stdout), 'utf8');
    await writeFile(path.join(privateOutput, 'dsh-web.stderr.log'), Buffer.concat(stderr), 'utf8');
  }
}

main().catch((error) => {
  process.stderr.write(`${error.stack ?? error.message}\n`);
  process.exitCode = 1;
});
