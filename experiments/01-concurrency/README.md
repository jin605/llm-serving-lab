# 01-concurrency

## 목적

동시 요청을 보냈을 때 Ollama가 요청을 어떻게 처리하는지, 동시 처리 수(`OLLAMA_NUM_PARALLEL`)에 따라 지연과 처리량이 어떻게 달라지는지 확인한다.

## 공통 조건

- 모델: `llama3.1:8b` (Q4_K_M)
- 장비: MacBook Pro, Apple M5 Pro, 48 GB
- Ollama 서버: 0.33.2, 터미널에서 `ollama serve`로 직접 실행
- prompt: `서울에 대해 자세히 설명해줘.` (20 tokens)
- stream: false
- options: temperature 0, seed 42, num_predict 64
- context 길이: 4096 (`OLLAMA_CONTEXT_LENGTH`)
- 캐시 상태: warm (워밍업 요청으로 모델을 미리 올린 뒤 측정)
- curl 요청을 백그라운드로 동시에 실행했다.
- 반복: 조건당 1회

서버 실행 예:

```bash
OLLAMA_CONTEXT_LENGTH=4096 OLLAMA_NUM_PARALLEL=4 /Applications/Ollama.app/Contents/Resources/ollama serve
```

## 실험 1: 직렬 처리 확인 (parallel=1, 요청 4개)

`OLLAMA_NUM_PARALLEL=1`에서 요청 4개를 동시에 보냈다.

- 결과: [p1-ctx4096-warm-4req](results/p1-ctx4096-warm-4req-20261013-001311/)
- 완료 시각: 1.26 / 2.44 / 3.60 / 4.77초
- 요청별 eval_duration: 약 1.15초로 모두 같다.
- 전체 처리량: 256 tokens / 4.77초 ≈ 54 tok/s

완료 시각이 eval 한 번만큼(약 1.17초) 간격으로 벌어진다. 서버가 요청을 하나씩 처리하고, 뒤의 요청은 앞 요청이 끝날 때까지 기다린다. 대기 시간은 Ollama 통계에 별도 필드로 나오지 않고 `total_duration`에 포함된다. 완료 순서는 요청 번호와 다를 수 있다. 백그라운드 curl이 서버에 도착하는 순서가 매번 달라지기 때문이다.

## 실험 2: 동시 처리 수에 따른 변화

`OLLAMA_NUM_PARALLEL`과 동시 요청 수를 같게 맞춰 1, 2, 4, 8로 바꿨다.

| parallel = 요청 수 | 1 | 2 | 4 | 8 |
| --- | ---: | ---: | ---: | ---: |
| 요청 완료 시간 (s) | 1.25 | 1.79 | 2.40 | 4.26 |
| 토큰당 생성 시간 (ms) | 17.8 | 24.5 | 34.4 | 61.7 |
| 전체 처리량 (tok/s) | 51 | 72 | 107 | 120 |
| 처리량 (parallel=1 대비) | 1.0x | 1.4x | 2.1x | 2.3x |
| 결과 | [p1](results/p1-ctx4096-warm-1req-20261013-000455/) | [p2](results/p2-ctx4096-warm-2req-20261013-000721/) | [p4](results/p4-ctx4096-warm-4req-20261013-000805/) | [p8](results/p8-ctx4096-warm-8req-20261013-000837/) |

- 요청 완료 시간: 해당 실행에서 가장 늦게 끝난 요청의 `client_total_s`.
- 토큰당 생성 시간: `eval_duration / eval_count`의 요청 평균.
- 전체 처리량: 생성 토큰 합계 / 요청 완료 시간.

### 관찰

- parallel ≥ 2에서는 모든 요청이 거의 같은 시각에 끝났다. 서버가 요청을 묶어 동시에 생성했다.
- 동시 처리 수를 늘리면 요청 하나의 토큰 생성은 느려지고 전체 처리량은 늘었다.
- 4 → 8에서 처리량은 약 13%만 늘었고, 요청 완료 시간은 약 1.8배, 토큰당 생성 시간은 약 2배가 됐다.

### 해석 (가설)

- 직렬 decode는 토큰마다 가중치(약 4.9 GB)를 메모리에서 읽어야 해서 메모리 대역폭에 묶인다. 이때 연산 유닛은 대부분 대기한다. `ollama ps`의 `100% GPU`는 모델이 GPU 메모리에 모두 올라갔다는 뜻이지 연산 사용률이 아니다.
- 요청을 묶으면 한 번 읽은 가중치로 여러 요청의 토큰을 계산하므로 같은 장비에서 처리량이 늘어난다.
- 8에서 토큰당 생성 시간이 요청 수에 비례해 늘어난 것은 연산 쪽 한계에 도달했기 때문으로 추정한다.
- 이 장비와 모델 조합에서는 parallel 4 근처가 지연과 처리량의 균형점으로 보인다.

## 한계

- 조건당 1회만 측정했다. 특히 4와 8 사이의 포화는 반복 측정으로 확인해야 한다.
- 이전에 context 32768(앱 기본값)로 측정한 결과는 정리하면서 삭제했다. 그중 parallel=4 warm 실행에서 처리량 약 96 tok/s, `prompt_eval_duration` 0.47초를 관찰했다. context 4096에서는 각각 107 tok/s, 0.12초였다. 차이의 원인은 확인하지 않았다.
- TTFT는 측정하지 않았다(stream: false).
- 메모리 대역폭과 연산 한계에 대한 해석은 측정이 아닌 추정이다.

## 기록 방식

- 실행마다 `results/p{parallel}-ctx{context}-{warm|cold}-{N}req-{시각}/` 디렉터리를 만들어 덮어쓰지 않는다.
- 각 디렉터리에 `conditions.json`(parallel, context 길이, warm/cold, 요청 수, Ollama 버전, 시작 시각)과 요청당 JSON 하나를 저장한다.
- 요청 JSON에는 Ollama 응답과 통계, curl이 측정한 `client_total_s`를 함께 저장한다. `client_total_s`는 초 단위이며 Ollama의 duration 필드는 나노초 단위다.
- 결과 해석은 이 문서에 기록한다. 별도의 시간·오류 TXT 파일은 만들지 않는다.
