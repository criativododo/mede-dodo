import test from 'node:test';
import assert from 'node:assert/strict';
import { rmSync, mkdirSync, symlinkSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { tempDirectory, initGitRepository, git } from './helpers.mjs';
import { resolveMemoryBranch, sourceSnapshot } from '../lib/git.mjs';

test('deriva a branch remota publicada sem assumir main', () => {
  const directory = tempDirectory();
  try {
    initGitRepository(directory);
    git(directory, ['branch', '-M', 'trunk']);
    const remote = join(directory, 'remote.git');
    git(directory, ['init', '--bare', remote]);
    git(directory, ['remote', 'add', 'origin', remote]);
    git(directory, ['push', '-u', 'origin', 'trunk']);
    assert.equal(resolveMemoryBranch(directory), 'trunk');
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test('sourceSnapshot não quebra com um symlink não rastreado apontando para um diretório', () => {
  // Reproduz o crash real: um pacote (ex. streamlit) registra um symlink em
  // .claude/skills/<algo> apontando para uma pasta dentro de .venv/. git ls-files
  // lista o symlink como uma única entrada; existsSync/readFileSync seguem o link e
  // caem no diretório, o que antes derrubava sourceSnapshot com EISDIR.
  const directory = tempDirectory();
  try {
    initGitRepository(directory);

    const targetDir = join(directory, 'vendored-package', 'skills', 'algo');
    mkdirSync(targetDir, { recursive: true });
    writeFileSync(join(targetDir, 'SKILL.md'), '# não deveria ser lido\n');

    const skillsDir = join(directory, '.claude', 'skills');
    mkdirSync(skillsDir, { recursive: true });
    symlinkSync(targetDir, join(skillsDir, 'algo'), 'dir');

    const snapshot = sourceSnapshot(directory);

    assert.ok(!Object.keys(snapshot.files).includes('.claude/skills/algo'));
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});
