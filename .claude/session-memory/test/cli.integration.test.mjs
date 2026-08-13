import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { tempDirectory, git, initGitRepository, writeGlobalGitConfig } from './helpers.mjs';

const repositoryRoot = process.cwd();
const cli = join(repositoryRoot, '.claude/session-memory/bin/session-memory.mjs');
const runCli = (app, args, environment, input) => execFileSync(process.execPath, [cli, ...args], { cwd: app, env: environment, input, encoding: 'utf8' });

function setupFixture(fixture) {
  const app = join(fixture, 'app'); const remote = join(fixture, 'memory-remote.git');
  initGitRepository(app); git(fixture, ['init', '--bare', 'memory-remote.git']); mkdirSync(join(app, '.claude/session-memory'), { recursive: true });
  writeFileSync(join(app, '.claude/session-memory/config.json'), JSON.stringify({ schemaVersion: 1, memoryRepositoryUrl: remote, memoryDirectory: 'memory', journalWindow: 5, checks: {} }));
  return { app, remote, memory: join(fixture, 'memory'), environment: { ...process.env, GIT_CONFIG_GLOBAL: writeGlobalGitConfig(fixture), CRIATIVODODO_MEMORY_DIR: join(fixture, 'memory') } };
}

function detailsJson() {
  return JSON.stringify({ objective: 'Validar fluxo V2', phase: 'Fase 4 — Armazenamento + Workspace Provisioning', sprint: 'Não formalizada', status: 'Parcial', context: 'Teste de integração.', workPerformed: ['Validou o fluxo V2.'], decisions: [], adrsAffected: ['ADR-017 — OAuth dedicado do Google Drive'], problems: [], blockers: ['Bloqueio de teste.'], nextTask: 'Continuar o teste.', statusSummary: 'Resumo de teste da integração.', observations: [], confidence: { level: 'Alta', reason: 'Fixture Git local.' } });
}

test('V2-001/V2-003 — /inicio não requer objetivo e /fim executa journal, commit, push e limpeza em uma transação', () => {
  const fixture = tempDirectory();
  try {
    const { app, memory, environment } = setupFixture(fixture);
    const initial = JSON.parse(runCli(app, ['inicio'], environment));
    assert.equal(initial.executiveSummary.phase, 'Nenhuma sessão registrada ainda.');
    assert.equal(initial.project, 'app', 'projectId inferido do nome da pasta raiz do repositório, sem hardcode');
    assert.equal('session' in initial, false, 'V2 não expõe Session ID artificial');
    assert.deepEqual(initial.driveSync, { active: false, due: false, reason: 'Projeto sem mapeamento google_drive_sync no CLAUDE.md local.' });
    const completed = JSON.parse(runCli(app, ['fim', '--details-stdin'], environment, detailsJson()));
    assert.equal(completed.published, true); assert.match(completed.journal, /^projects\/[a-z0-9-]+\/journals\/\d{4}\/\d{2}\/\d{4}-\d{2}-\d{2}_\d{4}--\w+\.md$/);
    assert.equal(completed.project, 'app');
    assert.equal(existsSync(join(app, '.claude/session-memory/runtime')), false, 'V2 não cria runtime persistente');
    assert.equal(existsSync(join(app, '.claude/session-memory/fim-details.json')), false, '/fim não deixa detalhes temporários no checkout');
    const validation = JSON.parse(runCli(app, ['validate'], environment)); assert.equal(validation.valid, true, validation.errors?.join('\n'));
    assert.equal(existsSync(join(memory, completed.journal)), true);
    const status = JSON.parse(runCli(app, ['status'], environment)); assert.equal(status.phase, 'Fase 4 — Armazenamento + Workspace Provisioning'); assert.equal(status.nextTask, 'Continuar o teste.');
  } finally { rmSync(fixture, { recursive: true, force: true }); }
});

test('V2-006 — arquivos runtime V1 são ignorados e não controlam a recuperação', () => {
  const fixture = tempDirectory();
  try {
    const { app, environment } = setupFixture(fixture);
    mkdirSync(join(app, '.claude/session-memory/runtime'), { recursive: true });
    writeFileSync(join(app, '.claude/session-memory/runtime/legacy.json'), '{"id":"legacy","objective":"não usar"}');
    const initial = JSON.parse(runCli(app, ['inicio'], environment));
    assert.equal(initial.executiveSummary.phase, 'Nenhuma sessão registrada ainda.');
    assert.equal(existsSync(join(app, '.claude/session-memory/runtime/legacy.json')), true, 'compatibilidade: legado não é destruído');
  } finally { rmSync(fixture, { recursive: true, force: true }); }
});

test('checkout principal e git worktree resolvem para o mesmo repositório de memória, sem CRIATIVODODO_MEMORY_DIR explícito', () => {
  const fixture = tempDirectory();
  try {
    const mainCheckout = join(fixture, 'checkout-principal', 'app'); const worktreeApp = join(fixture, 'algum-outro-caminho', 'worktrees', 'sessao-y', 'app'); const fakeHome = join(fixture, 'fake-home'); const remote = join(fixture, 'memory-remote.git');
    mkdirSync(fakeHome, { recursive: true }); initGitRepository(mainCheckout); initGitRepository(worktreeApp); git(fixture, ['init', '--bare', 'memory-remote.git']);
    const config = JSON.stringify({ schemaVersion: 1, memoryRepositoryUrl: remote, memoryDirectory: 'criativododo-memory-teste', journalWindow: 5, checks: {} });
    for (const app of [mainCheckout, worktreeApp]) { mkdirSync(join(app, '.claude/session-memory'), { recursive: true }); writeFileSync(join(app, '.claude/session-memory/config.json'), config); }
    const environment = { ...process.env, GIT_CONFIG_GLOBAL: writeGlobalGitConfig(fixture), HOME: fakeHome }; delete environment.CRIATIVODODO_MEMORY_DIR;
    const fromMain = JSON.parse(runCli(mainCheckout, ['inicio'], environment)); const expectedMemoryPath = join(fakeHome, 'criativododo-memory-teste'); assert.equal(fromMain.initializedMemory, true); assert.equal(existsSync(join(expectedMemoryPath, '.git')), true);
    const fromWorktree = JSON.parse(runCli(worktreeApp, ['inicio'], environment)); assert.equal(fromWorktree.initializedMemory, false); assert.equal(fromWorktree.executiveSummary.phase, fromMain.executiveSummary.phase);
  } finally { rmSync(fixture, { recursive: true, force: true }); }
});

test('dois projetos distintos no mesmo hub de memória ficam isolados — sem projectId hardcoded no kit', () => {
  const fixture = tempDirectory();
  try {
    const remote = join(fixture, 'memory-remote.git'); git(fixture, ['init', '--bare', 'memory-remote.git']);
    const memory = join(fixture, 'memory'); const environment = { ...process.env, GIT_CONFIG_GLOBAL: writeGlobalGitConfig(fixture), CRIATIVODODO_MEMORY_DIR: memory };
    const config = JSON.stringify({ schemaVersion: 1, memoryRepositoryUrl: remote, memoryDirectory: 'memory', journalWindow: 3, checks: {} });

    const projectAlpha = join(fixture, 'projeto-alfa'); initGitRepository(projectAlpha); mkdirSync(join(projectAlpha, '.claude/session-memory'), { recursive: true }); writeFileSync(join(projectAlpha, '.claude/session-memory/config.json'), config);
    const projectBeta = join(fixture, 'projeto-beta'); initGitRepository(projectBeta); mkdirSync(join(projectBeta, '.claude/session-memory'), { recursive: true }); writeFileSync(join(projectBeta, '.claude/session-memory/config.json'), config);

    runCli(projectAlpha, ['inicio'], environment);
    const fimAlpha = JSON.parse(runCli(projectAlpha, ['fim', '--details-stdin'], environment, JSON.stringify({ objective: 'Trabalho no Alfa', phase: 'Fase Alfa', sprint: 'S1', nextTask: 'seguir no alfa' })));
    assert.equal(fimAlpha.project, 'projeto-alfa');

    runCli(projectBeta, ['inicio'], environment);
    const fimBeta = JSON.parse(runCli(projectBeta, ['fim', '--details-stdin'], environment, JSON.stringify({ objective: 'Trabalho no Beta', phase: 'Fase Beta', sprint: 'S1', nextTask: 'seguir no beta' })));
    assert.equal(fimBeta.project, 'projeto-beta');

    const alphaStatus = JSON.parse(runCli(projectAlpha, ['status'], environment)); assert.equal(alphaStatus.phase, 'Fase Alfa');
    const betaStatus = JSON.parse(runCli(projectBeta, ['status'], environment)); assert.equal(betaStatus.phase, 'Fase Beta');
    assert.equal(JSON.parse(runCli(projectAlpha, ['journal'], environment)).length, 1);
    assert.equal(JSON.parse(runCli(projectBeta, ['journal'], environment)).length, 1);
  } finally { rmSync(fixture, { recursive: true, force: true }); }
});

test('sincronização com Drive é puramente declarativa via CLAUDE.md — /inicio nunca sincroniza sozinho', () => {
  const fixture = tempDirectory();
  try {
    const { app, environment } = setupFixture(fixture);
    const driveFolder = join(fixture, 'drive-folder');
    writeFileSync(join(app, 'CLAUDE.md'), ['# CLAUDE.md', '', '```google_drive_sync', `path: ${driveFolder}`, '```', ''].join('\n'));

    const initial = JSON.parse(runCli(app, ['inicio'], environment));
    assert.equal(initial.driveSync.active, true);
    assert.equal(initial.driveSync.due, true, 'nunca sincronizado ainda — está pronto, mas /inicio só relata, não executa');

    const check = JSON.parse(runCli(app, ['drive'], environment));
    assert.equal(check.due, true);

    const marked = JSON.parse(runCli(app, ['drive', '--mark'], environment));
    assert.equal(marked.published, true);
    assert.equal(marked.driveSync.due, true, 'comando manual: sempre due=true na própria confirmação');

    const rechecked = JSON.parse(runCli(app, ['drive'], environment));
    assert.equal(rechecked.due, false, 'logo após marcar, ainda não passaram 6h');
  } finally { rmSync(fixture, { recursive: true, force: true }); }
});

test('drive --run copia só os documentos elegíveis, de forma idempotente, e reporta o link do NotebookLM', () => {
  const fixture = tempDirectory();
  try {
    const { app, environment } = setupFixture(fixture);
    const driveFolder = join(fixture, 'drive-folder');
    mkdirSync(driveFolder, { recursive: true });
    const notebookUrl = 'https://notebook.google.com/notebook/62f4b450-72af-4b89-b32a-b05c91765b96';
    writeFileSync(join(app, 'CLAUDE.md'), ['# CLAUDE.md', '', '```google_drive_sync', `path: ${driveFolder}`, `notebooklm_url: ${notebookUrl}`, '```', ''].join('\n'));
    writeFileSync(join(app, 'README.md'), '# projeto');
    mkdirSync(join(app, 'specs'), { recursive: true });
    writeFileSync(join(app, 'specs/SPEC-001.md'), '# spec');
    writeFileSync(join(app, 'app.py'), 'print(1)');

    const first = JSON.parse(runCli(app, ['drive', '--run'], environment));
    assert.equal(first.driveFolder, driveFolder);
    assert.equal(first.notebookUrl, notebookUrl);
    assert.deepEqual(first.synced.sort(), ['README.md', 'specs/SPEC-001.md']);
    assert.equal(existsSync(join(driveFolder, 'README.md')), true);
    assert.equal(existsSync(join(driveFolder, 'specs/SPEC-001.md')), true);
    assert.equal(existsSync(join(driveFolder, 'app.py')), false, 'código-fonte nunca é sincronizado');

    const second = JSON.parse(runCli(app, ['drive', '--run'], environment));
    assert.deepEqual(second.synced, [], 'nada mudou desde a última cópia — idempotente');
    assert.deepEqual(second.skipped.sort(), ['README.md', 'specs/SPEC-001.md']);
  } finally { rmSync(fixture, { recursive: true, force: true }); }
});

test('drive --run sem mapeamento ou sem a pasta montada falha com erro claro, sem tentar contornar', () => {
  const fixture = tempDirectory();
  try {
    const { app, environment } = setupFixture(fixture);
    assert.throws(() => runCli(app, ['drive', '--run'], environment), /google_drive_sync/);

    writeFileSync(join(app, 'CLAUDE.md'), ['# CLAUDE.md', '', '```google_drive_sync', `path: ${join(fixture, 'pasta-inexistente')}`, '```', ''].join('\n'));
    assert.throws(() => runCli(app, ['drive', '--run'], environment), /não encontrada|montada/);
  } finally { rmSync(fixture, { recursive: true, force: true }); }
});
