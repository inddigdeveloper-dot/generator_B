#!/bin/bash
# VPS Setup Script — Install Ollama and serve the fine-tuned review model
# Run this on your Ubuntu/Debian VPS as root or with sudo
# Tested on: Ubuntu 22.04 LTS, 8GB RAM, 4 vCPU

set -e

echo "=== 1. Installing Ollama ==="
curl -fsSL https://ollama.com/install.sh | sh

echo "=== 2. Starting Ollama as a system service ==="
systemctl enable ollama
systemctl start ollama
sleep 3

echo "=== 3. Pulling base model (Llama 3.2 3B — ~2GB) ==="
ollama pull llama3.2:3b

echo "=== 4. Configure Ollama to listen on all interfaces ==="
# By default Ollama only listens on localhost.
# Open it to local network (keep firewall rules in place).
mkdir -p /etc/systemd/system/ollama.service.d
cat > /etc/systemd/system/ollama.service.d/override.conf << 'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
EOF
systemctl daemon-reload
systemctl restart ollama

echo "=== 5. Firewall — allow only your app server to reach Ollama ==="
# Replace YOUR_APP_SERVER_IP with your backend server's IP
# ufw allow from YOUR_APP_SERVER_IP to any port 11434
# ufw deny 11434
echo "  [MANUAL] Run: ufw allow from <your-backend-ip> to any port 11434"

echo "=== 6. Testing base model ==="
curl -s http://localhost:11434/api/generate \
  -d '{"model":"llama3.2:3b","prompt":"Write a 5-star review for a coffee shop. 2 sentences, casual.","stream":false}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['response'])"

echo ""
echo "=== Base setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Set in your .env:"
echo "       LLM_PROVIDER=ollama"
echo "       OLLAMA_BASE_URL=http://<this-vps-ip>:11434"
echo "       OLLAMA_MODEL=llama3.2:3b"
echo ""
echo "  2. After fine-tuning, deploy custom model:"
echo "       scp review-model/review-gen-q4.gguf  vps:/models/"
echo "       scp review-model/Modelfile             vps:/models/"
echo "       ssh vps 'ollama create review-gen -f /models/Modelfile'"
echo "       # Then update .env: OLLAMA_MODEL=review-gen"
echo ""
echo "  3. Monitor Ollama:"
echo "       journalctl -u ollama -f"
echo "       ollama ps   # see running models"
