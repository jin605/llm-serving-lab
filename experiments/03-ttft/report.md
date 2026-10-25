# 03-ttft

## 목적

사용자가 체감하는 두 지연, TTFT(첫 토큰까지 시간)와 TPOT(이후 토큰 간격)을 측정한다. 이번 실험에서는 입력 길이에 따라 두 값이 어떻게 변하는지 확인한다.

## 측정 방법

- 도구: [`benchmark/ttft.py`](../../benchmark/ttft.py)
- stream: true로 요청하고 Python 클라이언트에서 시간을 잰다.
  - TTFT: 요청 직전부터 `response`가 비어 있지 않은 첫 줄 도착까지
  - TPOT: (전체 시간 − TTFT) ÷ (`eval_count` − 1)
- 서버 통계의 `load_duration`이 0.1초를 넘으면 cold로 기록한다.
- 실행마다 `results/<시각>.json` 하나를 저장한다. 직접 잰 값과 서버 통계를 함께 담는다. 2026-10-25 이후 파일 이름에는 마이크로초가 붙는다.

curl의 `time_starttransfer`는 Ollama에서는 첫 토큰과 비슷하지만(약 20 ms), 응답 헤더를 첫 토큰보다 먼저 보내는 서버에서는 TTFT가 아니다. 서버가 바뀌어도 같은 기준으로 재기 위해 Python으로 첫 토큰을 직접 확인한다.

## 공통 조건

- 모델: `llama3.1:8b` (Q4_K_M)
- Ollama 서버 0.33.2, `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_CONTEXT_LENGTH=4096`
- 모델 warm 상태
- options: temperature 0, seed 42, num_predict 64

## 실험 1: 짧은 한글 질문 (2026-10-25)

직전 요청과 다른 질문이라 prompt cache가 없는 상태다.

| 질문 | 입력 토큰 | TTFT | TPOT |
| --- | ---: | ---: | ---: |
| 서울에 대해 자세히 설명해줘 | 19 | 120.5 ms | 18.3 ms |
| 부산에 대해 자세히 설명해줘 | 20 | 117.0 ms | 18.4 ms |
| 사과가 뭐야? | 16 | 113.1 ms | 18.3 ms |

결과: `results/20261025-1704*.json`, `results/20261025-170533.json`

같은 질문을 반복하면 TTFT가 약 37 ms로 줄었다. 원인은 [Prefix Cache 사전 관찰](../02-prefix-cache/report.md)에 기록했다.

## 실험 2: 입력 길이에 따른 TTFT (2026-10-25)

### 조건

- 입력: `The quick brown fox jumps over the lazy dog.`(10 tokens)을 n번 반복하고 `Summarize the text above.`를 붙였다.
- n = 1, 10, 50, 100, 200, 길이마다 3회
- prompt cache를 피하려고 입력 맨 앞에 매번 다른 번호(`[run n-<time_ns>]`)를 붙였다. Prefix cache는 앞부분이 일치하는 만큼만 재사용하므로 번호는 맨 앞에 있어야 한다.
- 실제 입력 토큰 수는 서버의 `prompt_eval_count`로 확인했다. context 4096을 넘지 않는다.

실행 명령:

```bash
for n in 1 10 50 100 200; do
  for rep in 1 2 3; do
    text=$(python3 -c "import sys, time; n=int(sys.argv[1]); print(f'[run {n}-{time.time_ns()}] ' + 'The quick brown fox jumps over the lazy dog. ' * n + 'Summarize the text above.')" "$n")
    python3 benchmark/ttft.py "$text"
  done
done
```

### 결과

결과: `results/20261025-1715*.json` (15개)

| 입력 토큰 | TTFT 3회 (ms) | TTFT 중앙값 | 입력 처리 (서버) | TPOT 평균 |
| ---: | --- | ---: | ---: | ---: |
| 40 | 143 / 110 / 102 | 110 ms | 100 ms | 18.2 ms |
| 130 | 124 / 123 / 131 | 124 ms | 113 ms | 18.3 ms |
| 530 | 547 / 501 / 505 | 505 ms | 487 ms | 18.4 ms |
| 1030 | 944 / 964 / 953 | 953 ms | 916 ms | 18.9 ms |
| 2030 | 1965 / 2013 / 1992 | 1992 ms | 1943 ms | 19.4 ms |

입력 처리는 서버 `prompt_eval_duration`의 중앙값이다. TTFT와 입력 처리의 차이(약 10~50 ms)는 클라이언트·HTTP 처리 시간이다.

### 관찰

- 약 130 tokens까지는 TTFT가 길이와 상관없이 약 100~120 ms로 거의 일정했다.
- 530 tokens 이후로는 TTFT가 길이에 비례했다. 530 → 2030 tokens 구간에서 토큰당 약 0.97 ms, 입력 처리 속도로 약 1030 tok/s다.
- 입력 처리(약 1030 tok/s)가 토큰 생성(약 54 tok/s)보다 약 20배 빨랐다.
- 입력이 길수록 TPOT이 18.2 → 19.4 ms로 약 7% 늘었다.

### 해석

- 입력 처리(prefill)는 모든 입력 토큰을 한 번에 묶어 계산하므로, 가중치를 한 번 읽어 수백 토큰에 쓴다. 그래서 토큰 생성(decode)보다 훨씬 빠르고, 메모리가 아니라 연산이 병목이라고 추정한다. GPU 연산 사용률은 아직 계산하지 않았다.
- 짧은 입력에서 TTFT가 일정한 것은 길이와 무관한 고정 비용이 지배하기 때문으로 보인다. 그 고정 비용의 정체는 확인하지 않았다.
- TPOT 증가는 메모리 대역폭 모델로 예측된다. 토큰 하나를 만들 때 가중치(4.92 GB)와 함께 앞선 모든 토큰의 KV cache를 읽는다. llama3.1:8b의 KV cache는 토큰당 약 128 KB(32 layers × 8 KV heads × 128 dim × K·V × 2 bytes, f16 가정)이므로 2030 tokens면 약 0.27 GB가 더 읽힌다. 예측 18.2 × (4.92 + 0.27) ÷ 4.92 ≈ 19.2 ms, 실측 19.4 ms.

### 서비스 관점

- 이 장비에서 RAG로 문서 2000 tokens를 붙이면 답이 시작되기까지 약 2초가 걸린다.
- TTFT 목표가 1초라면 입력을 약 1000 tokens 이하로 유지하거나, 공통 앞부분을 prefix cache로 재사용해야 한다.

## 한계

- 길이당 3회만 측정했다. 각 길이의 첫 실행이 다른 실행보다 느린 경향(40 tokens에서 143 ms)이 있으나 원인을 확인하지 않았다.
- 입력이 같은 문장의 반복이라 실제 문서와 다르다. 입력 처리 시간은 내용보다 토큰 수에 좌우된다고 가정했다.
- 모델이 문장 끝을 내고 일찍 멈춰 `eval_count`가 64보다 작은 실행이 많다(24~58). TPOT 계산에는 실제 생성 토큰 수를 썼다.
- 동시 요청이 없는 조건이다. 동시 요청에서의 TTFT는 다음 실험에서 측정한다.

## 측정 과정에서 겪은 문제

- zsh에서 `prompt`는 셸 프롬프트를 바꾸는 특수 변수다. 스크립트 변수 이름으로 쓰지 않는다.
- zsh는 `$( )` 서브셸 안에서 `$RANDOM`이 매번 같은 값을 낸다. 첫 시도에서 모든 입력이 같아져 2·3회차가 캐시로 약 35 ms가 나왔다. 이 결과 14개는 삭제했고, 번호는 Python의 `time.time_ns()`로 만든다.
- 같은 초에 끝난 두 실행의 파일 이름이 겹쳐 하나가 덮어써졌다. 파일 이름에 마이크로초를 붙였다.
