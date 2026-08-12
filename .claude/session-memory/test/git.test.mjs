import test from 'node:test';
import assert from 'node:assert/strict';
import { rmSync } from 'node:fs';
import { join } from 'node:path';
import { tempDirectory, initGitRepository, git } from './helpers.mjs';
import { resolveMemoryBranch } from '../lib/git.mjs';

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
