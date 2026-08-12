import { readFileSync } from "node:fs";

const { LINKEDIN_ACCESS_TOKEN, LINKEDIN_PERSON_URN } = process.env;

if (!LINKEDIN_ACCESS_TOKEN || !LINKEDIN_PERSON_URN) {
  console.error(
    "Faltou LINKEDIN_ACCESS_TOKEN e/ou LINKEDIN_PERSON_URN nos secrets do repositório."
  );
  process.exit(1);
}

const postText = readFileSync("draft.txt", "utf-8").trim();

if (!postText) {
  console.error("draft.txt está vazio, nada para publicar.");
  process.exit(1);
}

const body = {
  author: LINKEDIN_PERSON_URN, // formato: urn:li:person:XXXXXXXX
  commentary: postText,
  visibility: "PUBLIC",
  distribution: {
    feedDistribution: "MAIN_FEED",
    targetEntities: [],
    thirdPartyDistributionChannels: [],
  },
  lifecycleState: "PUBLISHED",
  isReshareDisabledByAuthor: false,
};

const res = await fetch("https://api.linkedin.com/rest/posts", {
  method: "POST",
  headers: {
    Authorization: `Bearer ${LINKEDIN_ACCESS_TOKEN}`,
    "Content-Type": "application/json",
    "X-Restli-Protocol-Version": "2.0.0",
    "LinkedIn-Version": "202506", // ajuste para a versão mais recente se necessário
  },
  body: JSON.stringify(body),
});

if (!res.ok) {
  const errText = await res.text();
  console.error("Erro publicando no LinkedIn:", res.status, errText);
  process.exit(1);
}

console.log("Post publicado com sucesso no LinkedIn!");
console.log("Texto publicado:\n", postText);
