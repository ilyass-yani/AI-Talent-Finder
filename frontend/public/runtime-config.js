// This file is written at build-time as a safe fallback. The docker
// entrypoint will overwrite it at container start when runtime env is set.
// In production (Vercel), NEXT_PUBLIC_API_URL takes precedence over this file.
window.__NEXT_PUBLIC_API_URL = "https://RHmaster-ai-talent-finder-backend.hf.space";
