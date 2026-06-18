# Intégration HF Inference API — Chatbot recruteur

## 1. Résumé

La fonction `_call_hf_inference` a été ajoutée dans `backend/app/api/chat.py`. Elle appelle l'endpoint OpenAI-compatible de Hugging Face Inference API avec le token lu depuis `HF_TOKEN_CHATBOT`. Elle s'insère dans la chaîne de priorité existante entre Anthropic et le LLM local, et retombe silencieusement sur le fallback template en cas d'échec.

## 2. Diagnostic — compatibilité OpenAI

**OUI, le code était déjà partiellement compatible.**  
La fonction `_call_local_llm` utilisait déjà le format OpenAI (`POST /v1/chat/completions`, `messages=[{role, content}]`, lecture de `choices[0].message.content`). Ce qui manquait uniquement : le header `Authorization: Bearer <token>` et la gestion robuste des codes HTTP 429/503.

## 3. Fichiers modifiés

| Fichier | Modification |
|---|---|
| `backend/app/api/chat.py` | Ajout de `import time` et `from urllib.error import HTTPError` ; ajout de la constante `_HF_INFERENCE_URL` et de la fonction `_call_hf_inference` ; mise à jour des deux chaînes d'appel LLM (dans `chat()` et `ideal_profile()`) pour inclure HF Inference entre Anthropic et le LLM local. |

Aucun autre fichier n'a été créé ou modifié.

## 4. Modèle retenu

**`Qwen/Qwen2.5-7B-Instruct`**

Pourquoi : c'est un modèle confirmé disponible sur `router.huggingface.co` via l'endpoint OpenAI-compatible. Mistral-7B-Instruct-v0.3 n'est pas déployé sur l'Inference API HF (exclusion explicite dans le brief). Qwen2.5-7B-Instruct est servi nativement par le routeur HF et produit des réponses en français de bonne qualité.

C'est la **valeur par défaut**. Elle peut être surchargée via `CHATBOT_MODEL` (voir section 5).

## 5. Variables d'environnement

| Variable | Rôle | Valeur par défaut | À configurer |
|---|---|---|---|
| `HF_TOKEN_CHATBOT` | Token d'authentification Hugging Face | aucune | **déjà configurée par le proprio** — ne pas y toucher |
| `CHATBOT_MODEL` | Identifiant HF du modèle à utiliser | `Qwen/Qwen2.5-7B-Instruct` | Optionnel — surcharger si on veut un autre modèle |
| `ANTHROPIC_API_KEY` | Clé Anthropic (priorité 1) | aucune | Déjà gérée — non modifiée |
| `LOCAL_LLM_BASE_URL` | URL d'un LLM local Ollama/vLLM (priorité 3) | aucune | Déjà gérée — non modifiée |

**Aucune valeur de token ne figure dans ce document ni dans le code.**

## 6. Comportement attendu

### Si `HF_TOKEN_CHATBOT` est présent et le modèle répond

Le chatbot appelle `https://router.huggingface.co/v1/chat/completions`, reçoit une réponse du LLM, et la retourne à l'utilisateur. La réponse est en français (consigne dans le prompt système). Le temps de réponse est typiquement 2–8 secondes.

### Fallback automatique si le LLM est indisponible

Dans tous les cas suivants, le chatbot retombe **sans erreur** sur les templates déterministes :
- `HF_TOKEN_CHATBOT` absent → fallback immédiat
- Timeout réseau (>30 s) → fallback
- HTTP 429 quota dépassé → fallback immédiat
- HTTP 503 cold start → une seule retry après 15 s, puis fallback

Le fallback répond toujours de manière cohérente (explication de score, comparaison, exploration, etc.) à partir des données en base — le backend ne plante jamais.

### Chaîne de priorité complète

```
1. ANTHROPIC_API_KEY présent  →  Anthropic Claude (API propriétaire)
2. HF_TOKEN_CHATBOT présent   →  HF Inference API / Qwen2.5-7B  ← NOUVEAU
3. LOCAL_LLM_BASE_URL présent →  LLM local (Ollama, vLLM…)
4. (aucun)                    →  Templates déterministes (fallback)
```

## 7. Comment tester

### Depuis le front / Swagger

Envoyer une requête `POST /api/chat` :

```json
{
  "message": "Pourquoi ce candidat a un score aussi bas ?",
  "context": {},
  "session_id": "test-session-1"
}
```

### Ce qu'on doit observer

- Si HF fonctionne : `response` contient une phrase naturelle générée par le LLM (pas un template à base de tirets)
- Si HF est absent/en erreur : `response` contient un texte template structuré (commence par le nom du candidat, score, compétences manquantes)
- Dans les deux cas : HTTP 200, jamais d'erreur 500

### Test de l'endpoint ideal-profile

```json
POST /api/chat/ideal-profile
{
  "job_title": "Data Engineer",
  "job_description": "Nous cherchons un Data Engineer avec Python, SQL et Spark.",
  "required_skills": ["Python", "SQL", "Spark"]
}
```

Avec HF actif, la réponse sera un JSON structuré généré par le LLM. Sans HF, le fallback local produit un profil basé sur l'analyse de mots-clés.
