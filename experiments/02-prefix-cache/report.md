# 02-prefix-cache

상태: 실험 1 완료 (Mac + Ollama). cache가 깨지는 조건은 다음 실험에서 확인한다.

## 질문

요청의 앞부분(시스템 프롬프트, RAG 문서)이 같을 때, 서버가 그 계산을 재사용하면 TTFT가 얼마나 줄어드는가? 어떤 조건에서 재사용이 깨지는가?

## 공통 조건

- 환경: [환경 기록](../../docs/environment.md), MacBook Pro M5 Pro 48 GB
- 모델: `llama3.1:8b` (Q4_K_M)
- 런타임: Ollama 서버 0.33.2, `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_CONTEXT_LENGTH=4096`
- 측정 도구: [`benchmark/ttft.py`](../../benchmark/ttft.py), stream: true, temperature 0, seed 42
- 모델 warm 상태에서 측정한다.

## 사전 관찰: 같은 prompt 반복 시 TTFT 감소 (2026-10-25)

TTFT 측정 도구를 만들며 같은 요청을 반복하다가 관찰했다.

- 조건: num_predict 64, 입력 20 tokens
- 결과는 터미널 출력만 있고 파일로 저장하지 않았다.

| 실행 | `서울에 대해 자세히 설명해줘.` | `부산에 대해 자세히 설명해줘.` |
| --- | ---: | ---: |
| 1번째 | 112.4 ms | 119.1 ms |
| 2번째 | 39.7 ms | 37.6 ms |
| 3번째 | 36.8 ms | 37.6 ms |

TPOT은 모든 실행에서 18.3~18.5 ms로 같았다.

### 해석

- 모델 로딩(cold start)은 아니다. 로딩이 있으면 약 1.5초가 더 걸린다. 첫 실행의 추가 시간은 약 75~80 ms다.
- 가설 1, GPU 예열: 유휴 상태의 GPU가 첫 요청에서 깨어나느라 느렸다.
- 가설 2, prompt cache: 같은 입력을 다시 보내면 직전 계산(KV cache)을 재사용한다.
- 서울 질문 3회 직후, GPU가 깨어 있는 상태에서 부산 질문으로 바꾸자 다시 119 ms로 느려졌다. 가설 1은 이를 설명하지 못하므로 가설 2를 지지한다.
- 이전 동시성 실험의 서버 통계에서도 같은 prompt의 첫 요청만 `prompt_eval_duration`이 약 0.10초였고, 이후 요청은 약 0.02초였다.

### 측정에 주는 교훈

- TTFT를 잴 때는 cache 상태를 통제해야 한다. 같은 prompt를 반복하면 실제 서비스보다 TTFT가 짧게 나온다.
- 01-concurrency 실험 1·2는 모든 요청이 같은 prompt였으므로, 일부 요청의 입력 처리 시간이 cache 덕분에 짧았을 수 있다.

## 실험 1: 공통 문서 길이에 따른 재사용 효과 (2026-10-26)

### 상황

RAG처럼 같은 문서를 붙여 두고 질문만 바꿔 묻는 경우를 재현했다. RAG 검색은 구현하지 않았다. LLM 서버는 검색 과정을 모르고 "문서 + 질문"으로 된 긴 입력만 받으므로, 입력의 길이와 모양만 흉내 냈다.

```text
요청 A: [doc <id>] <문서> Question: How many times does the word fox appear?   ← 문서를 처음 봄
요청 B: [doc <id>] <문서> Question: What animal is lazy?                     ← 같은 문서를 다시 봄
```

### 가설과 예측

- 가설: 서버는 앞부분이 같은 만큼 이전 계산(KV cache)을 재사용하고, 뒤의 다른 부분만 계산한다.
- 예측: A의 TTFT는 문서 길이에 비례한다(입력 길이 실험의 토큰당 약 0.97 ms). B의 TTFT는 문서 길이와 무관하게 짧은 입력 수준(약 110 ms)이다.

### 조건

- 문서: `The quick brown fox jumps over the lazy dog.`(10 tokens)을 n번 반복. n = 0, 50, 100, 200 → 약 0, 500, 1000, 2000 tokens
- 문서 맨 앞에 `[doc <time_ns>]`를 붙였다. A와 B는 같은 번호를 쓰고, 반복마다 번호가 바뀌어 이전 반복의 cache를 쓰지 못한다.
- A 직후 B를 보냈다. 길이마다 A·B 쌍을 3회 반복했다.
- num_predict 16 (TTFT만 본다)

실행 명령:

```bash
for n in 0 50 100 200; do
  for rep in 1 2 3; do
    id=$(python3 -c "import time; print(time.time_ns())")
    doc=$(python3 -c "import sys; print('The quick brown fox jumps over the lazy dog. ' * int(sys.argv[1]))" "$n")
    out="experiments/02-prefix-cache/results/doc${n}-rep${rep}"
    python3 benchmark/ttft.py "[doc $id] $doc Question: How many times does the word fox appear?" --num-predict 16 --out-dir "$out"
    python3 benchmark/ttft.py "[doc $id] $doc Question: What animal is lazy?" --num-predict 16 --out-dir "$out"
  done
done
```

### 결과

결과: `results/doc{n}-rep{1,2,3}/` (디렉터리마다 A·B 두 파일, 파일 이름 시각순으로 먼저가 A)

| 문서 길이 | 입력 토큰 (A / B) | A TTFT 3회 (ms) | B TTFT 3회 (ms) | A 평균 | B 평균 | 단축 |
| ---: | --- | --- | --- | ---: | ---: | ---: |
| 0 | 33 / 29 | 117 / 112 / 111 | 112 / 111 / 110 | 113 ms | 111 ms | 없음 |
| 약 500 | 533 / 529 | 558 / 559 / 550 | 104 / 111 / 114 | 555 ms | 110 ms | 약 5배 |
| 약 1000 | 1033 / 1029 | 938 / 944 / 942 | 105 / 114 / 114 | 941 ms | 111 ms | 약 8배 |
| 약 2000 | 2033 / 2029 | 1961 / 1972 / 1997 | 117 / 118 / 117 | 1976 ms | 117 ms | 약 17배 |

서버 입력 처리 시간(`prompt_eval_duration`)도 같은 경향이다. 2000 tokens 문서에서 A는 약 1935 ms, B는 약 105 ms였다.

### 관찰

- A의 TTFT는 문서 길이에 비례했다(토큰당 약 0.95 ms).
- B의 TTFT는 문서 길이와 상관없이 약 110 ms로 일정했다. 문서가 없을 때와 같다.
- 서버의 `prompt_eval_count`는 B에서도 전체 길이(예: 2029)로 기록됐다. cache 재사용 여부는 토큰 수가 아니라 `prompt_eval_duration`이나 TTFT로 판단해야 한다.

### 해석

- 가설을 지지한다. B는 같은 문서 부분을 재사용하고 뒤의 질문 부분만 계산했다.
- 문서가 길수록 효과가 크다. 2000 tokens 문서에서 TTFT가 약 2초에서 0.12초로 줄었다. 입력 길이 실험에서 "RAG 문서 2000 tokens면 TTFT 1초 목표를 못 지킨다"고 했던 문제가 두 번째 질문부터는 해결된다.
- B의 약 110 ms는 cache로 더 줄지 않는 바닥이다. 사전 관찰에서 완전히 같은 prompt를 다시 보냈을 때(새로 계산할 토큰이 거의 없음)는 약 37 ms였다. 새로 계산할 토큰이 몇 개라도 있으면 약 100 ms의 고정 비용이 드는 것으로 보인다. 그 정체는 확인하지 않았다.

### 한계

- A 직후 B를 보낸, cache에 가장 유리한 조건이다. 사이에 다른 요청이 끼면 cache가 밀려날 수 있다.
- 실제 RAG는 질문마다 검색 문서나 그 순서가 달라질 수 있다. Prefix cache는 앞부분이 처음부터 같은 만큼만 재사용하므로 실제 효과는 더 작을 수 있다.
- 문서가 같은 문장의 반복이다. 입력 처리 시간은 내용보다 토큰 수에 좌우된다고 가정했다.
- Ollama(llama.cpp)의 cache 저장 방식(슬롯별 보관, 메모리 한도)은 확인하지 않았다.

## 다음 실험: cache가 깨지는 조건

- 문서 맨 앞 한 토큰만 바꾸면 재사용이 완전히 깨지는가? 맨 뒤 한 토큰을 바꾸면?
- A와 B 사이에 다른 문서의 요청이 끼어들면 재사용이 유지되는가?
- RAG 문서의 순서가 바뀌면 재사용이 얼마나 줄어드는가? 공통 부분을 앞에, 바뀌는 부분을 뒤에 두면 얼마나 살릴 수 있는가?
