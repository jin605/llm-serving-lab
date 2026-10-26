# 학습 일지

한 학습 세션이 끝날 때 이해한 점, 막힌 점, 다음 행동을 짧게 기록한다. 매 명령이나 실행마다 기록할 필요는 없다. 상세 실험 수치는 해당 실험 폴더의 `report.md`에 둔다.

## 2026-10-06 — 로컬 실행과 출력 길이 관찰

- 실행: Ollama의 `llama3.1:8b`를 로딩하고 `ollama ps`에서 `100% GPU`를 확인했다.
- 이해: Prefill은 입력 처리, Decode는 출력 토큰을 순차적으로 생성하는 단계다.
- 이해: TTFT는 요청 시작부터 첫 출력 토큰을 받기까지의 시간이며, CLI의 입력 처리 시간과 같지 않다.
- 관찰: 짧은 출력과 긴 출력의 입력 토큰 수는 같았고, 긴 출력에서 생성 시간이 늘었다.
- 한계: CLI 단일 실행 결과이며 TTFT와 반복 측정은 아직 없다.
- 다음 행동: Python으로 Ollama API를 호출하고 응답과 통계를 JSON으로 저장한다.
- 관련 실험: [Baseline](../experiments/00-baseline/report.md)

## 다음 기록 양식

```markdown
## YYYY-MM-DD — 주제

- 공부 / 구현한 것:
- 이해한 점 또는 막힌 점:
- 다음 행동:
- 관련 실험:
```

## 2026-10-12 — 직접 동시 요청 2개 실행

- 실행: curl로 같은 질문 두 개를 동시에 전송했다.
- 관찰: client_total은 약 1.19초와 2.36초였다. TTFT는 측정하지 않았다.
- 이해: JSON은 Ollama 응답과 서버 통계이고, client_total은 curl에서 측정한 요청 완료까지의 시간이다.
- 기록: 요청당 JSON 하나로 합쳤다. 에이전트가 별도 실행한 1·2·4·8개 결과는 삭제했다.
- 다음 행동: 두 요청의 서버 통계를 비교하며 원인을 살펴본다.
- 관련 실험: [Concurrency](../experiments/01-concurrency/report.md)

## 2026-10-13 — 동시 처리 수에 따른 지연과 처리량

- 실행: Ollama 앱을 종료하고 터미널에서 `OLLAMA_CONTEXT_LENGTH=4096 OLLAMA_NUM_PARALLEL=N ollama serve`로 띄워 N을 1/2/4/8로 바꿔 측정했다.
- 관찰: parallel=1에서는 완료 시각이 eval 한 번(약 1.17초) 간격으로 벌어졌다. 대기 시간은 별도 필드 없이 `total_duration`에 포함된다.
- 관찰: 병렬에서는 요청이 같은 시각에 끝났고, 토큰당 생성 시간은 17.8 → 61.7 ms로 늘었지만 처리량은 51 → 120 tok/s로 늘었다. 4 → 8에서는 처리량이 약 13%만 늘었다.
- 이해: `ollama ps`의 `100% GPU`는 모델이 GPU 메모리에 모두 올라갔다는 뜻이지 연산 사용률이 아니다. Decode는 토큰마다 가중치를 읽어야 해서 메모리 대역폭에 묶이고, 요청을 묶으면 한 번 읽은 가중치를 여러 요청이 같이 쓴다(가설).
- 막힌 점: 결과 디렉터리를 고정 이름으로 써서 이전 결과가 덮어써졌다. 실행별 디렉터리와 `conditions.json`으로 바꿨다.
- 막힌 점: Ollama는 슬롯 수 × context 길이만큼 KV cache를 잡는다. parallel=8에 기본 context 32768이면 메모리가 부족할 수 있어 4096으로 줄였다.
- 다음 행동: 조건별 반복 측정으로 4~8 사이 포화를 확인한다.
- 관련 실험: [Concurrency](../experiments/01-concurrency/report.md)

## 2026-10-25 — 메모리 대역폭 검증과 TTFT 측정 시작

- 계산: 307 GB/s ÷ 4.92 GB ≈ 62 tok/s가 이론상 최대이고 실제는 56 tok/s다. 직렬 decode는 메모리 대역폭의 85~90%를 쓴다.
- 이해: 병목은 GPU 연산이 아니라 가중치를 읽는 속도다. 빨라지려면 읽는 양을 줄이거나(양자화) 한 번 읽은 가중치를 나눠 써야 한다(batching).
- 이해: 병렬 처리는 공짜가 아니다. 지연 목표(TTFT, TPOT)를 지키는 범위에서 처리량을 최대로 하는 지점을 찾아야 한다.
- 구현: `benchmark/ttft.py`로 stream 응답의 첫 토큰 도착 시각을 재서 TTFT와 TPOT을 계산했다. warm 상태에서 TTFT 약 37 ms, TPOT 약 18.4 ms.
- 관찰: 같은 prompt의 첫 요청만 TTFT가 약 115 ms였다. prompt를 바꾸는 실험으로 GPU 예열이 아니라 prompt cache 때문임을 확인했다.
- 이해: curl의 `time_starttransfer`는 Ollama에서는 첫 토큰과 비슷하지만, 헤더를 먼저 보내는 서버에서는 TTFT가 아니다. 그래서 Python으로 첫 토큰을 직접 확인한다.
- 구현: `ttft.py`가 prompt를 인자로 받고, cold/warm을 `load_duration`으로 판별해 결과를 JSON으로 저장하게 했다.
- 관찰: 입력 길이를 40~2030 tokens로 바꾸자 약 130 tokens까지 TTFT는 약 110 ms로 일정했고, 이후 토큰당 약 0.97 ms씩 늘었다.
- 이해: prefill은 입력을 한 번에 묶어 계산해 약 1030 tok/s로 decode(약 54 tok/s)보다 20배 빠르다. prefill은 연산, decode는 메모리가 병목이다(가설).
- 이해: 입력이 길면 토큰마다 KV cache도 더 읽어야 해서 TPOT이 18.2 → 19.4 ms로 늘었다. 메모리 대역폭 모델로 19.2 ms를 예측했고 맞았다.
- 막힌 점: zsh의 `prompt` 특수 변수와 서브셸 `$RANDOM` 고정값 때문에 첫 시도에서 cache가 끼어들었다. 결과를 지우고 다시 측정했다.
- 이해: 토큰은 음절이나 단어가 아니다. 비용과 지연은 토큰 수로 결정되고, 한국어는 영어보다 토큰이 많이 나오는 경우가 많다.
- 구현: `ttft.py`를 argparse로 바꿔 `--model`, `--num-predict`를 받고 답변 텍스트도 저장한다. 답변을 남기면 속도와 품질을 함께 볼 수 있다(대전 질문에 사실과 다른 답).
- 관찰: 출력 16~1024 tokens에서 전체 시간이 `TTFT + 출력 토큰 수 × TPOT` 예측과 맞았다. 모델이 일찍 멈추지 않게 숫자 세기 작업을 시켰다.
- 관찰: 1024 tokens를 연속 실행하자 TPOT이 회차마다 늘었다. `powermetrics`로 보니 GPU 클럭이 1620 → 약 1360 MHz로 내려갔고, 발열 단계는 Nominal이었다.
- 이해: 클럭이 15% 내려가도 TPOT은 5~7%만 늘었다. decode는 주로 메모리에 묶여 있기 때문이다. 긴 벤치마크는 클럭 하락까지 고려해야 한다.
- 관찰: 동시 사용자 8명에서 parallel을 1 → 8로 올리자 평균 TTFT는 4.48 → 0.32초로 줄고 TPOT은 18 → 62 ms로 늘었다.
- 이해: parallel은 TTFT와 TPOT 중 무엇을 희생할지 고르는 설정이다. TTFT 1초·TPOT 50 ms 목표로는 이 맥북에서 동시 약 4명이 한계다. 목표를 어떻게 잡느냐가 결론을 바꾼다.
- 관찰: 생성 중인 요청에 다른 요청의 입력 처리가 끼어들면 그 요청의 TPOT이 늘었다. chunked prefill이 해결하려는 문제다.
- 다음 행동: Mac에서 Prefix Cache 실험을 하고, GPU 서버에서 vLLM으로 같은 측정을 반복한다.
- 관련 실험: [Prefix Cache](../experiments/02-prefix-cache/report.md), [TTFT](../experiments/03-ttft/report.md)

## 2026-10-26 — Prefix cache 재사용 효과

- 실행: 같은 문서(약 0~2000 tokens)에 질문만 바꾼 요청 두 개를 연달아 보냈다. RAG 검색은 구현하지 않고 서버가 받는 입력 모양만 흉내 냈다.
- 관찰: 첫 요청의 TTFT는 문서 길이에 비례했고(2000 tokens에서 약 2초), 두 번째 요청은 길이와 상관없이 약 110 ms였다.
- 이해: 서버는 앞부분이 같은 만큼 KV cache를 재사용하고 뒤의 다른 부분만 계산한다. RAG에서 같은 문서로 여러 번 질문하면 두 번째부터 TTFT 목표를 지킬 수 있다.
- 이해: `prompt_eval_count`는 재사용한 토큰까지 포함한 전체 길이로 나온다. 재사용 여부는 `prompt_eval_duration`이나 TTFT로 판단한다.
- 이해: LLM 서버는 RAG 검색을 모른다. 서빙 성능은 문서를 어떻게 찾았는지가 아니라 입력의 길이와 앞부분이 얼마나 같은지로 정해진다.
- 다음 행동: 앞부분 변경, 다른 요청 끼어들기, 문서 순서 변경으로 cache가 깨지는 조건을 확인한다.
- 관련 실험: [Prefix Cache](../experiments/02-prefix-cache/report.md)
