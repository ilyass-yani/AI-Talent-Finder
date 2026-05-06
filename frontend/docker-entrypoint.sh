#!/bin/sh
set -e

# Create runtime config for client
if [ -n "$NEXT_PUBLIC_API_URL" ]; then
  cat > /app/public/runtime-config.js <<EOF
window.__NEXT_PUBLIC_API_URL = "${NEXT_PUBLIC_API_URL}";
EOF
else
  cat > /app/public/runtime-config.js <<'EOF'
window.__NEXT_PUBLIC_API_URL = undefined;
EOF
fi

exec npm start -- -H 0.0.0.0 -p ${PORT:-3000}
