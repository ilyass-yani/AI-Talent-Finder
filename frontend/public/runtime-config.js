// This file is written at build-time as a safe fallback. The docker
// entrypoint will overwrite it at container start when runtime env is set.
window.__NEXT_PUBLIC_API_URL = "/api";
