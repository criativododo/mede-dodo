import { basename, dirname, join } from 'node:path';
import { readJson } from './core.mjs';
import { git, isGitRepository } from './git.mjs';

/**
 * Nenhum nome de projeto é conhecido de antemão pelo kit: o identificador é sempre
 * inferido da pasta ativa no momento da invocação, para que o mesmo código sirva
 * qualquer repositório presente ou futuro sem alteração.
 */
export function slugify(value) {
  const base = String(value ?? '')
    .normalize('NFKD').replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/\.git$/, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return base || 'projeto';
}

function nameFromRemote(root) {
  const url = git(['remote', 'get-url', 'origin'], root, { allowFailure: true });
  if (typeof url !== 'string' || !url.trim()) return null;
  const cleaned = url.trim().replace(/\/$/, '').replace(/\.git$/, '');
  return cleaned.split(/[/:]/).filter(Boolean).pop() || null;
}

/**
 * Substitui o antigo `nameFromGitToplevel` (`git rev-parse --show-toplevel`), que dentro
 * de um Git worktree (`.claude/worktrees/<nome>`) retornava a raiz do PRÓPRIO worktree,
 * não do repositório principal — projectId incorreto (bug documentado em
 * `~/1. PROJECTS/DEBUG-INICIO-FIM.md`, 2026-08-10). `--git-common-dir` sempre aponta para
 * o `.git` real e compartilhado do repositório principal, em worktree ou não; `dirname()`
 * disso é a raiz real do projeto, independente de a partir de qual worktree a sessão foi
 * iniciada.
 */
function nameFromGitCommonDir(root) {
  const commonDir = git(['rev-parse', '--path-format=absolute', '--git-common-dir'], root, { allowFailure: true });
  if (typeof commonDir !== 'string' || !commonDir.trim()) return null;
  return basename(dirname(commonDir.trim()));
}

function nameFromPackageJson(root) {
  const manifest = readJson(join(root, 'package.json'), null);
  return manifest?.name ? String(manifest.name) : null;
}

/**
 * Resolve o identificador do projeto ativo a partir da pasta corrente, nesta ordem:
 * 1. Nome do repositório Git (remote `origin`, com fallback ao diretório Git comum —
 *    `--git-common-dir` — que resolve corretamente tanto em checkout normal quanto em
 *    worktree, ao contrário do antigo fallback por `--show-toplevel`).
 * 2. Campo `name` do `package.json` na raiz informada, se o passo 1 não se aplicar
 *    (diretório fora de um repositório Git, ou repositório sem remote e sem git-common-dir
 *    legível).
 * 3. Nome da própria pasta corrente.
 * `--project`/`CRIATIVODODO_PROJECT_ID` permitem um override explícito (ex.: testes,
 * ou uma sessão que precise gravar memória de um projeto diferente do cwd atual).
 */
export function resolveProjectId(root, { override } = {}) {
  const explicit = override ?? process.env.CRIATIVODODO_PROJECT_ID;
  if (explicit && String(explicit).trim()) return slugify(explicit);

  let candidate = null;
  if (isGitRepository(root)) candidate = nameFromRemote(root) || nameFromGitCommonDir(root);
  if (!candidate) candidate = nameFromPackageJson(root);
  if (!candidate) candidate = basename(root);
  return slugify(candidate);
}
