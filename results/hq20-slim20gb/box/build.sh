#!/bin/bash
set -e
PY312=/home/jamie/.local/share/uv/python/cpython-3.12-linux-x86_64-gnu/bin/python3.12
VENV=/home/jamie/venv-slim20
export CUDA_HOME=/opt/cuda
export PIP_NO_CACHE_DIR=1
echo "== stage venv $(date -u +%FT%TZ)"
"$PY312" -m venv "$VENV"
"$VENV/bin/pip" install --upgrade pip
echo "== stage pins"
"$VENV/bin/pip" install -r /home/jamie/qwen-serving/docker/requirements.txt
"$VENV/bin/python" - <<'PY'
import sys, torch, vllm, triton, transformers, tokenizers, compressed_tensors
print("VERSIONS python", sys.version.split()[0])
print("VERSIONS torch", torch.__version__)
print("VERSIONS vllm", vllm.__version__)
print("VERSIONS triton", triton.__version__)
print("VERSIONS transformers", transformers.__version__)
print("VERSIONS tokenizers", tokenizers.__version__)
print("VERSIONS compressed_tensors", compressed_tensors.__version__)
PY
SP=$("$VENV/bin/python" -c 'import vllm, os; print(os.path.dirname(vllm.__file__))' | tail -n1)
echo "SP=$SP"
echo "== stage patches"
cd /home/jamie/qwen-serving
sed -e 's/#.*//' -e 's/^[[:space:]]*//;s/[[:space:]]*$//' -e '/^$/d' /home/jamie/qwen-serving/patches/series | while IFS= read -r name; do
  case "$name" in
    dflash2-backport.patch) echo "== skip $name (retired)"; continue ;;
  esac
  echo "== $name"
  patch -p1 --fuzz 0 --no-backup-if-mismatch -d "$SP" < "/home/jamie/qwen-serving/patches/$name"
done
echo "== stage kvarn"
PY="$VENV/bin/python" /home/jamie/qwen-serving/kvarn/install.sh
echo "== stage verify"
PY="$VENV/bin/python" /home/jamie/qwen-serving/verify.sh --install
echo "== stage compile"
"$VENV/bin/python" -m compileall -q "$SP" && echo "compileall OK"
FLASHINFER_DISABLE_VERSION_CHECK=1 "$VENV/bin/python" -c "from vllm.utils.flashinfer import has_flashinfer; assert has_flashinfer(); print('flashinfer usable by vLLM')"
echo "== stage binary"
test -x "$VENV/bin/vllm"
"$VENV/bin/vllm" --version
"$VENV/bin/python" -c "import torch; print('cuda_available', torch.cuda.is_available())"
echo "BUILD_OK"
