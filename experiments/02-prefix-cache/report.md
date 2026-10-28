# 02-prefix-cache

상태: Mac + Ollama 실험 1~3 완료. vLLM에서 실험 1·2를 반복할 예정이다.

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

## 실험 2: 바뀐 위치에 따른 재사용 (2026-10-28)

### 질문

문서 중 한 문장만 바뀌면 재사용이 어디까지 유지되는가?

### 가설과 예측 (측정 전 작성)

- 가설: prefix cache는 처음부터 같은 부분까지만 재사용하고, 처음 달라진 지점부터 뒤는 전부 다시 계산한다.
- 예측: `TTFT ≈ 110 ms + (바뀐 지점 뒤의 토큰 수) × 토큰당 처리 시간`. 문서 약 1000 tokens 기준:

| 바뀐 위치 | 다시 계산할 양 | 예측 TTFT (0.95 ms/token) | 예측 TTFT (실험 1 기준 0.83 ms/token) |
| ---: | ---: | ---: | ---: |
| 바꾸지 않음 | 질문만 | 약 110 ms | 약 110 ms |
| 0% (첫 문장) | 전부 | 약 1060 ms | 약 940 ms |
| 25% | 75% | 약 820 ms | 약 735 ms |
| 50% | 50% | 약 585 ms | 약 525 ms |
| 75% | 25% | 약 350 ms | 약 320 ms |
| 100% (마지막 문장) | 거의 없음 | 약 110 ms | 약 110 ms |

### 조건

- 입력 생성: [`workloads/prefix_variants.py`](../../workloads/prefix_variants.py). 문장 100개(약 1000 tokens) 문서 뒤에 질문을 붙인다. `--change-at`으로 해당 위치 문장의 `fox`를 `cat`으로 바꾼다(토큰 수 같음).
- 요청 A: 원본 문서 + 질문 1. 요청 B: 한 문장을 바꾼 문서 + 질문 2. A 직후 B를 보낸다.
- 위치: 바꾸지 않음, 0, 25, 50, 75, 100%. 위치마다 3회. 반복마다 문서 번호를 바꿔 이전 cache를 쓰지 못하게 한다.
- num_predict 16

실행 명령:

```bash
for pos in none 0 25 50 75 100; do
  for rep in 1 2 3; do
    id=$(python3 -c "import time; print(time.time_ns())")
    out="experiments/02-prefix-cache/results/change${pos}-rep${rep}"
    change=(); [ "$pos" != none ] && change=(--change-at "$pos")
    a=$(python3 workloads/prefix_variants.py --doc-id "$id" --question "How many times does the word fox appear?")
    b=$(python3 workloads/prefix_variants.py --doc-id "$id" "${change[@]}" --question "What animal is lazy?")
    python3 benchmark/ttft.py "$a" --num-predict 16 --out-dir "$out"
    python3 benchmark/ttft.py "$b" --num-predict 16 --out-dir "$out"
  done
done
```

### 결과

결과: `results/change{none,0,25,50,75,100}-rep{1,2,3}/` (디렉터리마다 A·B 두 파일, 시각순으로 먼저가 A)

A(바꾸지 않은 원본, cache 없음)는 18회 모두 948~972 ms였다.

| 바뀐 위치 | 예측 (0.83 ms/token) | B TTFT 3회 (ms) | B 평균 |
| ---: | ---: | --- | ---: |
| 바꾸지 않음 | 약 110 ms | 105 / 115 / 117 | 112 ms |
| 0% | 약 940 ms | 956 / 957 / 950 | 954 ms |
| 25% | 약 735 ms | 743 / 738 / 740 | 740 ms |
| 50% | 약 525 ms | 522 / 507 / 518 | 516 ms |
| 75% | 약 320 ms | 351 / 352 / 351 | 351 ms |
| 100% | 약 110 ms | 118 / 118 / 109 | 115 ms |

### 관찰과 해석

- 가설을 지지한다. 처음 달라진 지점까지만 재사용하고 그 뒤는 다시 계산했다. `TTFT ≈ 115 ms + (처음 달라진 지점 뒤의 토큰 수) × 약 0.84 ms`로 예측할 수 있다.
- 75% 위치만 예측보다 약 30 ms 높았다. 입력 처리 시간이 토큰 수에 완전히 정비례하지는 않는 것으로 보이며 원인은 확인하지 않았다.
- 1000 tokens 중 단어 하나만 달라도 그 위치가 맨 앞이면 재사용이 전혀 되지 않았다(954 ms, cache 없는 A와 같음). 맨 끝이 바뀌면 손해가 거의 없었다.
- 프롬프트 설계 규칙: 고정된 내용(시스템 프롬프트, 공통 문서)은 앞에, 자주 바뀌는 내용(현재 시각, 사용자 정보, 질문)은 뒤에 둔다. RAG 문서는 고정된 순서로 붙인다.

## 실험 3: 다른 요청이 끼어들 때 (2026-10-28)

### 조건과 결과

- A(문서1) → 다른 문서 요청 k개 → B(문서1, 질문만 다름) 순서로 보냈다. k = 0, 1, 3, 7, 각 3회. 모든 문서는 약 1000 tokens이고 서로 다르다.
- parallel=1이라 처리 칸이 하나뿐이다. 다른 요청이 처리되면 문서1의 KV cache는 GPU 칸에서 밀려난다.
- 결과: `results/interleave{k}-rep{1,2,3}/` (요청 순서대로 저장, 마지막 파일이 B)

| 끼어든 요청 수 | B TTFT 3회 | 평균 |
| ---: | --- | ---: |
| 0 | 106 / 105 / 105 ms | 105 ms |
| 1 | 128 / 133 / 133 ms | 131 ms |
| 3 | 141 / 148 / 141 ms | 143 ms |
| 7 | 153 / 139 / 129 ms | 140 ms |

cache 없는 요청은 약 930~1030 ms였다.

### 해석

- 다른 요청이 7개 끼어들어도 B는 문서1을 재사용했다. llama.cpp가 밀려난 KV cache를 RAM에 보관했다가 다시 가져온 것으로 본다. 서버 로그의 `cache state ... limits: 8192 MiB`가 이 보관함이다.
- 끼어든 요청이 있으면 약 25~40 ms가 더 들었다. 보관함에서 문서 하나의 cache(약 128 MB)를 가져오는 비용으로 추정한다. 그래도 다시 계산(약 950 ms)보다 약 7배 빠르다.
- 계산상 보관함 8 GiB에는 약 1000 tokens 문서 약 60개가 들어간다. 넘치는 지점은 측정하지 않았다.

### vLLM 실무와의 관계

- 이 RAM 보관함은 llama.cpp 고유 동작이다. vLLM은 기본적으로 GPU 메모리 안에서 블록 단위로 cache를 관리하고 자리가 모자라면 오래된 것부터 지운다. 이번 수치는 vLLM에 그대로 옮길 수 없다.
- 개념은 실무와 이어진다. KV cache를 CPU 메모리나 디스크로 넘겨 보관하는 기능(vLLM의 LMCache 연동, SGLang 계층형 cache 등)이 같은 아이디어다. 서버가 여러 대이면 "다른 요청이 끼어들면?"이 "다른 서버로 가면?"이 되고, cache-aware routing으로 해결한다.
- 실험 1·2의 원리(앞에서부터 일치하는 만큼 재사용)와 프롬프트 설계 규칙은 vLLM, SGLang, 상용 API의 prompt caching에도 통한다.

## 측정하지 않은 것

- RAG 문서 순서가 바뀌는 경우는 따로 측정하지 않았다. 첫 문서가 바뀌면 실험 2의 0% 위치와 같아 재사용이 거의 되지 않는다고 예측한다.
- 보관함이 넘치는 지점은 llama.cpp 설정에 따른 값이라 측정하지 않았다.
- 같은 실험 1·2를 GPU 서버의 vLLM에서 반복해 원리가 같은지 확인한다.
