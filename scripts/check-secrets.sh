#!/bin/bash
# Block API keys from being committed

for file in "$@"; do
    if grep -E "gsk_[a-zA-Z0-9]{45,}|sk-proj-[a-zA-Z0-9_-]{90,}|-----BEGIN.*PRIVATE KEY-----" "$file" >/dev/null 2>&1; then
        echo "❌ ERROR: Secret detected in $file"
        echo "   Found patterns matching:"
        echo "   - Groq API keys (gsk_*)"
        echo "   - OpenAI API keys (sk-proj-*)"
        echo "   - Private keys (PEM format)"
        exit 1
    fi
done

exit 0
