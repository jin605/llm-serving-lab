"""Prefix cache 실험용 입력을 만든다.

같은 문장을 반복한 문서 뒤에 질문을 붙인다. --change-at을 주면 문서의 해당 위치 문장
하나를 토큰 수가 같은 다른 문장으로 바꾼다. 결과는 표준 출력으로 내보낸다.
"""
import argparse

SENTENCE = "The quick brown fox jumps over the lazy dog."
CHANGED = "The quick brown cat jumps over the lazy dog."  # fox → cat, 토큰 수 같음

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--doc-id", required=True, help="문서 맨 앞에 붙는 번호. 같은 번호끼리만 cache를 공유한다")
parser.add_argument("--sentences", type=int, default=100, help="문서 문장 수 (문장당 10 tokens)")
parser.add_argument("--change-at", type=int, help="바꿀 문장 위치(%%). 0이면 첫 문장, 100이면 마지막 문장")
parser.add_argument("--question", required=True)
args = parser.parse_args()

doc = [SENTENCE] * args.sentences
if args.change_at is not None:
    index = round(args.change_at / 100 * (args.sentences - 1))
    doc[index] = CHANGED

print(f"[doc {args.doc_id}] {' '.join(doc)} Question: {args.question}")
