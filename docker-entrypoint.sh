#!/bin/sh
set -e

# Create a runtime config file that sets a global variable accessible to client code
# This allows the frontend to pick up the backend API URL at container runtime
if [ -n "$NEXT_PUBLIC_API_URL" ]; then
  cat > /app/public/runtime-config.js <<EOF
window.__NEXT_PUBLIC_API_URL = "${NEXT_PUBLIC_API_URL}";
EOF
else
  cat > /app/public/runtime-config.js <<'EOF'
window.__NEXT_PUBLIC_API_URL = undefined;
EOF
fi

exec npx next start -H 0.0.0.0 -p 8080
