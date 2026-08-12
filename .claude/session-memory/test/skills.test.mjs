import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const root = process.cwd();

test('as seis skills públicas de sessão possuem frontmatter e invocam o CLI', () => {
  for (const name of ['inicio', 'fim', 'status', 'journal', 'roadmap', 'check']) {
    const content = readFileSync(join(root, '.claude/skills', name, 'SKILL.md'), 'utf8');
    assert.match(content, new RegExp(`name: ${name}`));
    assert.match(content, /disable-model-invocation: true/);
    assert.match(content, /session-memory\.mjs/);
  }
});
