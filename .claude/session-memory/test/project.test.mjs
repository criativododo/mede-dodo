import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { basename, join } from 'node:path';
import { tempDirectory, git, initGitRepository } from './helpers.mjs';
import { resolveProjectId, slugify } from '../lib/project.mjs';

test('slugify: normaliza acentos, caixa e pontuação para um identificador estável', () => {
  assert.equal(slugify('Criativo Dodô! Portal_v2'), 'criativo-dodo-portal-v2');
  assert.equal(slugify('  --já com traços--  '), 'ja-com-tracos');
  assert.equal(slugify(''), 'projeto');
  assert.equal(slugify(null), 'projeto');
});

test('resolveProjectId: repositório Git com remote usa o nome do repositório remoto, não um caminho fixo', () => {
  const fixture = tempDirectory();
  try {
    const repo = join(fixture, 'qualquer-pasta-local');
    initGitRepository(repo);
    const bare = join(fixture, 'algum-outro-nome.git');
    git(repo, ['init', '--bare', bare]);
    git(repo, ['remote', 'add', 'origin', bare]);
    assert.equal(resolveProjectId(repo), 'algum-outro-nome');
  } finally {
    rmSync(fixture, { recursive: true, force: true });
  }
});

test('resolveProjectId: repositório Git sem remote cai para o nome da pasta raiz do worktree', () => {
  const fixture = tempDirectory();
  try {
    const repo = join(fixture, 'Meu Repo Sem Remote');
    initGitRepository(repo);
    assert.equal(resolveProjectId(repo), slugify(basename(repo)));
  } finally {
    rmSync(fixture, { recursive: true, force: true });
  }
});

test('resolveProjectId: fora de um repositório Git usa o campo name do package.json', () => {
  const fixture = tempDirectory();
  try {
    const dir = join(fixture, 'pasta-qualquer');
    mkdirSync(dir, { recursive: true });
    writeFileSync(join(dir, 'package.json'), JSON.stringify({ name: '@escopo/meu-pacote' }));
    assert.equal(resolveProjectId(dir), 'escopo-meu-pacote');
  } finally {
    rmSync(fixture, { recursive: true, force: true });
  }
});

test('resolveProjectId: sem Git e sem package.json usa o nome da pasta corrente', () => {
  const fixture = tempDirectory();
  try {
    const dir = join(fixture, 'Pasta Final');
    mkdirSync(dir, { recursive: true });
    assert.equal(resolveProjectId(dir), slugify(basename(dir)));
  } finally {
    rmSync(fixture, { recursive: true, force: true });
  }
});

test('resolveProjectId: override explícito (flag ou env) tem prioridade sobre qualquer inferência', () => {
  const fixture = tempDirectory();
  try {
    const repo = join(fixture, 'repo');
    initGitRepository(repo);
    assert.equal(resolveProjectId(repo, { override: 'Outro Projeto' }), 'outro-projeto');

    const original = process.env.CRIATIVODODO_PROJECT_ID;
    process.env.CRIATIVODODO_PROJECT_ID = 'via-env';
    try {
      assert.equal(resolveProjectId(repo), 'via-env');
    } finally {
      if (original === undefined) delete process.env.CRIATIVODODO_PROJECT_ID; else process.env.CRIATIVODODO_PROJECT_ID = original;
    }
  } finally {
    rmSync(fixture, { recursive: true, force: true });
  }
});
