# Vercel deploy (food-nutrition)

## Ready checklist

- [x] `vercel.json` — Vite output `dist`, SPA rewrites, API includes `data/food.db` + sql.js wasm
- [x] `/api/*` serverless handlers — health / foods / foods/:id / stats
- [x] Rate limit 5/min with exact Chinese 429 message
- [x] UI modes unchanged (client-side)
- [ ] GitHub remote + auth (required for Vercel Git integration)

## Architecture change

Local keeps Express + `better-sqlite3`.  
Vercel cannot rely on native sqlite bindings, so production API uses **sql.js** (WASM) over the same `data/food.db`.

## User must provide (blocker)

This Cloud Agent environment has:

- no `GH_TOKEN`
- `gh` not logged in
- no git `origin` remote

Provide one of:

1. **GitHub repo URL** already created (e.g. `https://github.com/<you>/food-nutrition`) + permission for the agent to push, or  
2. Run locally:

```bash
cd food-nutrition
gh auth login
gh repo create food-nutrition --public --source=. --remote=origin --push
# then Import on vercel.com
```

## After GitHub is connected

1. Import repo on Vercel  
2. Deploy (no env vars required for v1)  
3. Smoke: `/api/health`, search, open detail, hit 429 on 6th request  
