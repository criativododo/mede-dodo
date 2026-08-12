import { existsSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

function writeIfAbsent(filePath, content) {
  if (!existsSync(filePath)) writeFileSync(filePath, content, 'utf8');
}

/**
 * Bootstrap do repositório de memória (hub compartilhado por qualquer projeto que use este
 * kit). Não escreve nada específico de um projeto: cada `projectId` ganha sua própria pasta
 * sob `projects/<projectId>/` de forma preguiçosa, na primeira vez que uma sessão daquele
 * projeto roda `/fim` (ver `documents.mjs`). O bootstrap só garante que o repositório tenha
 * um README e um primeiro commit para que `/inicio` tenha uma branch remota para ler.
 */
export function createInitialMemory(memoryPath) {
  writeIfAbsent(join(memoryPath, 'README.md'), `# Memória operacional multi-projeto\n\nRepositório privado de continuidade de contexto entre sessões, compartilhado por qualquer repositório de aplicação que use o kit \`.claude/session-memory/\`. Não contém código de aplicação, credenciais nem artefatos de deploy.\n\nCada projeto vive isolado em \`projects/<projectId>/\` (identificador inferido automaticamente do repositório ativo — ver \`lib/project.mjs\`):\n\n- \`executive-summary.md\` — estado atual, gerado a partir dos journals ativos. Não editar manualmente.\n- \`journals/\` — uma sessão por arquivo, janela recente carregada por \`/inicio\`.\n- \`archive/YYYY-MM.md\` — journals consolidados quando a janela ativa excede o limite (ver \`/fim\`).\n\nUse os comandos versionados no repositório da aplicação: \`/inicio\`, \`/fim\`, \`/status\`, \`/journal\` e \`/validate\`.\n`);
}
