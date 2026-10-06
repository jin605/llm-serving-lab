# LLM Serving / AI Systems 문제 해결형 학습·프로젝트 계획

## 1. 목표

이 계획의 목표는 특정 프레임워크를 많이 다루는 것이 아니다.

최종적으로 다음 흐름을 스스로 수행할 수 있는 것을 목표로 한다.

```text
LLM 서비스를 직접 배포
→ 실제 부하 발생
→ TTFT / TPOT / Throughput / GPU Memory 측정
→ 병목 위치 추적
→ 가설 수립
→ Serving Runtime / Infra / Model 설정 변경
→ 동일 조건으로 재측정
→ 개선 여부와 Trade-off 설명
```

핵심 포지셔닝:

> **LLM Serving / AI Systems Engineer**
>
> 모델을 새로 연구하는 것보다, 이미 학습된 LLM을 실제 GPU 환경에서 빠르고 안정적이며 효율적으로 운영하고 병목을 분석하는 역할에 초점을 둔다.

기존의 Knowledge Graph / Ontology 경험은 차별화 요소로 유지하되, 본 프로젝트의 중심은 **LLM Serving 문제 해결 능력**으로 둔다.

---

# 2. 기술이 아니라 문제를 기준으로 공부한다

기존 방식:

```text
vLLM 공부
→ SGLang 공부
→ LiteLLM 공부
→ Prometheus 공부
→ Grafana 공부
→ CUDA 공부
→ K8s 공부
```

문제점:

- 기술을 많이 나열하게 됨
- 실제 문제 해결 경험이 약해질 수 있음
- "써봤다" 수준으로 끝날 가능성이 높음
- 면접에서 왜 사용했는지 설명하기 어려움

변경 방식:

```text
문제 발생
→ 무엇을 측정할지 결정
→ 병목 가설 수립
→ 필요한 기술 선택
→ 실험
→ 결과 비교
→ 개선
```

즉 기술은 목적이 아니라 문제를 해결하기 위한 수단으로 사용한다.

---

# 3. 전체 프로젝트 질문

전체 프로젝트는 하나의 질문으로 묶는다.

> **제한된 GPU 자원에서 LLM 서비스를 얼마나 빠르고 안정적이며 효율적으로 운영할 수 있는가?**

이를 다음 네 개의 하위 문제로 나눈다.

```text
Problem 1.
요청이 늘어날 때 왜 latency가 증가하는가?

Problem 2.
반복되는 Prompt인데 왜 Prefix Cache가 제대로 재사용되지 않는가?

Problem 3.
GPU가 있는데도 왜 충분한 Throughput이 나오지 않는가?

Problem 4.
여러 GPU / 여러 서버 환경에서 어떻게 안정적으로 운영할 것인가?
```

---

# 4. 핵심 성능 지표

프로젝트 전체에서 공통으로 보는 지표는 다음과 같다.

## Latency

### TTFT

Time To First Token.

사용자 요청 이후 첫 번째 token이 생성되기까지 걸리는 시간.

주로 영향을 받는 요소:

- Prefill
- Prompt Length
- Prefix Cache
- Scheduler
- Queueing
- GPU Saturation

### TPOT

Time Per Output Token.

첫 token 이후 token 하나를 생성하는 데 걸리는 시간.

주로 영향을 받는 요소:

- Decode
- Memory Bandwidth
- KV Cache
- Batch
- GPU Compute

### End-to-End Latency

전체 요청부터 응답 완료까지 걸리는 시간.

---

## Throughput

예:

```text
requests/sec
tokens/sec
output tokens/sec
```

동시에 얼마나 많은 요청을 처리할 수 있는지를 본다.

---

## 안정성

```text
p50 latency
p95 latency
p99 latency
Error Rate
OOM 발생 여부
Max Stable Concurrency
```

평균값보다 p95 / p99와 안정적인 최대 처리량을 중요하게 본다.

---

## GPU 자원

```text
GPU Utilization
VRAM Usage
Memory Bandwidth
KV Cache Usage
Power
GPU Idle Time
```

---

# 5. Problem 1 — 요청이 늘어나면 왜 느려지는가?

## 문제 정의

동시 요청 수를 늘렸을 때 어느 순간부터 TTFT와 p95 latency가 급격히 증가할 수 있다.

확인할 질문:

```text
Concurrency가 증가하면
왜 latency가 증가하는가?

GPU 계산 자원이 부족한가?
메모리가 부족한가?
KV Cache가 부족한가?
Scheduler Queue가 쌓이는가?
Batching이 비효율적인가?
```

---

## 실험

Concurrency를 단계적으로 증가시킨다.

```text
1
4
8
16
32
64
```

환경은 최대한 고정한다.

```text
동일 GPU
동일 Model
동일 dtype
동일 Prompt Dataset
동일 Input Length
동일 Output Length
```

측정:

```text
TTFT
TPOT
Throughput
p50
p95
GPU Utilization
VRAM
KV Cache Usage
Error Rate
```

---

## 분석 흐름

```text
Concurrency 증가
↓
TTFT / p95 증가 확인
↓
GPU Utilization 확인
↓
KV Cache / VRAM 확인
↓
Queue / Scheduler 확인
↓
Batching 상태 확인
↓
병목 가설 수립
```

---

## 필요한 기술

이 문제를 해결할 때 필요한 만큼 사용한다.

```text
vLLM
Continuous Batching
KV Cache
Prometheus
Grafana
Nsight Systems
```

SGLang은 동일 workload 비교가 필요한 경우 추가한다.

---

## 결과물

```text
Concurrency vs TTFT
Concurrency vs TPOT
Concurrency vs Throughput
Concurrency vs GPU Utilization
Concurrency vs VRAM
```

최종적으로 다음 질문에 답할 수 있어야 한다.

> 이 환경에서 stable concurrency는 얼마이며, 그 이상에서 병목이 발생하는 원인은 무엇인가?

---

# 6. Problem 2 — Prefix Cache가 왜 재사용되지 않는가?

이 문제는 프로젝트의 Deep Dive Case Study로 사용한다.

## 문제 배경

Qwen 계열 Hybrid Architecture에서 일반 Attention과 GDN / Linear Attention 계열 레이어가 함께 사용될 수 있다.

개념적으로:

```text
일반 Attention

Token 1 → K,V
Token 2 → K,V
Token 3 → K,V
...
Token N → K,V

→ sequence length에 따라 KV Cache 증가
```

반면 GDN / Linear Attention 계열은 state snapshot 형태의 cache를 사용할 수 있다.

```text
GDN / Linear Attention

[State Snapshot]

→ 상대적으로 고정된 state 크기
```

특정 환경에서 관찰 가능한 예시:

```text
GDN / Linear Attention State
≈ 204KB / layer

Attention KV Cache
≈ 1KB / token / GPU
```

실제 값은 모델 버전, dtype, tensor parallel 구성, runtime 버전에 따라 달라질 수 있으므로 직접 확인한다.

---

## 핵심 가설

Hybrid Cache 구조 때문에 cache page/block granularity가 커지면 일반 Attention의 Prefix Cache 재사용 단위도 커질 수 있다.

예:

```text
204KB page
÷
1KB/token

≈ 204 tokens
```

이 경우 공통 prefix가 150 token이라면:

```text
Request A
[공통 150][A 전용 token...]

Request B
[공통 150][B 전용 token...]
```

block 단위 hash라면 첫 full block에 서로 다른 token이 포함될 수 있다.

```text
Request A Block
hash(common + A)

Request B Block
hash(common + B)

→ Cache Key 불일치
→ Prefix Cache Miss
```

가설:

> **Hybrid cache의 큰 block/page granularity가 짧은 shared prefix에서 cache reuse efficiency를 낮추고 TTFT를 증가시킬 수 있다.**

---

## 실험 2-1. Shared Prefix Length

예:

```text
32
64
128
192
200
203
204
205
208
216
256
512
1024
```

측정:

```text
Cache Hit / Miss
Cached Tokens
Prefix Cache Hit Rate
TTFT
TPOT
Throughput
VRAM
GPU Utilization
```

---

## 실험 2-2. Workload 유형

```text
A. 동일한 긴 System Prompt + 서로 다른 User Prompt
B. 짧은 공통 Prefix + 서로 다른 User Prompt
C. 완전히 다른 Prompt
D. 동일 Prompt 반복
```

---

## 원인 추적

```text
TTFT 증가
↓
Prefill 재계산량 증가 여부 확인
↓
Prefix Cache Hit Rate 확인
↓
Cache Key / Block Hash 확인
↓
Block Size 확인
↓
KV Cache Manager / Allocator 확인
↓
Qwen Hybrid Cache 구조 확인
↓
GDN State와 Attention KV Memory Layout 비교
```

---

## Source Code 분석 범위

vLLM 전체를 읽는 것이 목적이 아니다.

다음 질문에 답할 수 있을 정도로만 내려간다.

```text
1. Cache memory 크기는 어디서 결정되는가?
2. Hybrid layer별 cache requirement는 어떻게 표현되는가?
3. Block/Page 크기는 어떻게 결정되는가?
4. Prefix Cache는 어떤 단위로 hash하는가?
5. 어떤 조건에서 cached block을 재사용하는가?
6. Cache miss가 TTFT에 얼마나 영향을 주는가?
```

분석 대상:

```text
Qwen Model Implementation
↓
Attention / GDN / Linear Attention Layer
↓
KV Cache Specification
↓
KV Cache Manager / Allocator
↓
Block Pool
↓
Prefix Cache
↓
Block Hash / Cache Key
```

---

## 선택: vLLM 수정

원인이 명확한 경우에만 수행한다.

```text
Original vLLM
vs
Modified vLLM
```

비교:

```text
Cache Hit Rate
TTFT
TPOT
Throughput
VRAM
GPU Utilization
Correctness
```

성과보다 중요한 것은 과정이다.

```text
문제 관찰
→ 가설
→ Source 분석
→ 원인 확인
→ 수정
→ A/B Test
→ Trade-off 설명
```

수정이 성능 개선으로 이어지지 않아도 결과를 그대로 기록한다.

---

# 7. Problem 3 — GPU가 있는데도 왜 Throughput이 안 나오는가?

## 문제 정의

GPU Utilization이 낮거나 충분한 GPU가 있는데도 throughput이 낮을 수 있다.

가능한 원인:

```text
Batch Size가 너무 작음
Scheduler가 비효율적
Memory-bound
Compute-bound
Kernel launch overhead
CPU-GPU synchronization
Memory Copy
KV Cache pressure
```

---

## 분석 순서

먼저 높은 레벨에서 본다.

```text
Throughput 낮음
↓
GPU Utilization 확인
↓
Batch / Concurrency 확인
↓
VRAM / KV Cache 확인
↓
Memory Bandwidth 확인
↓
CPU-GPU Timeline 확인
```

여기까지로 설명되지 않을 때만 낮은 레벨로 내려간다.

```text
Nsight Systems
↓
Kernel / Memory Copy / Idle 분석
↓
특정 Kernel 병목 확인
↓
Nsight Compute
↓
필요 시 Triton / CUDA
```

---

## 중요한 원칙

CUDA는 프로젝트의 출발점이 아니다.

```text
나쁜 접근

CUDA부터 공부
→ Kernel 작성
→ 어디에 쓸지 고민
```

대신:

```text
좋은 접근

Serving 병목 발견
→ Profiling
→ Kernel 문제 확인
→ 필요하면 CUDA/Triton
```

CUDA는 **문제 해결에 필요할 때 내려가는 마지막 계층**으로 둔다.

---

# 8. Problem 4 — 여러 GPU / 서버를 어떻게 운영할 것인가?

## 문제 정의

단일 GPU에서 끝나지 않고 여러 GPU와 여러 inference instance를 운영할 때 다음 문제가 생긴다.

```text
어느 GPU에 Job을 배치할 것인가?
GPU 부족 시 어떻게 처리할 것인가?
GPU 장애 발생 시 어떻게 대응할 것인가?
여러 Replica에 요청을 어떻게 분산할 것인가?
모델 하나가 GPU 하나에 안 들어가면 어떻게 할 것인가?
```

---

## 핵심 개념

### Data Parallel / Replica

```text
Load Balancer
      ↓
 ┌────┼────┐
GPU1 GPU2 GPU3
Model Model Model
```

각 GPU에 모델 replica를 두고 요청을 분산한다.

---

### Tensor Parallel

모델 하나를 여러 GPU에 나눈다.

```text
Model
 ↓
GPU 1
GPU 2
GPU 3
GPU 4
```

---

### Continuous Batching

각 inference instance 내부에서 여러 요청을 지속적으로 묶는다.

---

## Kubernetes GPU Scheduling

필요한 범위:

```text
GPU Node
GPU Resource Request / Limit
Pod Scheduling
Node Selector / Affinity
GPU Operator
Device Plugin
Job / Deployment
Restart Policy
Health Check
```

처음부터 복잡한 GPU Scheduler를 직접 구현하지 않는다.

목표는:

> 모델 Serving Pod를 GPU Node에 배포하고, 요청 부하와 장애 상황에서 어떻게 동작하는지 이해한다.

---

# 9. GPU 장애 대응 학습 범위

GPU Infra / MLOps 영역을 과도하게 깊게 파기보다 운영 관점에서 이해한다.

## 기본 흐름

```text
GPU Error
↓
Xid 확인
↓
Hardware / Software 분류
↓
특정 Job 문제?
CUDA / Driver 문제?
일시적 오류?
↓
Process Restart
Pod Restart
Node Reboot
Power Cycle
↓
지속 시 Hardware 점검 / Vendor 대응
```

알아야 할 수준:

```text
Xid란 무엇인가
nvidia-smi 확인
GPU 상태 확인
Driver / CUDA Version 확인
OOM 여부 확인
특정 workload에서 재현되는지 확인
Pod / Node 장애 분리
```

Kernel-level 문제를 직접 수정하는 것은 별도 전문 영역으로 본다.

---

# 10. Speculative Decoding / Drafter Deep Dive

이 영역은 선택적 심화 주제로 둔다.

## 구조

```text
Draft Model
→ 여러 token 후보 생성
        ↓
Target Model
→ 후보를 한 번에 검증
        ↓
채택 가능한 token 사용
```

핵심 trade-off:

```text
Drafter가 너무 작음
→ 빠름
→ 예측 정확도 낮음
→ Acceptance Rate 낮음

Drafter가 너무 큼
→ 예측 정확도 높음
→ Drafter 자체 비용 증가
```

---

## 실험 변수

```text
Draft Model Size
Draft Length
Acceptance Rate
Prompt 유형
Output Length
Concurrency
```

측정:

```text
TTFT
TPOT
Throughput
Acceptance Rate
GPU Utilization
VRAM
```

핵심 질문:

> 어떤 drafter 설정이 실제 end-to-end decode latency를 가장 잘 줄이는가?

---

# 11. Quantization은 별도 기술이 아니라 Serving 선택지로 다룬다

기존 방식:

```text
FP16
INT8
INT4
공부
```

변경:

> VRAM이 부족하거나 throughput 개선이 필요할 때 quantization이 실제 서비스에 어떤 영향을 주는지 측정한다.

---

## 실험

```text
FP16 / BF16
vs
INT8 / FP8
vs
INT4 / FP4
```

측정:

```text
Model Weight Memory
Total VRAM
TTFT
TPOT
Throughput
Quality
OOM 여부
Max Stable Concurrency
```

핵심 질문:

> 메모리는 줄었지만 실제 latency와 품질까지 개선되었는가?

---

# 12. Observability는 문제 추적을 위해 사용한다

## Prometheus / Grafana

목적:

```text
서비스 상태를 지속적으로 관찰
```

수집:

```text
request/sec
TTFT
TPOT
p95 latency
tokens/sec
GPU Utilization
VRAM
Error Rate
```

---

## OpenTelemetry

목적:

서비스 전체 경로에서 어디가 느린지 추적.

예:

```text
HTTP Request
→ Backend
→ Retrieval
→ LLM Gateway
→ vLLM
→ GPU
→ Response
```

---

## Nsight Systems

목적:

```text
CPU-GPU 실행 흐름 분석
```

확인:

```text
Kernel 실행 순서
Memory Copy
GPU Idle
CPU-GPU Synchronization
```

---

## Nsight Compute

목적:

특정 CUDA kernel 내부 병목 분석.

확인:

```text
Memory Throughput
Warp Stall
Occupancy
Instruction Efficiency
```

필요할 때만 사용한다.

---

# 13. 프로젝트 아키텍처

프로젝트는 복잡한 스택 자랑이 아니라 실험 가능한 최소 구조로 시작한다.

## 1차

```text
Client
 ↓
Backend API
 ↓
vLLM
 ↓
Qwen
 ↓
GPU
```

---

## 2차

```text
Client
 ↓
Backend API
 ↓
vLLM / SGLang
 ↓
Qwen
 ↓
GPU

+
Prometheus / Grafana
```

---

## 3차

```text
Client
 ↓
Backend
 ↓
LLM Gateway
 ↓
vLLM Replica
 ↓
GPU

+
Kubernetes
+
Monitoring
```

---

## 선택적 Knowledge Layer

차별화를 위해 별도 실험으로 연결할 수 있다.

```text
User
 ↓
Backend
 ↓
Ontology / Knowledge Graph
 ↓
GraphRAG
 ↓
LLM Serving
 ↓
GPU
```

하지만 Serving 프로젝트의 중심 질문을 흐리지 않도록 분리한다.

---

# 14. 실험 우선순위

## Phase 1 — Baseline Serving

목표:

```text
모델을 GPU에서 정상적으로 Serving
```

학습:

```text
Linux
Docker
LLM Inference 기본
Prefill / Decode
vLLM 기본
```

결과:

```text
단일 요청 정상 처리
TTFT / TPOT 측정
GPU / VRAM 확인
```

---

## Phase 2 — Load & Benchmark

목표:

```text
부하가 증가할 때 시스템이 어떻게 변하는지 확인
```

학습:

```text
Concurrency
Continuous Batching
KV Cache
Throughput
p50 / p95
```

실험:

```text
Concurrency 1 / 4 / 8 / 16 / 32 / 64
```

---

## Phase 3 — Cache Deep Dive

목표:

```text
Prefix Cache와 Hybrid Cache 병목을 직접 분석
```

학습:

```text
Qwen Attention Architecture
GDN / Linear Attention
KV Cache
Block / Page
Prefix Hash
Cache Hit Rate
```

결과:

```text
Prefix Length
→ Cache Hit Rate
→ TTFT
```

---

## Phase 4 — Runtime Comparison

목표:

```text
같은 workload에서 vLLM과 SGLang의 차이를 설명
```

주의:

누가 더 빠른지 순위를 매기는 것이 목적이 아니다.

확인:

```text
어떤 workload에서
어떤 runtime 구조가
왜 유리하거나 불리한가?
```

---

## Phase 5 — Production Operation

목표:

```text
Serving을 실제 서비스처럼 운영
```

학습:

```text
Kubernetes
GPU Scheduling
Prometheus
Grafana
OpenTelemetry
GPU Error 기본 대응
```

---

## Phase 6 — Low-level Deep Dive

조건:

고수준 분석으로 설명되지 않는 성능 병목이 존재할 때만 진행.

```text
Nsight Systems
↓
Nsight Compute
↓
Triton
↓
CUDA
```

---

# 15. 프로젝트 결과물

기술 목록보다 문제와 결과를 먼저 보여준다.

## README 구조

```text
1. Problem
2. Environment
3. Baseline
4. Measurement
5. Hypothesis
6. Experiment
7. Result
8. Root Cause
9. Improvement
10. Trade-off
```

---

## 예시

### Case 1 — Concurrency Saturation

```text
Problem
Concurrency 32 이상에서 p95 TTFT 급증

Observation
GPU Utilization XX%
KV Cache XX%
Queueing 증가

Hypothesis
...

Change
...

Result
p95 TTFT: XX → YY
Throughput: XX → YY
```

---

### Case 2 — Qwen Prefix Cache

```text
Problem
짧은 shared prefix에서 cache hit rate 저하

Observation
Block boundary 전후 hit rate 차이

Root Cause
Hybrid cache page/block granularity

Result
Prefix Length
→ Cache Hit Rate
→ TTFT 관계 확인
```

---

### Case 3 — GPU Bottleneck

```text
Problem
GPU Utilization이 낮은데 throughput도 낮음

Profiling
Nsight Systems 확인

Root Cause
...

Improvement
...
```

---

# 16. GitHub 구조

기술별 폴더보다 실험 중심으로 구성한다.

```text
llm-serving-lab/
├── serving/
│   ├── baseline/
│   ├── vllm/
│   └── sglang/
├── workloads/
│   ├── concurrency/
│   ├── prefix-cache/
│   └── speculative-decoding/
├── experiments/
│   ├── 01-concurrency/
│   ├── 02-prefix-cache/
│   ├── 03-quantization/
│   ├── 04-runtime-comparison/
│   └── 05-gpu-profiling/
├── infra/
│   ├── docker/
│   ├── kubernetes/
│   └── monitoring/
├── benchmark/
├── scripts/
├── results/
├── docs/
└── README.md
```

---

# 17. 공부 범위

## 반드시 이해

```text
LLM Inference
Prefill
Decode
TTFT
TPOT
Throughput
Latency
Concurrency
KV Cache
Continuous Batching
Prefix Caching
GPU Memory
Memory Bandwidth
Quantization
```

---

## 반드시 실습

```text
vLLM Serving
Concurrency Benchmark
Prefix Cache Experiment
GPU / VRAM Monitoring
Prometheus / Grafana
Kubernetes GPU Deployment
```

---

## 문제 발생 시 깊게

```text
SGLang
Speculative Decoding
Nsight
Triton
CUDA
NCCL
Tensor Parallel
Distributed Inference
```

---

## 후순위

```text
MPI
OpenMP
OpenACC
Slurm
Singularity
HPC 전반
```

현재 목표가 HPC Engineer가 아니라면 필수로 보지 않는다.

---

# 18. 이 프로젝트에서 하지 않을 것

범위를 명확히 제한한다.

```text
새로운 LLM Architecture 연구
새로운 Quantization Algorithm 개발
CUDA Kernel을 이유 없이 직접 구현
프레임워크 기능 전부 학습
Kubernetes 전체 기능 학습
분산학습 시스템 구축
```

핵심은 다음이다.

> **문제 해결에 필요한 깊이까지만 내려간다.**

---

# 19. 최종적으로 설명할 수 있어야 하는 것

프로젝트가 끝났을 때 아래 질문에 답할 수 있어야 한다.

```text
1. Prefill과 Decode의 차이는 무엇인가?
2. TTFT와 TPOT는 각각 무엇에 영향을 받는가?
3. Continuous Batching은 왜 필요한가?
4. KV Cache가 GPU Memory에 어떤 영향을 주는가?
5. Prefix Cache는 언제 효과가 있고 언제 효과가 없는가?
6. Concurrency가 증가하면 어느 지점에서 saturation이 발생하는가?
7. GPU Utilization이 낮다고 항상 GPU가 부족하지 않은 것은 왜인가?
8. Memory-bound와 Compute-bound를 어떻게 구분하는가?
9. Quantization이 메모리와 성능에 어떤 trade-off를 만드는가?
10. 여러 GPU를 쓸 때 Data Parallel과 Tensor Parallel은 어떻게 다른가?
11. vLLM과 SGLang은 어떤 workload 차이에서 비교해야 하는가?
12. GPU 장애가 발생했을 때 어디까지 직접 진단할 수 있는가?
13. 언제 Nsight를 사용해야 하는가?
14. 언제 CUDA/Triton까지 내려가야 하는가?
15. 실제 병목을 어떻게 측정하고 개선했는가?
```

---

# 20. 최종 프로젝트 메시지

이 프로젝트에서 보여줘야 하는 것은 다음이 아니다.

```text
vLLM 사용 가능
SGLang 사용 가능
CUDA 사용 가능
K8s 사용 가능
Grafana 사용 가능
```

보여줘야 하는 것은 다음이다.

> **LLM Serving 시스템을 직접 배포하고, 실제 workload를 만들어 성능을 측정하고, 병목을 가설화하고, Runtime·GPU·Infra 레벨에서 원인을 추적한 뒤 개선 여부를 검증할 수 있다.**

최종 흐름:

```text
Deploy
→ Load
→ Measure
→ Observe
→ Hypothesize
→ Analyze
→ Optimize
→ Validate
```

이 흐름이 기술 스택보다 우선한다.

---

# 21. 권장 최종 포지셔닝

```text
Backend
→ AI Backend
→ LLM Serving / Inference
→ GPU / AI Systems
```

Kubernetes / MLOps 영역은 운영 확장 능력으로 가져가고,

CUDA / Triton은 실제 병목이 Low-level Kernel에 있을 때 내려갈 수 있는 심화 역량으로 가져간다.

Knowledge Graph / Ontology는 별도의 강점으로 유지한다.

최종적으로는:

> **Backend 기반의 LLM Serving / AI Systems Engineer**

를 중심 포지션으로 잡고,

> **Knowledge Graph / Ontology 경험을 가진 AI Systems Engineer**

라는 차별화를 더하는 방향으로 구성한다.
