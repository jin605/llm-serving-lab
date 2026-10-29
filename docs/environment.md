# 실행 환경

환경이 바뀌면 날짜와 변경 내용을 기록한다. 아래 항목은 실험 실행 시 다시 확인한다.

## 로컬

- 확인일: 2026-10-13 (최초 2026-10-06)
- 장비: MacBook Pro
- 칩: Apple M5 Pro
- 메모리: 48 GB (통합 메모리), Ollama 인식 GPU 메모리 37.4 GiB
- OS 버전: macOS 26.6.2
- Python 버전: 3.14.5
- 런타임 / 버전: Ollama 서버 0.33.2 (`/Applications/Ollama.app/Contents/Resources/ollama`)
  - PATH의 `ollama`는 Homebrew 0.23.3(`/opt/homebrew/bin/ollama`)이므로 서버 실행에 쓰지 않는다.
- 서버 실행: Ollama 앱을 종료하고 터미널에서 직접 실행한다.
  - `OLLAMA_CONTEXT_LENGTH=4096 OLLAMA_NUM_PARALLEL=N /Applications/Ollama.app/Contents/Resources/ollama serve`
  - 요청이 5분 없으면 모델이 내려간다(`OLLAMA_KEEP_ALIVE` 기본 5m). 측정 전 워밍업 요청을 보낸다.
- 모델: `llama3.1:8b`
- 로컬 표시 ID: `46e0c10c039e`
- 전체 digest: `46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e`
- tokenizer revision: 미기록
- 로딩 상태: `100% GPU`, 9.2 GB (context 32768) / 5.3 GB (context 4096, parallel 1)
- 양자화: Q4_K_M (GGUF)

## GPU 서버

### 2026-10-29 RunPod (04-vllm)

- 제공 업체 / 인스턴스: RunPod Pod, Secure Cloud, US-WA-1
- GPU 종류 / 개수 / VRAM: NVIDIA RTX 6000 Ada Generation × 1, 49,140 MiB
- GPU 사양 (nvidia-smi): 최대 SM 클럭 3,105 MHz, 최대 메모리 클럭 10,001 MHz, 전력 한도 300 W. 부하 중 메모리 클럭은 9,501 MHz였다.
- 메모리 대역폭: 사양 약 960 GB/s (384-bit). 부하 중 메모리 클럭 기준 약 912 GB/s.
- CPU / RAM: AMD EPYC 75F3 16 vCPU / 62 GB
- OS / 드라이버 / CUDA: Ubuntu 24.04 / 595.91.07 / 13.2
- 컨테이너 이미지: `runpod/pytorch:1.5.0-cu1281-torch280-ubuntu2404`, Container disk 50 GB, 볼륨 없음
- Python: 3.12.3, `uv venv`로 만든 가상환경 (시스템 pip는 Debian 패키지 충돌로 설치 실패)
- 런타임 버전: vLLM 0.32.0, PyTorch 2.13.0 (vLLM 설치 시 함께 설치)
- 모델 ID: `meta-llama/Llama-3.1-8B-Instruct` (Hugging Face gated, revision 미기록)
- dtype / 양자화 / 최대 context 길이: bf16(기본값), 양자화 없음, `--max-model-len 4096`
- 서버 실행 명령: `vllm serve meta-llama/Llama-3.1-8B-Instruct --max-model-len 4096 --gpu-memory-utilization 0.90 --port 8000` (동시 처리 수 실험에서는 `--max-num-seqs N` 추가)
- 메모리 배분 (서버 로그): 모델 15.0 GiB, 활성값 최대 1.43 GiB, CUDA graph 0.24 GiB, KV cache 25.95 GiB = 212,576 tokens (토큰당 128 KiB)
- 대여 비용 / 실행 시간: $1.00/hr (GPU $0.99 + 디스크 $0.007), 약 48분, 약 $0.80
- 측정 위치: 측정 스크립트를 같은 Pod 안에서 실행했다 (`localhost:8000`). 네트워크 지연이 섞이지 않는다.

## 측정 조건

- 부하 생성기 실행 위치와 서버까지의 네트워크 경로:
- 측정 위치 및 TTFT / TPOT 계산 방법:
- 입력 / 출력 토큰 수와 생성 설정:
- 동시 요청 수 또는 요청 도착률:
- 워밍업 / Cache 초기 상태:
- 측정 요청 수 / 반복 횟수:
- 오류와 실패 요청 처리 방법:
