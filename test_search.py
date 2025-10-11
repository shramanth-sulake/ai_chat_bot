"""
test_search.py

Simple runner to test semantic search against the stored sample embeddings.
"""

from app.search import search

def main():
    while True:
        query = input("\nEnter your query (or 'exit' to quit): ")
        if query.lower() == "exit":
            break
        results = search(query, top_k=3)
        print("\nTop matches:")
        for text, score in results:
            print(f"  [score={score:.3f}] {text[:80]}...")

if __name__ == "__main__":
    main()
