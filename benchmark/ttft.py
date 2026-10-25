import argparse
import json
import time
import urllib.request
from datetime import datetime
from pathlib import Path

parser = argparse.ArgumentParser(description="Ollama 요청 하나의 TTFT와 TPOT을 측정한다.")
parser.add_argument("prompt", help="보낼 질문")
parser.add_argument("--model", default="llama3.1:8b")
parser.add_argument("--num-predict", type=int, default=64, help="최대 출력 토큰 수")
args = parser.parse_args()

payload = {
    "model": args.model,
    "prompt": args.prompt,
    "stream": True,
    "options": {"temperature": 0, "seed": 42, "num_predict": args.num_predict},
}
req = urllib.request.Request(
    "http://localhost:11434/api/generate",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
)

started_at = datetime.now().astimezone()
start = time.perf_counter()              # 1. 요청 보내기 직전 시각
first_token_at = None
chunks = []                              # 받은 토큰 조각을 모아 답변 텍스트를 만든다

with urllib.request.urlopen(req) as resp:
    for line in resp:                    # 2. 한 줄(토큰 하나)씩 읽기
        event = json.loads(line)
        if event["response"] and first_token_at is None:
            first_token_at = time.perf_counter()   # 3. 첫 토큰 도착 시각
        chunks.append(event["response"])
        if event["done"]:
            end = time.perf_counter()              # 4. 마지막 줄 도착 시각
            final = event

ttft = first_token_at - start
total = end - start
tpot = (total - ttft) / (final["eval_count"] - 1)

# 모델 로딩이 0.1초 넘게 걸렸으면 cold로 본다
load_s = final["load_duration"] / 1e9
cache_state = "cold" if load_s > 0.1 else "warm"

result = {
    "started_at": started_at.isoformat(),
    "model": args.model,
    "prompt": args.prompt,
    "options": payload["options"],
    "cache_state": cache_state,
    "ttft_s": ttft,
    "tpot_s": tpot,
    "total_s": total,
    "response": "".join(chunks),
    "server_stats": {k: v for k, v in final.items() if k not in ("response", "context")},
}

out_dir = Path("experiments/03-ttft/results")
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / f"{started_at:%Y%m%d-%H%M%S-%f}.json"
out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")

print(f"TTFT  = {ttft * 1000:.1f} ms ({cache_state}, load {load_s * 1000:.0f} ms)")
print(f"TPOT  = {tpot * 1000:.1f} ms")
print(f"total = {total:.3f} s ({final['eval_count']} tokens, {final['done_reason']})")
print(f"saved to {out_path}")
