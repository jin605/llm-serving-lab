# LLM Serving Lab

문제 해결 중심의 LLM 서빙 학습 및 실험 기록.

목표는 모델을 배포하고, 부하를 만들어 성능을 측정하고, 병목 가설을 실험으로 검증하는 것이다.

## 학습 순서

1. [추론 개요](docs/concepts/01-inference-overview.md)
2. [Prefill과 Decode](docs/concepts/02-prefill-decode.md)
3. [KV Cache](docs/concepts/03-kv-cache.md)
4. [Baseline](experiments/00-baseline/README.md): 단일 요청과 측정 기준 확립
5. [Concurrency](experiments/01-concurrency/README.md): 부하에 따른 성능 변화
6. [Prefix Cache](experiments/02-prefix-cache/README.md): 공통 Prefix 재사용 조건

## 진행 상황

- [x] 학습 및 실험 기록 구조 마련
- [ ] 로컬 실행 환경 구성
- [ ] Baseline 측정
- [ ] Concurrency 실험
- [ ] Prefix Cache 실험

## 디렉터리 역할

| 경로 | 역할 |
| --- | --- |
| `docs/` | 학습 일지, 개념 정리, 환경 기록, 소스 분석 |
| `serving/` | 로컬 및 vLLM 서버 실행 설정 |
| `workloads/` | 프롬프트와 요청 패턴 생성 |
| `benchmark/` | 공통 측정 및 지표 계산 코드 |
| `experiments/` | 실험별 보고서, 설정, 결과 |
| `scripts/` | 실행, 수집, 분석 보조 스크립트 |

## 기록 규칙

- 매일 공부한 내용은 [학습 일지](docs/learning-log.md)에 짧게 기록한다.
- 정리된 개념은 `docs/concepts/`, 소스 분석은 `docs/source-reading/`에 기록한다.
- 실험의 질문, 조건, 결과 해석은 해당 실험의 `README.md`에 기록한다.
- 실험 결과는 `experiments/<실험>/results/run-001/`처럼 실행별로 저장하고 덮어쓰지 않는다.
- 실행별 설정과 환경도 결과와 함께 보관한다.
- 모델 가중치는 저장소 외부 캐시에 보관하고 모델 ID와 revision을 기록한다.
- 관찰한 사실과 원인에 대한 가설을 구분한다.

## 관련 기록

- [전체 학습 계획](llm_serving_problem_driven_plan.md)
- [학습 일지](docs/learning-log.md)
- [환경 기록](docs/environment.md)
