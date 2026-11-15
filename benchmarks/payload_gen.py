"""Deterministic payload generators matching examples/*/bench.py verbatim."""
import os
import random
import sys
from typing import Any, Dict

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from examples.pii_scrubber.verify import (
    gen_synthetic_aadhaar,
    gen_synthetic_card,
    gen_synthetic_pan,
    gen_synthetic_phone,
)


def get_quant_payloads() -> Dict[str, Dict[str, Any]]:
    return {
        "ticks_100k": {
            "ticks": 100_000,
            "start_price": 100.0,
            "stop_pct": 0.05,
            "fee_rate": 0.001,
            "iters": 40,
            "desc": "100,000 ticks trailing-stop backtest",
        }
    }


def get_ar_spatial_payloads() -> Dict[str, Dict[str, Any]]:
    specs = [
        ("small", 100, 1500, "Small cloud (100 vertices)"),
        ("medium", 1000, 200, "Medium cloud (1,000 vertices)"),
        ("large", 10000, 20, "Large cloud (10,000 vertices)"),
    ]
    out: Dict[str, Dict[str, Any]] = {}
    for key, n_points, iters, desc in specs:
        rng = random.Random(42)
        xs = [rng.uniform(-20.0, 20.0) for _ in range(n_points)]
        ys = [rng.uniform(-20.0, 20.0) for _ in range(n_points)]
        zs = [rng.uniform(1.0, 50.0) for _ in range(n_points)]
        out[key] = {
            "xs": xs,
            "ys": ys,
            "zs": zs,
            "ray": (0.0, 0.0, 0.0, 0.1, 0.2, 1.0),
            "iters": iters,
            "n_points": n_points,
            "desc": desc,
        }
    return out


def get_geo_payloads() -> Dict[str, Dict[str, Any]]:
    specs = [
        ("short", 100, 1500, "Short trail (100 waypoints)"),
        ("medium", 1000, 200, "Medium trail (1,000 waypoints)"),
        ("large", 10000, 20, "Long route (10,000 waypoints)"),
    ]
    out: Dict[str, Dict[str, Any]] = {}
    for key, n_points, iters, desc in specs:
        rng = random.Random(42)
        cur_lat = 12.9716
        cur_lon = 77.5946
        lats = [cur_lat]
        lons = [cur_lon]
        for _ in range(n_points - 1):
            cur_lat += rng.uniform(-0.01, 0.01)
            cur_lon += rng.uniform(-0.01, 0.01)
            lats.append(cur_lat)
            lons.append(cur_lon)
        out[key] = {
            "lats": lats,
            "lons": lons,
            "iters": iters,
            "n_points": n_points,
            "desc": desc,
        }
    return out


def get_pdf_payloads() -> Dict[str, Dict[str, Any]]:
    rng = random.Random(2026)
    tokens = [
        "inter-\noperability", "trans-\n   piler", "auto-\n\nmation",
        "docu-\n   ment", "page-\nbreak", "con-\nfiguration",
        "\f", "\f\n\n", "\nPage 1\n", "\nPage 99\n", "\nPage 12345\n",
        "    ", "  \t  ", "\t\t",
        "\n\n\n", "\n\n\n\n\n", "\n", "\n\n",
        "standard", "paragraph", "content", "sentence.", "court", "ruling", "statute",
        "\u0928\u092e\u0938\u094d\u0924\u0947", "\u092a\u094d\u0930\u094c\u0926\u094d\u092f\u094b\u0917\u093f\u0915\u0940", "\u0926\u0938\u094d\u0924\u093e\u0935\u0947\u091c\u093c", "\U0001f680", "\U0001f525", "12345",
    ]
    s_parts = []
    while sum(len(p) for p in s_parts) < 1024:
        s_parts.append(rng.choice(tokens) + " ")
    s_text = "".join(s_parts)[:1024]

    m_parts = []
    while sum(len(p) for p in m_parts) < 10240:
        m_parts.append(rng.choice(tokens) + " ")
    m_text = "".join(m_parts)[:10240]

    l_text = (m_text * 10)[:100000]
    return {
        "small": {"text": s_text, "iters": 800, "desc": f"Small extract ({len(s_text)} chars)"},
        "medium": {"text": m_text, "iters": 150, "desc": f"Medium document ({len(m_text)} chars)"},
        "large": {"text": l_text, "iters": 20, "desc": f"Large corpus ({len(l_text)} chars)"},
    }


def get_pii_payloads() -> Dict[str, Dict[str, Any]]:
    rng = random.Random(1337)
    short_text = f"Notice: Account card {gen_synthetic_card(rng)} charged $45."
    med_lines = []
    curr_len = 0
    templates = [
        "Audit log entry #{id}: Customer with PAN {pan} updated phone to {phone}.\n",
        "Transaction verification: Card {card} approved, Aadhaar {aadhaar} KYC verified.\n",
        "System notification: User {id} invoice paid on 2026-11-15 for \u20b95,000.\n",
        "\u0928\u092e\u0938\u094d\u0924\u0947 \u0917\u094d\u0930\u093e\u0939\u0915 #{id}: \u0906\u0927\u093e\u0930 {aadhaar} \u0938\u092b\u0932\u0924\u093e\u092a\u0942\u0930\u094d\u0935\u0915 \u0938\u0924\u094d\u092f\u093e\u092a\u093f\u0924 \U0001f680\n",
    ]
    uid = 1000
    while curr_len < 8192:
        tmpl = rng.choice(templates)
        line = tmpl.format(
            id=uid,
            card=gen_synthetic_card(rng),
            aadhaar=gen_synthetic_aadhaar(rng),
            phone=gen_synthetic_phone(rng),
            pan=gen_synthetic_pan(rng),
        )
        med_lines.append(line)
        curr_len += len(line)
        uid += 1
    med_text = "".join(med_lines)[:8192]
    large_text = (med_text * (100000 // len(med_text) + 1))[:100000]
    return {
        "short": {"text": short_text, "iters": 2000, "desc": f"Short record ({len(short_text)} chars)"},
        "medium": {"text": med_text, "iters": 200, "desc": f"Medium document ({len(med_text)} chars)"},
        "large": {"text": large_text, "iters": 20, "desc": f"Large corpus ({len(large_text)} chars)"},
    }


def get_ocr_payloads() -> Dict[str, Dict[str, Any]]:
    rng = random.Random(42)
    vocab = [
        "invoice", "receipt", "customer", "vendor", "payment",
        "balance", "statement", "account", "transaction", "subtotal",
        "discount", "shipping", "quantity", "description", "reference",
        "inventory", "department", "organization", "authorized", "signature",
    ]

    def mutate(w: str) -> str:
        chars = list(w)
        if len(chars) > 2:
            chars.pop(rng.randint(0, len(chars) - 1))
        chars.insert(rng.randint(0, len(chars)), rng.choice("abcde"))
        return "".join(chars)

    s_cands = [mutate(rng.choice(vocab)) for _ in range(20)]
    s_query = mutate("invoice")
    m_cands = [mutate(rng.choice(vocab)) for _ in range(200)]
    m_query = mutate("transaction")
    l_cands = [mutate(rng.choice(vocab)) for _ in range(2000)]
    l_query = mutate("organization")
    return {
        "small": {"query": s_query, "candidates": s_cands, "max_d": 3, "iters": 400, "desc": "Small corpus (20 candidates)"},
        "medium": {"query": m_query, "candidates": m_cands, "max_d": 3, "iters": 40, "desc": "Medium corpus (200 candidates)"},
        "large": {"query": l_query, "candidates": l_cands, "max_d": 3, "iters": 8, "desc": "Large corpus (2,000 candidates)"},
    }


def get_rag_payloads() -> Dict[str, Dict[str, Any]]:
    rng = random.Random(2026)
    words = [
        "retrieval-augmented", "generation", "pipeline", "documents", "embedding",
        "semantic", "vector", "database", "transformer", "attention", "context",
        "knowledge", "graph", "chunking", "strategy", "sliding", "window",
        "\u0928\u092e\u0938\u094d\u0924\u0947", "\u092a\u094d\u0930\u0923\u093e\u0932\u0940", "\u0926\u0938\u094d\u0924\u093e\u0935\u0947\u091c\u093c", "\u0938\u0942\u091a\u0928\u093e", "\u092a\u094d\u0930\u094c\u0926\u094d\u092f\u094b\u0917\u093f\u0915\u0940",
        "\U0001f680", "\u26a1", "\U0001f50d", "\U0001f4ca", "\U0001f9e0",
        "section", "paragraph", "tokenization", "optimization", "latency",
    ]
    s_parts = []
    while sum(len(p) for p in s_parts) < 1024:
        s_parts.append(rng.choice(words) + rng.choice([" ", " ", "\n", ", "]))
    s_text = "".join(s_parts)[:1024]

    m_parts = []
    while sum(len(p) for p in m_parts) < 10240:
        m_parts.append(rng.choice(words) + rng.choice([" ", " ", "\n", ". ", "; "]))
    m_text = "".join(m_parts)[:10240]

    l_text = (m_text * 10)[:100000]
    return {
        "small": {"text": s_text, "size": 250, "overlap": 50, "iters": 800, "desc": f"Small doc ({len(s_text)} chars)"},
        "medium": {"text": m_text, "size": 500, "overlap": 100, "iters": 150, "desc": f"Medium doc ({len(m_text)} chars)"},
        "large": {"text": l_text, "size": 1000, "overlap": 200, "iters": 20, "desc": f"Large doc ({len(l_text)} chars)"},
    }


def _escape_line(s: str) -> str:
    return (
        s.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\f", "\\f")
        .replace("\t", "\\t")
    )


def export_codon_fixture(out_path: str) -> None:
    """Export single-line UTF-8 fixture so Codon native binary reads identical payloads."""
    lines = []

    def add_str(tag: str, s: str):
        lines.append(f"STR\t{tag}\t{_escape_line(s)}\n")

    def add_floats(tag: str, vals):
        lines.append(f"FLT\t{tag}\t" + ",".join(repr(v) for v in vals) + "\n")

    def add_strs(tag: str, vals):
        lines.append(f"LST\t{tag}\t" + "\t".join(_escape_line(v) for v in vals) + "\n")

    for k, v in get_ar_spatial_payloads().items():
        add_floats(f"ar_{k}_xs", v["xs"])
        add_floats(f"ar_{k}_ys", v["ys"])
        add_floats(f"ar_{k}_zs", v["zs"])
    for k, v in get_geo_payloads().items():
        add_floats(f"geo_{k}_lats", v["lats"])
        add_floats(f"geo_{k}_lons", v["lons"])
    for k, v in get_pdf_payloads().items():
        add_str(f"pdf_{k}", v["text"])
    for k, v in get_pii_payloads().items():
        add_str(f"pii_{k}", v["text"])
    for k, v in get_ocr_payloads().items():
        add_str(f"ocr_{k}_q", v["query"])
        add_strs(f"ocr_{k}_c", v["candidates"])
    for k, v in get_rag_payloads().items():
        add_str(f"rag_{k}", v["text"])

    with open(out_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
