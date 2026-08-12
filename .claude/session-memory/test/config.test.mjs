import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { tempDirectory } from './helpers.mjs';
import { loadConfig, resolveMemoryPath } from '../lib/config.mjs';

function withEnv(overrides, run) {
  const originals = {};
  for (const key of Object.keys(overrides)) originals[key] = process.env[key];
  Object.assign(process.env, overrides);
  try {
    return run();
  } finally {
    for (const key of Object.keys(overrides)) {
      if (originals[key] === undefined) delete process.env[key];
      else process.env[key] = originals[key];
    }
  }
}

function withCwd(directory, run) {
  const original = process.cwd();
  process.chdir(directory);
  try {
    return run();
  } finally {
    process.chdir(original);
  }
}

test('resolveMemoryPath: caminho absoluto do config é usado como está, independente do cwd', () => {
  const absolute = '/var/tmp/memoria-canonica';
  withEnv({ CRIATIVODODO_MEMORY_DIR: '' }, () => {
    assert.equal(resolveMemoryPath(absolute), absolute);
  });
});

test('resolveMemoryPath: caminho relativo do config resolve contra o home, nunca contra o cwd', () => {
  withEnv({ CRIATIVODODO_MEMORY_DIR: '' }, () => {
    const expected = join(homedir(), 'criativododo-memory');
    const first = withCwd('/tmp', () => resolveMemoryPath('criativododo-memory'));
    const second = withCwd(homedir(), () => resolveMemoryPath('criativododo-memory'));
    assert.equal(first, expected);
    assert.equal(second, expected);
    assert.equal(first, second);
  });
});

test('resolveMemoryPath: CRIATIVODODO_MEMORY_DIR absoluto tem prioridade sobre o config', () => {
  const envAbsolute = '/var/tmp/memoria-via-env';
  withEnv({ CRIATIVODODO_MEMORY_DIR: envAbsolute }, () => {
    assert.equal(resolveMemoryPath('../qualquer-coisa-relativa'), envAbsolute);
  });
});

test('resolveMemoryPath: CRIATIVODODO_MEMORY_DIR relativo também resolve contra o home, não contra o cwd', () => {
  withEnv({ CRIATIVODODO_MEMORY_DIR: 'memoria-alternativa' }, () => {
    const expected = join(homedir(), 'memoria-alternativa');
    const fromArbitraryCwd = withCwd('/tmp', () => resolveMemoryPath('config-nunca-usado'));
    assert.equal(fromArbitraryCwd, expected);
  });
});

test('resolveMemoryPath: mesmo resultado a partir do checkout principal, de um worktree ou de um cwd arbitrário', () => {
  const fixture = tempDirectory();
  try {
    const mainCheckout = join(fixture, 'checkout-principal');
    const worktree = join(fixture, 'checkout-principal', '.claude', 'worktrees', 'sessao-x');
    const arbitraryCwd = join(fixture, 'em-qualquer-outro-lugar', 'sub', 'dir');
    mkdirSync(mainCheckout, { recursive: true });
    mkdirSync(worktree, { recursive: true });
    mkdirSync(arbitraryCwd, { recursive: true });
    withEnv({ CRIATIVODODO_MEMORY_DIR: '' }, () => {
      const results = [mainCheckout, worktree, arbitraryCwd].map((cwd) =>
        withCwd(cwd, () => resolveMemoryPath('criativododo-memory')));
      assert.equal(new Set(results).size, 1);
      assert.equal(results[0], join(homedir(), 'criativododo-memory'));
    });
  } finally {
    rmSync(fixture, { recursive: true, force: true });
  }
});

test('loadConfig: memoryPath final não depende do diretório de invocação (root)', () => {
  const fixture = tempDirectory();
  try {
    const mainCheckout = join(fixture, 'checkout-principal');
    const worktree = join(fixture, 'worktrees', 'sessao-x');
    for (const root of [mainCheckout, worktree]) {
      mkdirSync(join(root, '.claude/session-memory'), { recursive: true });
      writeFileSync(join(root, '.claude/session-memory/config.json'), JSON.stringify({
        schemaVersion: 1,
        memoryRepositoryUrl: 'https://example.test/memoria.git',
        memoryDirectory: 'criativododo-memory',
        journalWindow: 5,
        checks: {},
      }));
    }
    withEnv({ CRIATIVODODO_MEMORY_DIR: join(fixture, 'memoria-canonica') }, () => {
      const configFromMain = loadConfig(mainCheckout);
      const configFromWorktree = loadConfig(worktree);
      assert.equal(configFromMain.memoryPath, join(fixture, 'memoria-canonica'));
      assert.equal(configFromMain.memoryPath, configFromWorktree.memoryPath);
    });
  } finally {
    rmSync(fixture, { recursive: true, force: true });
  }
});
