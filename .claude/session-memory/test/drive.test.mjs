import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { tempDirectory } from './helpers.mjs';
import { evaluateDriveSync, markDriveSynced, readDriveConfig, readDriveSyncState } from '../lib/drive.mjs';

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
