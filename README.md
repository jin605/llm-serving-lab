# LLM Serving Lab

문제 해결 중심의 LLM 서빙 학습 및 실험 기록.

## PoC 목표

Ollama와 vLLM에 요청을 보내고, 입력 길이·출력 길이·동시 요청 수에 따른 성능을 측정하고 비교하는 Python CLI 도구를 만든다.

질문 → 개념 공부 → 기능 구현 → 실험 → 기록 순서로 진행한다.

## 구현 단계와 완료 기준

- [x] 1. Ollama API로 단일 요청: 모델과 프롬프트를 입력받아 응답을 받는다.
- [x] 2. 결과 저장: 응답과 실행 통계를 JSON 파일로 저장한다.
- [x] 3. 스트리밍 측정: 요청 시작부터 첫 출력 도착까지 TTFT를 측정한다.
- [x] 4. 길이별 반복 실험: 입력·출력 길이 조건과 실제 토큰 수를 기록하고 비교한다.
- [x] 5. 동시 요청과 분석: 동시 요청 수에 따른 지연과 처리량을 비교한다.
- [ ] 6. vLLM 연결: NVIDIA GPU 서버에서 같은 측정 도구로 실험한다.
- [ ] 7. Prefix Cache: 공통 Prefix 재사용 조건과 성능 변화를 검증한다.

SGLang, Quantization, GPU Profiling, Kubernetes는 필요한 실험이 생길 때 확장한다.

## 현재 진행 상황

- 학습 및 실험 기록 구조 마련.1
- 로컬 Ollama에서 `llama3.1:8b` 실행과 GPU 로딩 확인.
- CLI로 출력 길이에 따른 생성 시간 변화 관찰: [Baseline 기록](experiments/00-baseline/report.md).
- curl로 동시 요청을 보내 `OLLAMA_NUM_PARALLEL` 1/2/4/8에 따른 지연과 처리량을 비교했다: [Concurrency 결과](experiments/01-concurrency/report.md).
- 결과: parallel=1은 요청을 순차 처리하고, 병렬 처리 시 처리량은 51 → 120 tok/s로 늘었으나 4 이후 포화했다.
- 결과는 실행별 디렉터리에 `conditions.json`과 요청당 JSON 하나로 저장하며, client_total_s를 함께 기록한다.
- 직렬 decode가 메모리 대역폭의 85~90%를 쓰는 것을 계산으로 확인했다.
- `benchmark/ttft.py`로 단일 요청의 TTFT와 TPOT을 측정했다. 같은 prompt 반복 시 prompt cache로 TTFT가 줄어드는 것을 관찰했다: [Prefix Cache 사전 관찰](experiments/02-prefix-cache/report.md).
- `ttft.py`가 prompt를 인자로 받고 결과를 JSON으로 저장한다. 입력 길이 40~2030 tokens에서 TTFT를 측정했다: [TTFT 결과](experiments/03-ttft/report.md).
- 결과: 약 130 tokens까지 TTFT는 약 110 ms로 일정하고, 이후 길이에 비례한다(입력 처리 약 1030 tok/s). 입력이 길면 KV cache를 더 읽어 TPOT이 약 7% 늘었다.
- `ttft.py`가 모델 이름과 답변 텍스트도 저장한다. 출력 16~1024 tokens에서 `전체 시간 ≈ TTFT + 출력 토큰 수 × TPOT`이 맞는 것을 확인했다.
- 긴 연속 실행에서 GPU 클럭이 1620 → 약 1360 MHz로 내려가며 TPOT이 약 5~7% 늘어나는 것을 `powermetrics`로 관찰했다.
- 동시 사용자 8명에서 parallel 1/2/4/8별 TTFT·TPOT을 측정했다. TTFT 1초·TPOT 50 ms 목표를 지키며 처리할 수 있는 사용자는 약 4명이었다: [Concurrency 실험 3](experiments/01-concurrency/report.md).
- 같은 문서에 질문만 바꿔 보내자 두 번째 요청의 TTFT가 문서 길이와 상관없이 약 110 ms였다. 2000 tokens 문서에서 약 2초 → 0.12초: [Prefix Cache 실험 1](experiments/02-prefix-cache/report.md).
- 다음 작업: prefix cache가 깨지는 조건(앞부분 변경, 다른 요청 끼어들기, 문서 순서 변경)을 확인한다. 이후 GPU 서버에서 vLLM으로 같은 측정을 반복한다(6단계).
## 디렉터리 역할

| 경로 | 역할 |
| --- | --- |
| `docs/` | 학습 일지와 실행 환경 |
| `serving/` | 로컬 및 vLLM 서버 실행 설정 |
| `workloads/` | 프롬프트와 요청 패턴 생성 |
| `benchmark/` | 공통 측정 및 지표 계산 코드 |
| `experiments/` | 실험별 보고서, 설정, 결과 |
| `scripts/` | 실행, 수집, 분석 보조 스크립트 |

## 기록 방식

- 계획과 진행 상황은 이 README에서 관리한다.
- 공부한 개념, 막힌 점, 다음 행동은 [학습 일지](docs/learning-log.md)에 한 학습 세션당 짧게 기록한다. 매 실행마다 글을 쓰지 않는다.
- 실험의 조건, 비교 결과, 해석은 해당 실험 폴더의 `report.md`에 묶어 기록한다.
- 결과는 실행별 디렉터리에 `conditions.json`과 요청당 JSON 하나로 저장하며 client_total_s를 포함한다. 별도 시간·오류 TXT 파일은 만들지 않는다.
- 실행별 설정과 환경도 결과와 함께 보관하고 덮어쓰지 않는다.
- 개념과 소스 분석도 우선 학습 일지에 적고, 찾기 어려울 만큼 쌓일 때만 별도 문서로 분리한다.
- 모델 가중치는 저장소 외부 캐시에 보관하고 모델 ID와 revision을 기록한다.
- 관찰한 사실과 원인에 대한 가설을 구분한다.

## 관련 기록

- [전체 학습 계획](llm_serving_problem_driven_plan.md): 장기 로드맵이며 현재 PoC 단계는 이 README를 따른다.
- [학습 일지](docs/learning-log.md)
- [환경 기록](docs/environment.md)
- [Concurrency](experiments/01-concurrency/report.md)
- [Prefix Cache](experiments/02-prefix-cache/report.md)
- [TTFT](experiments/03-ttft/report.md)