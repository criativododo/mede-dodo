import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { tempDirectory } from './helpers.mjs';
import { evaluateDriveSync, markDriveSynced, planDriveSync, readDriveConfig, readDriveSyncState, syncDriveFiles } from '../lib/drive.mjs';

function writeClaudeMd(root, body) {
  mkdirSync(root, { recursive: true });
  writeFileSync(join(root, 'CLAUDE.md'), body, 'utf8');
}

test('readDriveConfig: projeto sem CLAUDE.md não tem sincronização declarada', () => {
  const dir = tempDirectory();
  try {
    assert.equal(readDriveConfig(dir), null);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('readDriveConfig: CLAUDE.md sem o bloco google_drive_sync não ativa sincronização', () => {
  const dir = tempDirectory();
  try {
    writeClaudeMd(dir, '# CLAUDE.md\n\nSem nenhum mapeamento de Drive aqui.\n');
    assert.equal(readDriveConfig(dir), null);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('readDriveConfig: bloco declarativo presente é a única fonte de verdade', () => {
  const dir = tempDirectory();
  try {
    writeClaudeMd(dir, [
      '# CLAUDE.md', '',
      '```google_drive_sync',
      'path: /Users/exemplo/Drive/Meu Projeto',
      '```', '',
    ].join('\n'));
    const config = readDriveConfig(dir);
    assert.deepEqual(config, { path: '/Users/exemplo/Drive/Meu Projeto' });
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('evaluateDriveSync: sem mapeamento, nunca ativo — nenhuma tentativa de sincronização', () => {
  const result = evaluateDriveSync({ config: null, state: null });
  assert.equal(result.active, false);
  assert.equal(result.due, false);
});

test('evaluateDriveSync: com mapeamento, comando manual sempre está pronto para sincronizar', () => {
  const result = evaluateDriveSync({ config: { path: '/x' }, state: { lastSyncedAt: new Date().toISOString() }, manualTrigger: true });
  assert.equal(result.active, true);
  assert.equal(result.due, true);
});

test('evaluateDriveSync: sem sincronização manual, só fica pronto após 6h da última sincronização', () => {
  const now = new Date('2026-08-09T12:00:00.000Z');
  const justSynced = evaluateDriveSync({ config: { path: '/x' }, state: { lastSyncedAt: '2026-08-09T10:00:00.000Z' }, now });
  assert.equal(justSynced.due, false);

  const sixHoursAgo = evaluateDriveSync({ config: { path: '/x' }, state: { lastSyncedAt: '2026-08-09T06:00:00.000Z' }, now });
  assert.equal(sixHoursAgo.due, true);

  const neverSynced = evaluateDriveSync({ config: { path: '/x' }, state: { lastSyncedAt: null }, now });
  assert.equal(neverSynced.due, true);
});

test('markDriveSynced/readDriveSyncState: round-trip persiste o horário por projeto', () => {
  const dir = tempDirectory();
  try {
    const before = readDriveSyncState(dir, 'meu-projeto');
    assert.equal(before.lastSyncedAt, null);
    markDriveSynced(dir, 'meu-projeto', '2026-08-09T09:00:00.000Z');
    const after = readDriveSyncState(dir, 'meu-projeto');
    assert.equal(after.lastSyncedAt, '2026-08-09T09:00:00.000Z');
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('markDriveSynced: sem manifesto explícito, preserva o manifesto anterior (só o timestamp muda)', () => {
  const dir = tempDirectory();
  try {
    markDriveSynced(dir, 'meu-projeto', '2026-08-09T09:00:00.000Z', { 'README.md': 'abc' });
    markDriveSynced(dir, 'meu-projeto', '2026-08-09T15:00:00.000Z');
    const after = readDriveSyncState(dir, 'meu-projeto');
    assert.equal(after.lastSyncedAt, '2026-08-09T15:00:00.000Z');
    assert.deepEqual(after.files, { 'README.md': 'abc' });
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('readDriveConfig: chaves extras do bloco (ex.: notebooklm_url) ficam disponíveis dinamicamente', () => {
  const dir = tempDirectory();
  try {
    writeClaudeMd(dir, [
      '# CLAUDE.md', '',
      '```google_drive_sync',
      'path: /Users/exemplo/Drive/Meu Projeto',
      'notebooklm_url: https://notebook.google.com/notebook/abc',
      '```', '',
    ].join('\n'));
    const config = readDriveConfig(dir);
    assert.equal(config.notebooklm_url, 'https://notebook.google.com/notebook/abc');
    assert.equal(evaluateDriveSync({ config, state: null }).notebookUrl, 'https://notebook.google.com/notebook/abc');
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('planDriveSync: qualquer .md de raiz entra (nomenclatura livre por projeto), CLAUDE.md fica de fora, código e build ficam de fora', () => {
  const dir = tempDirectory();
  try {
    mkdirSync(dir, { recursive: true });
    writeFileSync(join(dir, 'README.md'), '# readme');
    writeFileSync(join(dir, 'DUMMY.md'), '# dummy');
    writeFileSync(join(dir, 'FINDER-0001.md'), '# finder');
    writeFileSync(join(dir, 'GUIA-PROMPTS-NOTEBOOKLM.md'), '# guia — nome livre, não está em nenhuma lista fixa');
    writeFileSync(join(dir, 'CLAUDE.md'), '# configuração do agente — nunca espelhada');
    writeFileSync(join(dir, 'app.py'), 'print(1)');
    mkdirSync(join(dir, 'specs'), { recursive: true });
    writeFileSync(join(dir, 'specs/SPEC-001.md'), '# spec');
    mkdirSync(join(dir, 'decisions'), { recursive: true });
    writeFileSync(join(dir, 'decisions/ADR-001.md'), '# adr');
    mkdirSync(join(dir, 'docs/issues'), { recursive: true });
    writeFileSync(join(dir, 'docs/issues/ISSUE-0001.md'), '# issue');
    mkdirSync(join(dir, '.venv/lib'), { recursive: true });
    writeFileSync(join(dir, '.venv/lib/site.md'), '# não deve entrar');
    mkdirSync(join(dir, 'legado'), { recursive: true });
    writeFileSync(join(dir, 'legado/antigo.md'), '# não deve entrar');

    const files = planDriveSync(dir);
    assert.deepEqual(files, [
      'DUMMY.md', 'FINDER-0001.md', 'GUIA-PROMPTS-NOTEBOOKLM.md', 'README.md',
      'decisions/ADR-001.md', 'docs/issues/ISSUE-0001.md', 'specs/SPEC-001.md',
    ]);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('syncDriveFiles: só copia arquivos novos/alterados (idempotência via sha-256) e nunca apaga órfãos no destino', () => {
  const root = tempDirectory();
  const dest = tempDirectory();
  try {
    writeFileSync(join(root, 'README.md'), 'v1');
    writeFileSync(join(dest, 'ORFAO.md'), 'preservar');

    const first = syncDriveFiles({ root, destFolder: dest, files: ['README.md'], previousManifest: {} });
    assert.deepEqual(first.synced, ['README.md']);
    assert.deepEqual(first.skipped, []);
    assert.equal(readFileSync(join(dest, 'README.md'), 'utf8'), 'v1');
    assert.equal(existsSync(join(dest, 'ORFAO.md')), true, 'nunca deleta o que não tem correspondente local');

    const second = syncDriveFiles({ root, destFolder: dest, files: ['README.md'], previousManifest: first.manifest });
    assert.deepEqual(second.synced, [], 'sem mudança de conteúdo, não regrava');
    assert.deepEqual(second.skipped, ['README.md']);

    writeFileSync(join(root, 'README.md'), 'v2');
    const third = syncDriveFiles({ root, destFolder: dest, files: ['README.md'], previousManifest: second.manifest });
    assert.deepEqual(third.synced, ['README.md'], 'conteúdo mudou — hash diferente, regrava');
    assert.equal(readFileSync(join(dest, 'README.md'), 'utf8'), 'v2');
  } finally {
    rmSync(root, { recursive: true, force: true });
    rmSync(dest, { recursive: true, force: true });
  }
});
