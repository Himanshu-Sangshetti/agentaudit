"""Free, local baselines for the Guard (tool poisoning) suite. No Clocked or paid API calls.

Arms:
  protectai  protectai/deberta-v3-base-prompt-injection-v2 (Apache-2.0)
  deepset    deepset/deberta-v3-base-injection (MIT)
  keyword    a keyword regex, to show what the task is worth with no model

Long texts are split into 512-token windows (stride 128) and the attack probability is the max
over windows, so a payload at the end of a long description is not truncated away.

Usage: uv run --group bench python bench/baselines/run_guard_baselines.py [--arms protectai deepset keyword]
"""
import argparse
import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODELS = {
    "protectai": ("protectai/deberta-v3-base-prompt-injection-v2", "90c9989b1a342275dd0d1a95aad283c04e075671"),
    "deepset": ("deepset/deberta-v3-base-injection", "80dda00d0b0d9a03917a7685e2ddbcd28e04dbb1"),
}
MAX_TOKENS, STRIDE = 512, 128
KEYWORDS = re.compile(
    r"\b(ignore (all |any |the )?(previous|prior|above)|disregard|do not (tell|mention|inform)|don't (tell|mention)|"
    r"without (telling|informing|notifying)|secretly|<important>|system prompt|before (using|calling) (this|any|the)|"
    r"must (first )?call|~/\.ssh|id_rsa|\.env\b|api[_ ]?key|password|exfiltrat|send (it|them|the contents?) to|"
    r"forward (all|every)|bcc|override|instead of)\b", re.I)


def load(split):
    return [json.loads(l) for l in (ROOT / f"data/built/guard_{split}.jsonl").read_text().splitlines()]


def record(r, p, verdict, ms):
    return {"id": r["id"], "label": r["label"], "source": r["source"], "group": r["group"], "p": p,
            "verdict": verdict, "category": None, "severity": None, "rtt_ms": ms}


def run_model(arm, rows):
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    name, rev = MODELS[arm]
    # Prefer a local copy of the pinned revision (fetched with fetch_models.sh) over the hub cache.
    local = ROOT / "data/raw/models" / name.split("/")[1]
    src, kw = (str(local), {}) if (local / "model.safetensors").exists() else (name, {"revision": rev})
    tok = AutoTokenizer.from_pretrained(src, **kw)
    model = AutoModelForSequenceClassification.from_pretrained(src, **kw).eval()
    # Find the label index meaning "injection" from the model's own config.
    labels = {v.lower(): int(k) for k, v in model.config.id2label.items()}
    pos = next(i for lbl, i in labels.items() if lbl in ("injection", "label_1", "1"))
    torch.set_num_threads(max(1, torch.get_num_threads()))
    out = []
    for r in rows:
        t0 = time.perf_counter()
        enc = tok(r["text"], truncation=True, max_length=MAX_TOKENS, stride=STRIDE,
                  return_overflowing_tokens=True, padding=True, return_tensors="pt")
        enc.pop("overflow_to_sample_mapping", None)
        with torch.no_grad():
            probs = torch.softmax(model(**{k: v for k, v in enc.items() if k in ("input_ids", "attention_mask")}).logits, -1)
        p = float(probs[:, pos].max())
        out.append(record(r, p, "injection" if p >= 0.5 else "benign", (time.perf_counter() - t0) * 1000))
    return out


def run_keyword(rows):
    out = []
    for r in rows:
        t0 = time.perf_counter()
        hit = bool(KEYWORDS.search(r["text"]))
        out.append(record(r, 1.0 if hit else 0.0, "injection" if hit else "benign", (time.perf_counter() - t0) * 1000))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", nargs="+", default=["keyword", "protectai", "deepset"])
    ap.add_argument("--splits", nargs="+", default=["dev", "test"])
    a = ap.parse_args()
    for arm in a.arms:
        for split in a.splits:
            rows = load(split)
            recs = run_keyword(rows) if arm == "keyword" else run_model(arm, rows)
            path = ROOT / f"bench/results/baseline_guard_{split}_{arm}.jsonl"
            path.write_text("\n".join(json.dumps(x) for x in recs))
            print(f"{arm}/{split}: {len(recs)} rows -> {path.relative_to(ROOT)}", flush=True)


if __name__ == "__main__":
    main()
