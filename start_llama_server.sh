#!/bin/bash
# Script para iniciar llama-server con el modelo Llama-3.2-3B-Instruct-GGUF:Q4_K_M
# Uso: ./start_llama_server.sh

llama-server \
  -hf bartowski/Llama-3.2-3B-Instruct-GGUF:Q4_K_M \
  -c 4096 \
  --port 8080 \
  --host 0.0.0.0 \
  --alias llama-3.2-3b \
  -t 4 \
  --mmap
