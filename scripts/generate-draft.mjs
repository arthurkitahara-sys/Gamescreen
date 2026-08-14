import { execSync } from "node:child_process";
import { writeFileSync } from "node:fs";

const { GEMINI_API_KEY, BEFORE_SHA, AFTER_SHA, REPO_NAME } = process.env;

if (!GEMINI_API_KEY) {
  console.error("Faltou GEMINI_API_KEY nos secrets do repositório.");
  process.exit(1);
}

// SHA "zero" acontece no primeiro push de uma branch nova - usamos o commit
// mais antigo disponível nesse caso.
const ZERO_SHA = "0000000000000000000000000000000000000000";
const rangeStart =
  !BEFORE_SHA || BEFORE_SHA === ZERO_SHA
    ? execSync(`git rev-list --max-parents=0 HEAD`).toString().trim()
    : BEFORE_SHA;

function safeExec(cmd) {
  try {
    return execSync(cmd, { maxBuffer: 1024 * 1024 * 10 }).toString();
  } catch (e) {
    return "";
  }
}

// Mensagens dos commits desse push
const commitLog = safeExec(
  `git log ${rangeStart}..${AFTER_SHA} --pretty=format:"- %s (%h)"`
);

// Resumo dos arquivos alterados (evita mandar o diff inteiro, que pode ser gigante)
const diffStat = safeExec(`git diff ${rangeStart} ${AFTER_SHA} --stat`);

// Diff real, mas truncado para não estourar o contexto nem vazar coisa demais
let diffFull = safeExec(`git diff ${rangeStart} ${AFTER_SHA}`);
const MAX_DIFF_CHARS = 12000;
if (diffFull.length > MAX_DIFF_CHARS) {
  diffFull = diffFull.slice(0, MAX_DIFF_CHARS) + "\n...(diff truncado)...";
}

const prompt = `Você vai escrever um post para o meu LinkedIn pessoal contando o que eu acabei de implementar no projeto "${REPO_NAME}".

Commits deste push:
${commitLog || "(sem mensagens de commit disponíveis)"}

Arquivos alterados:
${diffStat || "(não disponível)"}

Diff (pode estar truncado):
${diffFull || "(não disponível)"}

Regras para o post:
- Tom: pessoal, direto, sem jargão corporativo vazio, sem emojis em excesso (no máximo 2).
- Foque no PORQUÊ e no IMPACTO da mudança, não numa lista técnica de commits.
- Não invente funcionalidades que não estão nos dados acima.
- Não inclua nomes de arquivos, variáveis ou trechos de código.
- Não inclua hashtags forçadas; no máximo 2-3 relevantes no final, se fizer sentido.
- Tamanho ideal: 3 a 6 frases curtas.
- Responda APENAS com o texto final do post, sem aspas, sem comentários extras.`;

const GEMINI_MODEL = "gemini-3.5-flash-lite"; // modelo atual do tier gratuito

const res = await fetch(
  `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent`,
  {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-goog-api-key": GEMINI_API_KEY,
    },
    body: JSON.stringify({
      contents: [
        {
          role: "user",
          parts: [{ text: prompt }],
        },
      ],
      generationConfig: {
        maxOutputTokens: 500,
      },
    }),
  }
);

if (!res.ok) {
  const errText = await res.text();
  console.error("Erro chamando a API do Gemini:", res.status, errText);
  process.exit(1);
}

const data = await res.json();
const postText = (data.candidates?.[0]?.content?.parts ?? [])
  .map((p) => p.text ?? "")
  .join("\n")
  .trim();

if (!postText) {
  console.error("A resposta do Gemini veio vazia:", JSON.stringify(data));
  process.exit(1);
}

const draftMarkdown = `## 📝 Rascunho gerado para o LinkedIn

> Revise abaixo. Se estiver bom, aprove o job "publish" para postar.
> Se não estiver, edite o arquivo \`draft.md\` do artifact e rode o job "publish" manualmente, ou simplesmente rejeite.

---

${postText}

---
`;

writeFileSync("draft.md", draftMarkdown, "utf-8");
// Guardamos só o texto puro também, para o script de publicação usar direto
writeFileSync("draft.txt", postText, "utf-8");

console.log("Rascunho gerado com sucesso.");
