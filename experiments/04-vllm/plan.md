# 04-vllm 실행 계획

Mac + Ollama에서 한 실험을 NVIDIA GPU + vLLM에서 같은 도구로 반복한다. GPU는 켜져 있는 시간만큼 비용이 드므로, 이 문서의 명령을 위에서부터 복사해 실행하고 끝나면 바로 삭제한다.

목표 시간: 2~3시간 / 예상 비용: 약 $2~3

## 0. 빌리기 전 (Mac)

- [ ] Hugging Face에서 `meta-llama/Llama-3.1-8B-Instruct` 사용 승인 (완료: 2026-10-29)
- [ ] Read-Only 토큰 발급, 안전한 곳에 보관 (저장소·채팅에 붙이지 않는다)
- [ ] RunPod 계정 Settings에 SSH 공개 키 등록 (`cat ~/.ssh/id_ed25519.pub`, 없으면 `ssh-keygen -t ed25519`)
- [ ] 최신 커밋을 GitHub에 push (서버에서 `git clone`으로 받는다)
- [ ] 아래 예측을 읽고, 측정 전 내 예측을 적어 둔다

## 1. Pod 만들기 (RunPod)

- Cloud: Community Cloud
- GPU: RTX 6000 Ada (48 GB, $0.74/hr) 또는 L40S (48 GB, $0.79/hr). 없으면 같은 48 GB급을 고르고 아래 예측을 다시 계산한다.
- Template: RunPod PyTorch (CUDA 12.x)
- Container disk: 50 GB 이상 (모델 약 16 GB + vLLM 설치)
- Environment variable: `HF_TOKEN` = 발급한 토큰 (RunPod의 Secret 기능을 쓸 수 있으면 그것을 쓴다)
- SSH 접속 정보(IP, 포트)를 확인한다.

## 2. 서버 준비 (Pod 안)

```bash
# 환경 기록용
nvidia-smi
nvidia-smi --query-gpu=name,memory.total,clocks.max.sm,power.limit --format=csv
python3 --version

# 측정 도구
cd /workspace
git clone https://github.com/jin605/llm-serving-lab.git
cd llm-serving-lab

# vLLM 설치 후 버전 기록
pip install vllm
python3 -c "import vllm; print(vllm.__version__)"
```

`nvidia-smi` 출력, vLLM 버전, Python 버전, 시간당 가격을 [환경 기록](../../docs/environment.md)의 GPU 서버 항목에 적는다.

## 3. vLLM 서버 실행

터미널을 두 개 연다(SSH 두 번 접속 또는 tmux). 터미널 1에서 서버를 띄운다.

```bash
vllm serve meta-llama/Llama-3.1-8B-Instruct \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.90 \
  --port 8000
```

- `--max-model-len 4096`: Mac 실험의 context 4096과 맞춘다.
- 처음 실행 시 모델(약 16 GB)을 내려받는다. 시작 로그에서 KV cache에 잡힌 메모리와 토큰 수(`GPU KV cache size`)를 기록한다. Mac에서 처리 칸과 RAM 보관함을 따로 봤던 것과 비교한다.
- 동시 처리 수를 제한하는 실험에서는 `--max-num-seqs N`을 추가해 다시 띄운다(Ollama의 `OLLAMA_NUM_PARALLEL`에 해당).

터미널 2에서 동작을 확인한다.

```bash
cd /workspace/llm-serving-lab
M=meta-llama/Llama-3.1-8B-Instruct
V="--api openai --base-url http://localhost:8000/v1 --model $M"
python3 benchmark/ttft.py "warmup" $V --num-predict 2 --out-dir /tmp/warmup
```

측정 스크립트는 서버와 같은 Pod 안에서 실행한다. Mac에서 인터넷을 거쳐 요청하면 네트워크 지연이 TTFT에 섞인다.

## 4. 측정 전 예측

### 모델 크기

- Mac: Q4_K_M 약 4.92 GB
- vLLM: FP16(bf16) 약 8.03B × 2 bytes ≈ 16.1 GB. 양자화가 달라 Mac과 직접 비교할 때는 이 차이를 함께 설명한다.

### TPOT (메모리 대역폭 모델)

`TPOT ≈ 모델 크기 ÷ (메모리 대역폭 × 사용률)`. Mac에서 사용률은 약 90%였다. 대역폭은 일반적으로 알려진 사양이며 빌린 GPU의 실제 사양을 확인한다.

| 장비 | 대역폭 | 모델 | 이론 최대 | 예측 TPOT (90%) |
| --- | ---: | ---: | ---: | ---: |
| Mac M5 Pro (실측) | 307 GB/s | 4.92 GB | 62 tok/s | 17.8 ms (실측) |
| RTX 6000 Ada | 약 960 GB/s | 16.1 GB | 약 60 tok/s | 약 18.6 ms |
| L40S | 약 864 GB/s | 16.1 GB | 약 54 tok/s | 약 20.7 ms |
| H100 SXM (참고) | 약 3,350 GB/s | 16.1 GB | 약 208 tok/s | 약 5.3 ms |

예측대로라면 GPU가 대역폭은 약 3배지만 FP16 모델이 약 3배 커서, 요청 하나의 TPOT은 Mac의 4비트 모델과 비슷하다. 맞는지 확인하는 것이 첫 실험이다.

### TTFT (prefill)

- prefill은 연산이 병목이다. 8B 모델은 토큰당 약 16 GFLOP이다.
- Mac은 약 1,030 tok/s(약 16.5 TFLOPS)였다. 48 GB급 데이터센터 GPU의 FP16 tensor 성능은 Mac보다 10배 안팎 높다고 알려져 있으나 정확한 값은 빌린 GPU 사양으로 확인한다.
- 대략 예측: 입력 2000 tokens의 TTFT가 Mac 약 2초에서 0.2~0.5초 수준으로 줄어든다. 사양 확인 후 다시 계산한다.

### 동시 사용자

- Mac에서는 요청 하나를 더할 때마다 한 단계가 약 5~7 ms 늘었다(이상 대비 8개 29%). 연산량으로는 GPU 한계가 아니었고 llama.cpp 묶음 decode 효율을 의심했다.
- 예측: vLLM에서는 8명이 동시에 와도 한 단계 시간이 요청 하나일 때보다 조금만 늘고(예: 20~25 ms), 8명 모두 TTFT 1초·TPOT 50 ms 목표를 지킨다. 목표를 지키는 최대 동시 사용자는 수십 명 수준으로 예상한다.

## 5. 실험 (터미널 2, 저장소 루트에서)

모든 명령은 위의 `M`, `V` 변수를 쓴다. 결과는 `experiments/04-vllm/results/` 아래에 저장한다.

### 실험 1: 단일 요청 TTFT·TPOT

```bash
for rep in 1 2 3; do
  python3 benchmark/ttft.py "[run $(date +%s%N)] Count from 1 to 2000, separated by commas. Do not stop early." $V --num-predict 64 --out-dir experiments/04-vllm/results/single
done
```

### 실험 2: 입력 길이 (03-ttft 실험 2와 같음)

```bash
for n in 1 10 50 100 200; do
  for rep in 1 2 3; do
    text=$(python3 -c "import sys, time; n=int(sys.argv[1]); print(f'[run {n}-{time.time_ns()}] ' + 'The quick brown fox jumps over the lazy dog. ' * n + 'Summarize the text above.')" "$n")
    python3 benchmark/ttft.py "$text" $V --out-dir experiments/04-vllm/results/input-length
  done
done
```

### 실험 3: 출력 길이 (03-ttft 실험 3과 같음)

```bash
for n in 16 64 256 1024; do
  for rep in 1 2 3; do
    python3 benchmark/ttft.py "[run $(date +%s%N)] Count from 1 to 2000, separated by commas. Do not stop early." $V --num-predict "$n" --out-dir experiments/04-vllm/results/output-length
  done
done
```

1024 tokens 실행 중에는 터미널 3에서 GPU 클럭·전력·온도를 기록한다.

```bash
nvidia-smi --query-gpu=timestamp,clocks.sm,power.draw,temperature.gpu,utilization.gpu --format=csv -l 1 | tee experiments/04-vllm/results/output-length-gpu.csv
```

### 실험 4: 동시 사용자 (01-concurrency 실험 3과 같음)

(a) 동시 처리 수 제한별 8명: 서버를 `--max-num-seqs P`(P = 1, 2, 4, 8)로 다시 띄우고 워밍업 후 실행한다.

```bash
P=1
N=8
stamp=$(date +%Y%m%d-%H%M%S)
out="experiments/04-vllm/results/concurrency-seqs${P}-${N}req-${stamp}"
for i in $(seq 1 $N); do
  python3 benchmark/ttft.py "[req ${i}-${stamp}] Count from 1 to 2000, separated by commas. Do not stop early." $V --out-dir "$out" &
done
wait
```

(b) 기본 설정(`--max-num-seqs` 없음)에서 사용자 수를 늘린다. 위 명령에서 `P=default`로 두고 N = 8, 16, 32, 64로 바꿔 실행한다. 사용자가 늘 때 TPOT이 어디서 50 ms를 넘는지 본다.

### 실험 5: Prefix cache (02-prefix-cache 실험 1·2와 같음)

vLLM은 prefix caching이 기본으로 켜져 있다. 실행 로그로 확인한다.

```bash
for pos in none 0 25 50 75 100; do
  for rep in 1 2 3; do
    id=$(python3 -c "import time; print(time.time_ns())")
    out="experiments/04-vllm/results/prefix-change${pos}-rep${rep}"
    change=(); [ "$pos" != none ] && change=(--change-at "$pos")
    a=$(python3 workloads/prefix_variants.py --doc-id "$id" --question "How many times does the word fox appear?")
    b=$(python3 workloads/prefix_variants.py --doc-id "$id" "${change[@]}" --question "What animal is lazy?")
    python3 benchmark/ttft.py "$a" $V --num-predict 16 --out-dir "$out"
    python3 benchmark/ttft.py "$b" $V --num-predict 16 --out-dir "$out"
  done
done
```

- Pod의 기본 셸이 bash라면 배열 문법은 그대로 동작한다.
- 대조군: 시간이 남으면 서버를 `--no-enable-prefix-caching`으로 다시 띄워 `none` 조건만 반복한다. B가 A와 같아지면 cache 효과가 확인된다.

## 6. 끝내기

- [ ] 결과를 Mac으로 가져온다 (Mac에서 실행):
  ```bash
  scp -P <포트> -r root@<IP>:/workspace/llm-serving-lab/experiments/04-vllm/results experiments/04-vllm/
  ```
- [ ] 가져온 파일 수를 확인한다.
- [ ] 서버 로그의 KV cache 크기, vLLM 버전, GPU 사양을 환경 기록에 적었는지 확인한다.
- [ ] **Pod를 Terminate(삭제)한다.** Stop만 하면 저장 공간 요금이 계속 나갈 수 있다.
- [ ] RunPod 결제 화면에서 사용 시간과 금액을 확인해 환경 기록에 적는다.
