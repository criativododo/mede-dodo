import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync, writeFileSync, mkdirSync, renameSync } from 'node:fs';
import { dirname, resolve, relative, sep } from 'node:path';

export class SessionMemoryError extends Error {}

export function fail(message) {
  throw new SessionMemoryError(message);
}

export function run(command, args, { cwd, allowFailure = false, input } = {}) {
  try {
    return execFileSync(command, args, {
      cwd,
      input,
      encoding: 'utf8',
      stdio: ['pipe', 'pipe', 'pipe'],
    }).trim();
  } catch (error) {
    if (allowFailure) {
      return {
        ok: false,
        status: error.status ?? 1,
        stdout: String(error.stdout ?? '').trim(),
        stderr: String(error.stderr ?? '').trim(),
      };
    }
    const detail = String(error.stderr ?? error.message).trim();
    fail(`${command} ${args.join(' ')} falhou${detail ? `: ${detail}` : ''}`);
  }
}

export function parseArgs(argv) {
  const result = { _: [] };
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith('--')) {
      result._.push(token);
      continue;
    }
    const [key, inlineValue] = token.slice(2).split('=', 2);
    if (inlineValue !== undefined) {
      result[key] = inlineValue;
      continue;
    }
    const next = argv[index + 1];
    if (!next || next.startsWith('--')) {
      result[key] = true;
      continue;
    }
    result[key] = next;
    index += 1;
  }
  return result;
}

export function nowIso() {
  return new Date().toISOString();
}

export function dateParts(iso = nowIso()) {
  const date = new Date(iso);
  const local = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Sao_Paulo',
    year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(date).reduce((acc, part) => ({ ...acc, [part.type]: part.value }), {});
  const time = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'America/Sao_Paulo', hour: '2-digit', minute: '2-digit', hour12: false,
  }).formatToParts(date).reduce((acc, part) => ({ ...acc, [part.type]: part.value }), {});
  return {
    year: local.year,
    month: local.month,
    day: local.day,
    hhmm: `${time.hour}${time.minute}`,
    localDate: `${local.year}-${local.month}-${local.day}`,
  };
}

export function readJson(filePath, fallback) {
  if (!existsSync(filePath)) return fallback;
  return parseJson(readFileSync(filePath, 'utf8'), filePath);
}

export function parseJson(value, label) {
  try {
    return JSON.parse(value);
  } catch (error) {
    fail(`JSON inválido em ${label}: ${error.message}`);
  }
}

export function atomicWrite(filePath, value) {
  mkdirSync(dirname(filePath), { recursive: true });
  const tempPath = `${filePath}.tmp-${process.pid}`;
  writeFileSync(tempPath, value, 'utf8');
  renameSync(tempPath, filePath);
}

export function resolveInside(root, candidate) {
  const resolved = resolve(root, candidate);
  const rootWithSeparator = root.endsWith(sep) ? root : `${root}${sep}`;
  if (resolved !== root && !resolved.startsWith(rootWithSeparator)) {
    fail(`Caminho fora do repositório de memória: ${candidate}`);
  }
  return resolved;
}

export function relativePosix(root, filePath) {
  return relative(root, filePath).split(sep).join('/');
}

export function print(value) {
  process.stdout.write(`${typeof value === 'string' ? value : JSON.stringify(value, null, 2)}\n`);
}

/** Estimativa de custo de contexto: chars do payload e aproximação de tokens (chars / 4). */
export function estimateCost(value) {
  const chars = (typeof value === 'string' ? value : JSON.stringify(value)).length;
  return { chars, approxTokens: Math.round(chars / 4) };
}

export function requireArg(args, name) {
  if (!args[name] || args[name] === true) fail(`Informe --${name}.`);
  return args[name];
}
