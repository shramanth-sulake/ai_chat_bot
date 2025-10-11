# quick_test.py
from app.search_db import search_db
r = search_db("customer_experience", top_k=3)
print(r)
