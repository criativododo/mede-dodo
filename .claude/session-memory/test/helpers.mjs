import { execFileSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, mkdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

export function tempDirectory(prefix = 'session-memory-') {
  return mkdtempSync(join(tmpdir(), prefix));
}

export function git(directory, args) {
  return execFileSync('git', args, { cwd: directory, encoding: 'utf8' }).trim();
}

export function initGitRepository(directory) {
  mkdirSync(directory, { recursive: true });
  git(directory, ['init']);
  git(directory, ['config', 'user.name', 'Session Memory Test']);
  git(directory, ['config', 'user.email', 'session-memory@example.test']);
  writeFileSync(join(directory, 'README.md'), '# fixture\n');
  git(directory, ['add', 'README.md']);
  git(directory, ['commit', '-m', 'initial fixture']);
}

export function writeGlobalGitConfig(directory) {
  const filePath = join(directory, 'gitconfig');
  writeFileSync(filePath, '[user]\n\tname = Session Memory Test\n\temail = session-memory@example.test\n');
  return filePath;
}
