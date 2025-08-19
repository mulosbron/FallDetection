# SmolVLM2 Fall Detection AI Service

This project runs fall detection on images using the SmolVLM2 model, optimized for an RTX 4070 in WSL2 (Ubuntu).

## 🚀 What it does

- Uses `HuggingFaceTB/SmolVLM2-2.2B-Instruct` for vision-language inference
- Deterministic Yes/No output per image
- Robust logic:
  - Multi-crop voting (center and zoom crops)
  - Two-step questioning per crop:
    1) "Is there a person visible?" (Yes/No)
    2) If Yes → "Is a person lying on the ground/floor (fallen)?" (Yes/No)
  - Final decision by majority vote across crops
- Detailed logging with timestamps and per-test results

## 📋 System Requirements

- GPU: NVIDIA RTX 4070 (or similar) with CUDA 12.1 support
- RAM: 16 GB minimum
- Disk: 10 GB free
- OS: Windows 10/11 with WSL2 (Ubuntu)
- Python: 3.12 (recommended)

## 🛠️ Setup (Windows + WSL2)

### 1) Install WSL2 (once)
```powershell
# Run in Windows PowerShell (Admin)
wsl --install
# Reboot when prompted
```

### 2) Update Ubuntu
```bash
# Inside WSL (Ubuntu)
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git
```

### 3) Go to the project folder (WSL path)
```bash
cd /mnt/c/Users/duggy/OneDrive/Belgeler/Github/FallDetection/ai-service
```

### 4) Create and activate a virtual environment
```bash
python3 -m venv smolvlm2_env
source smolvlm2_env/bin/activate
```

### 5) Install PyTorch (CUDA 12.1 wheels)
```bash
pip install torch==2.5.1+cu121 torchvision==0.20.1+cu121 torchaudio==2.5.1+cu121 \
  --index-url https://download.pytorch.org/whl/cu121
```

### 6) Install the rest of the dependencies
```bash
pip install -r requirements.txt
```

## 📦 requirements.txt

```txt
# Transformers with SmolVLM2 support (required)
git+https://github.com/huggingface/transformers@v4.49.0-SmolVLM-2

# PyTorch CUDA 12.1 (install via the index-url above)
torch==2.5.1+cu121
torchvision==0.20.1+cu121
torchaudio==2.5.1+cu121
--index-url https://download.pytorch.org/whl/cu121

# Image processing
Pillow==11.0.0
numpy==2.1.2

# HTTP and utilities
requests==2.32.5
tqdm==4.67.1

# Logging / monitoring
psutil==7.0.0

# Required extra
num2words==0.5.14

# Hugging Face stack
huggingface-hub==0.34.4
tokenizers==0.21.4
safetensors==0.6.2
```

## ✅ Deterministic Yes/No logic (how it works)

- Prompts are asked through the processor chat template with a PIL image.
- Generation is deterministic: `do_sample=False`, `temperature=0.0`, `max_new_tokens=2` → short, stable Yes/No.
- Only newly generated tokens are decoded (no prompt leakage).
- Precision fix: only `pixel_values` are cast to `float16`; text tensors remain default to avoid weight/input dtype mismatch.

## ▶️ Usage

1) Activate your env each session:
```bash
source smolvlm2_env/bin/activate
```
2) Put test images into `test-images/` (supports: jpg, jpeg, png, webp, bmp, tiff)
3) Run:
```bash
python3 analyze_image.py
```

You will see per-image logs and final decision:
- Person on ground → `Yes`
- No person / person not fallen → `No`

Logs are saved under `logs/smolvlm2_test_YYYYMMDD_HHMMSS.log`.

## 🧠 What changed vs a naive prompt

- Naive single-question prompting often yields unstable or wrong results.
- This implementation adds:
  - Multi-crop image evidence (center + tighter crops)
  - Two-step questions (presence → fallen)
  - Majority voting
- Together, these significantly improve robustness and reduce false positives/negatives.

## 🧪 Example ground-truth convention

- Files named like `fall_1_x.jpg|png|webp` represent images with a fallen person → expected `Yes`.
- Files named like `fall_0_x.jpg|png|webp` represent non-fall images → expected `No`.

You can expand your dataset using this convention to quickly sanity-check accuracy.

## 🔧 Troubleshooting

- CUDA not available
  - Check driver, WSL GPU support, and run:
    ```bash
    python3 -c "import torch; print(torch.cuda.is_available())"
    ```

- Dtype mismatch like: `Input type (CUDABFloat16Type) and weight type (torch.cuda.HalfTensor) should be the same`
  - Ensure only `pixel_values` are cast to `float16` (code already does this)
  - Keep model weights in `float16` (default from checkpoint)

- Long first run
  - First model load downloads weights; subsequent runs are fast

- No `pip` in WSL
  - `sudo apt install -y python3-pip python3-venv`

- Missing Hugging Face auth for private models
  - `export HUGGING_FACE_HUB_TOKEN=your_token_here`

## 📁 Project Structure

```
ai-service/
├── analyze_image.py      # Main script (multi-crop + two-step + voting)
├── requirements.txt      # Pinned dependencies
├── README.md             # This file
├── logs/                 # Run logs
└── test-images/          # Input images
```

## ⚙️ Performance notes

- Model VRAM footprint: ~4.2 GB (RTX 4070)
- First run: model download (a few minutes)
- Subsequent runs: a few seconds per image (depending on size/crops)

## 🧭 Roadmap (optional)

- Dockerized microservice (FastAPI): `/infer` endpoint for images
- Batch endpoints and background queue
- CSV/JSON metrics export (accuracy, precision/recall against filename labels)
- Real-time video polling service (multi-process)

## 📄 License

MIT

## Environment used

- WSL2 Ubuntu + Python 3.12 + RTX 4070 + CUDA 12.1
