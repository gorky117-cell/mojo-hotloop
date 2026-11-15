import math
import time
from all7 import (
    stateful_trailing_backtest,
    find_closest_point_to_ray,
    accumulate_haversine_distance,
    clean_pdf_text,
    scrub_pii,
    find_closest_match,
    chunk_document,
)

print("1. quant:", stateful_trailing_backtest(10000, 100.0, 0.05, 0.001))
xs = [0.1 * float(i) for i in range(100)]
ys = [0.2 * float(i) for i in range(100)]
zs = [1.0 + 0.3 * float(i) for i in range(100)]
print("2. ar_spatial:", find_closest_point_to_ray(xs, ys, zs, 0.0, 0.0, 0.0, 0.1, 0.2, 1.0))
lats = [12.97 + 0.001 * float(i) for i in range(100)]
lons = [77.59 + 0.001 * float(i) for i in range(100)]
print("3. geo:", accumulate_haversine_distance(lats, lons))
s_pdf = "inter-\noperability \f\nPage 1\n  hello   \u0928\u092e\u0938\u094d\u0924\u0947\U0001f680\n\n\nworld"
print("4. pdf len:", len(clean_pdf_text(s_pdf)))
print("5. pii:", scrub_pii("Customer PAN ABCDE1234F call 9876543210"))
cands = ["invoice", "receipt", "\u0928\u092e\u0938\u094d\u0924\u0947", "organization"]
print("6. ocr:", find_closest_match("invoic", cands, 3), find_closest_match("\u0928\u092e\u0938\u094d\u0924", cands, 3))
print("7. rag:", len(chunk_document("retrieval-augmented generation pipeline \u0928\u092e\u0938\u094d\u0924\u0947 \U0001f680 vector database", 25, 5)))
