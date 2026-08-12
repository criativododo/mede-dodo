import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { tempDirectory, git, initGitRepository, writeGlobalGitConfig } from './helpers.mjs';
import { publishSessionWorktree } from '../lib/publish.mjs';
import { git as realGit } from '../lib/git.mjs';

const repositoryRoot = process.cwd(); const cli = join(repositoryRoot, '.claude/session-memory/bin/session-memory.mjs');
const runCli = (app, args, environment, input) => execFileSync(process.execPath, [cli, ...args], { cwd: app, env: environment, input, encoding: 'utf8' });
function setup(fixture) { const app = join(fixture, 'app'); const remote = join(fixture, 'memory-remote.git'); initGitRepository(app); git(fixture, ['init', '--bare', 'memory-remote.git']); mkdirSync(join(app, '.claude/session-memory'), { recursive: true }); writeFileSync(join(app, '.claude/session-memory/config.json'), JSON.stringify({ schemaVersion: 1, memoryRepositoryUrl: remote, memoryDirectory: 'memory', journalWindow: 5, checks: {} })); return { app, environment: { ...process.env, GIT_CONFIG_GLOBAL: writeGlobalGitConfig(fixture), CRIATIVODODO_MEMORY_DIR: join(fixture, 'memory') } }; }
function details(objective) { return JSON.stringify({ objective, phase: 'Fase de teste', sprint: 'S1', status: 'Parcial', context: 'Teste.', workPerformed: [], decisions: [], adrsAffected: [], problems: [], blockers: [], nextTask: 'tarefa', observations: [], confidence: { level: 'Alta', reason: 'teste' } }); }

test('V2-004/V2-005 — /fim usa worktree efêmero e uma nova abertura recupera somente pelo Git após interrupção', () => {
  const fixture = tempDirectory();
  try { const { app, environment } = setup(fixture); runCli(app, ['inicio'], environment); const result = JSON.parse(runCli(app, ['fim', '--details-stdin'], environment, details('Sessão A'))); assert.equal(result.published, true); assert.equal(JSON.parse(runCli(app, ['inicio'], environment)).executiveSummary.latestJournals.length, 1); }
  finally { rmSync(fixture, { recursive: true, force: true }); }
});

test('V2 — duas finalizações consecutivas preservam journals independentes sem estado de sessão compartilhado', () => {
  const fixture = tempDirectory();
  try { const { app, environment } = setup(fixture); runCli(app, ['inicio'], environment); runCli(app, ['fim', '--details-stdin'], environment, details('Sessão A')); runCli(app, ['fim', '--details-stdin'], environment, details('Sessão B')); const journals = JSON.parse(runCli(app, ['journal'], environment)); assert.equal(journals.length, 2); assert.deepEqual(new Set(journals.map((journal) => journal.objective)), new Set(['Sessão A', 'Sessão B'])); }
  finally { rmSync(fixture, { recursive: true, force: true }); }
});

test('worktree temporário faz retry de publicação sem force-push', () => {
  const fixture = tempDirectory();
  try {
    const remote = join(fixture, 'memory-remote.git'); git(fixture, ['init', '--bare', 'memory-remote.git']); const seed = join(fixture, 'seed'); initGitRepository(seed); git(seed, ['remote', 'add', 'origin', remote]); git(seed, ['push', '-q', '-u', 'origin', 'HEAD:main']); const worktree = join(fixture, 'worktree'); git(seed, ['worktree', 'add', '--detach', worktree, 'origin/main']);
    let pushes = 0; const gitFn = (args, cwd, options) => { if (args[0] === 'push' && pushes++ === 0) return { ok: false, status: 1, stdout: '', stderr: 'rejeitado' }; return realGit(args, cwd, options); };
    const result = publishSessionWorktree({ worktree, remoteBranch: 'main', message: 'teste', prepareCommit: (wt) => writeFileSync(join(wt, 'journal.md'), 'conteúdo\n'), gitFn }); assert.equal(result.published, true); assert.equal(result.attempts, 2);
  } finally { rmSync(fixture, { recursive: true, force: true }); }
});
