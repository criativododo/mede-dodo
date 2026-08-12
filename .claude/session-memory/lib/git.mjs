import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { run, fail } from './core.mjs';

export function git(args, cwd, options) {
  return run('git', args, { cwd, ...options });
}

export function isGitRepository(directory) {
  const result = git(['rev-parse', '--is-inside-work-tree'], directory, { allowFailure: true });
  return result === 'true';
}

export function ensureGitRepository(directory, label) {
  if (!isGitRepository(directory)) fail(`${label} não é um repositório Git: ${directory}`);
}

function splitNull(value) {
  return value ? value.split('\0').filter(Boolean) : [];
}

function hashFile(filePath) {
  return createHash('sha256').update(readFileSync(filePath)).digest('hex');
}

export function isSensitivePath(filePath) {
  const name = filePath.toLowerCase();
  return /(^|\/)\.env(?:\.|$)/.test(name)
    || /client_secret|credential|refresh_token|secret|private[._-]?key|\.pem$|\.p12$/.test(name);
}

export function redactPath(filePath) {
  return isSensitivePath(filePath) ? '[arquivo sensível redigido]' : filePath;
}

export function sourceSnapshot(root) {
  ensureGitRepository(root, 'Repositório da aplicação');
  const tracked = splitNull(git(['ls-files', '-z'], root));
  const untracked = splitNull(git(['ls-files', '--others', '--exclude-standard', '-z'], root));
  const files = {};
  for (const filePath of new Set([...tracked, ...untracked])) {
    if (filePath.startsWith('.claude/session-memory/runtime/')) continue;
    const absolutePath = join(root, filePath);
    if (existsSync(absolutePath)) files[filePath] = hashFile(absolutePath);
  }
  const branchResult = git(['symbolic-ref', '--quiet', '--short', 'HEAD'], root, { allowFailure: true });
  return {
    head: git(['rev-parse', 'HEAD'], root),
    branch: typeof branchResult === 'string' ? branchResult : 'HEAD destacada',
    status: git(['status', '--porcelain=v1'], root),
    files,
  };
}

/**
 * Estado de alterações que pode ser derivado em qualquer processo, sem um baseline
 * persistido de sessão. É usado pelo journal V2: arquivos rastreados são comparados
 * com HEAD e arquivos não rastreados entram como criados.
 */
export function changedFilesFromGitState(root) {
  ensureGitRepository(root, 'Repositório da aplicação');
  const output = git(['diff', '--name-status', 'HEAD'], root);
  const created = [];
  const modified = [];
  const removed = [];
  for (const line of output.split('\n').filter(Boolean)) {
    const [status, ...parts] = line.split('\t');
    const filePath = parts.at(-1);
    if (!filePath) continue;
    if (status.startsWith('A')) created.push(redactPath(filePath));
    else if (status.startsWith('D')) removed.push(redactPath(filePath));
    else modified.push(redactPath(filePath));
  }
  for (const filePath of splitNull(git(['ls-files', '--others', '--exclude-standard', '-z'], root))) {
    if (!filePath.startsWith('.claude/session-memory/runtime/')) created.push(redactPath(filePath));
  }
  const compare = (a, b) => a.localeCompare(b, 'pt-BR');
  return {
    current: sourceSnapshot(root),
    created: [...new Set(created)].sort(compare),
    modified: [...new Set(modified)].sort(compare),
    removed: [...new Set(removed)].sort(compare),
  };
}

export function commitsSince(root, baselineHead) {
  const output = git(['log', '--format=%H%x1f%h%x1f%ad%x1f%s', '--date=iso-strict', `${baselineHead}..HEAD`], root);
  if (!output) return [];
  return output.split('\n').filter(Boolean).map((line) => {
    const [hash, shortHash, date, subject] = line.split('\x1f');
    return { hash, shortHash, date, subject };
  });
}

/** Commits desde uma referência quando ela é informada; sem baseline, o journal V2
 * registra somente o HEAD atual, que é a evidência técnica derivável no encerramento. */
export function commitsSinceHead(root, from) {
  if (from) return commitsSince(root, from);
  const output = git(['log', '-1', '--format=%H%x1f%h%x1f%ad%x1f%s', '--date=iso-strict'], root);
  if (!output) return [];
  const [hash, shortHash, date, subject] = output.split('\x1f');
  return [{ hash, shortHash, date, subject }];
}

/**
 * Descobre a branch publicada do repositório de memória sem assumir um nome.
 * A configuração explícita é o fallback para remotos sem HEAD simbólico e sem
 * upstream local identificável.
 */
export function resolveMemoryBranch(repositoryPath, configuredBranch) {
  if (configuredBranch) return configuredBranch;

  const upstream = git(['rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}'], repositoryPath, { allowFailure: true });
  if (typeof upstream === 'string' && upstream.startsWith('origin/')) return upstream.slice('origin/'.length);

  const remoteHead = git(['symbolic-ref', '--quiet', '--short', 'refs/remotes/origin/HEAD'], repositoryPath, { allowFailure: true });
  if (typeof remoteHead === 'string' && remoteHead.startsWith('origin/')) return remoteHead.slice('origin/'.length);

  const branches = git(['for-each-ref', '--format=%(refname:strip=3)', 'refs/remotes/origin'], repositoryPath, { allowFailure: true });
  const candidates = typeof branches === 'string'
    ? branches.split('\n').filter((branch) => branch && branch !== 'HEAD')
    : [];
  if (candidates.length === 1) return candidates[0];

  fail('Não foi possível determinar a branch da memória. Configure memoryBranch em .claude/session-memory/config.local.json.');
}

/**
 * Worktrees efêmeros por sessão (ADR-021, Fase 3): cada sessão opera em seu próprio
 * `git worktree`, isolado do repositório "hub" e de qualquer outra sessão — nenhum
 * processo compartilha um working tree mutável com outro.
 */
export function addSessionWorktree(hubPath, worktreePath, ref) {
  git(['worktree', 'add', '--detach', worktreePath, ref], hubPath);
}

export function removeSessionWorktree(hubPath, worktreePath) {
  const result = git(['worktree', 'remove', '--force', worktreePath], hubPath, { allowFailure: true });
  if (typeof result === 'string') return;
  // diretório já pode ter sido apagado manualmente; apenas limpa o registro administrativo.
  git(['worktree', 'prune'], hubPath, { allowFailure: true });
}
