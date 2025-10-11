"""
test_llm.py

Test script to run the retrieval -> LLM generation pipeline from the terminal.
It uses app.search.search to get top chunks and app.llm_manager.generate_answer to get natural text.
"""

from app.search import search
from app.llm_manager import generate_answer

def main():
    print("RAG test (type 'exit' to quit)")
    while True:
        q = input("\nAsk a question: ").strip()
        if not q or q.lower() == "exit":
            break

        # Retrieve top chunks
        results = search(q, top_k=3)  # returns [(chunk_text, score), ...]
        if not results:
            print("No retrieval results found.")
            continue

        print("\nTop retrieved chunks:")
        for t, s in results:
            print(f"  [score={s:.3f}] {t[:200]}{'...' if len(t) > 200 else ''}")

        chunks = [text for text, _ in results]

        # Generate answer using the LLM
        answer = generate_answer(q, chunks)
        print("\nGenerated answer:\n")
        print(answer)
        print("\n" + "-"*60)

if __name__ == "__main__":
    main()
