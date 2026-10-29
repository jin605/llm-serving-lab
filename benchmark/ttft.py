import argparse
import json
import time
import urllib.request
from datetime import datetime
from pathlib import Path

parser = argparse.ArgumentParser(description="LLM 서버에 요청 하나를 보내 TTFT와 TPOT을 측정한다.")
parser.add_argument("prompt", help="보낼 질문")
parser.add_argument("--model", default="llama3.1:8b")
parser.add_argument("--num-predict", type=int, default=64, help="최대 출력 토큰 수")
parser.add_argument("--out-dir", default="experiments/03-ttft/results", help="결과 저장 디렉터리")
parser.add_argument("--api", choices=["ollama", "openai"], default="ollama",
                    help="ollama: /api/generate, openai: OpenAI 호환 /chat/completions (vLLM, Ollama 모두 지원)")
parser.add_argument("--base-url", help="기본값: ollama는 http://localhost:11434, openai는 http://localhost:11434/v1")
args = parser.parse_args()

options = {"temperature": 0, "seed": 42, "num_predict": args.num_predict}
if args.api == "ollama":
    base_url = args.base_url or "http://localhost:11434"
    url = f"{base_url}/api/generate"
    payload = {"model": args.model, "prompt": args.prompt, "stream": True, "options": options}
else:
    base_url = args.base_url or "http://localhost:11434/v1"
    url = f"{base_url}/chat/completions"
    payload = {
        "model": args.model,
        "messages": [{"role": "user", "content": args.prompt}],
        "stream": True,
        "stream_options": {"include_usage": True},  # 마지막에 토큰 수(usage)를 받는다
        "temperature": options["temperature"],
        "seed": options["seed"],
        "max_tokens": options["num_predict"],
    }

req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
)


def read_events(resp):
    """응답 스트림을 JSON 이벤트로 바꾼다. Ollama는 줄마다 JSON, OpenAI 형식은 'data: ' 뒤에 JSON이 온다."""
    for line in resp:
        line = line.strip()
        if not line:
            continue
        if args.api == "openai":
            if not line.startswith(b"data: "):
                continue
            line = line[len(b"data: "):]
            if line == b"[DONE]":
                return
        yield json.loads(line)


def token_text(event):
    if args.api == "ollama":
        return event["response"]
    choices = event.get("choices") or []
    if not choices:
        return ""
    return (choices[0].get("delta") or {}).get("content") or ""


started_at = datetime.now().astimezone()
start = time.perf_counter()              # 1. 요청 보내기 직전 시각
first_token_at = None
last_token_at = None
chunks = []                              # 받은 토큰 조각을 모아 답변 텍스트를 만든다
finish_reason = None
server_stats = {}

with urllib.request.urlopen(req) as resp:
    for event in read_events(resp):      # 2. 이벤트(대개 토큰 하나)씩 읽기
        text = token_text(event)
        if text:
            now = time.perf_counter()
            if first_token_at is None:
                first_token_at = now     # 3. 첫 토큰 도착 시각
            last_token_at = now          # 4. 마지막 토큰 도착 시각
            chunks.append(text)
        if args.api == "ollama":
            if event["done"]:
                finish_reason = event["done_reason"]
                server_stats = {k: v for k, v in event.items() if k not in ("response", "context")}
        else:
            for choice in event.get("choices") or []:
                if choice.get("finish_reason"):
                    finish_reason = choice["finish_reason"]
            if event.get("usage"):
                server_stats = {"usage": event["usage"]}
end = time.perf_counter()

if args.api == "ollama":
    output_tokens = server_stats["eval_count"]
else:
    # usage가 없으면 내용이 있던 이벤트 수로 대신한다
    output_tokens = server_stats.get("usage", {}).get("completion_tokens") or len(chunks)

ttft = first_token_at - start
total = end - start
# 토큰 사이 간격의 평균. 토큰이 N개면 간격은 N-1개다
tpot = (last_token_at - first_token_at) / (output_tokens - 1) if output_tokens > 1 else None

# 모델 로딩이 0.1초 넘게 걸렸으면 cold로 본다. OpenAI 형식은 로딩 시간을 알려 주지 않는다
if "load_duration" in server_stats:
    load_s = server_stats["load_duration"] / 1e9
    cache_state = "cold" if load_s > 0.1 else "warm"
else:
    load_s = None
    cache_state = "unknown"

result = {
    "started_at": started_at.isoformat(),
    "api": args.api,
    "url": url,
    "model": args.model,
    "prompt": args.prompt,
    "options": options,
    "cache_state": cache_state,
    "ttft_s": ttft,
    "tpot_s": tpot,
    "total_s": total,
    "output_tokens": output_tokens,
    "finish_reason": finish_reason,
    "response": "".join(chunks),
    "server_stats": server_stats,
}

out_dir = Path(args.out_dir)
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / f"{started_at:%Y%m%d-%H%M%S-%f}.json"
out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")

load_text = f", load {load_s * 1000:.0f} ms" if load_s is not None else ""
print(f"TTFT  = {ttft * 1000:.1f} ms ({cache_state}{load_text})")
print(f"TPOT  = {tpot * 1000:.1f} ms" if tpot is not None else "TPOT  = (토큰 1개라 계산 불가)")
print(f"total = {total:.3f} s ({output_tokens} tokens, {finish_reason})")
print(f"saved to {out_path}")
