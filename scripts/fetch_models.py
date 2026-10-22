"""Download every model the desk needs. Safe to re-run. Weights stay gitignored."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    models = Path(os.environ.get("FASTEMBED_CACHE_PATH", ROOT / "models"))
    models.mkdir(parents=True, exist_ok=True)
    os.environ["FASTEMBED_CACHE_PATH"] = str(models)
    os.environ.pop("HF_HUB_OFFLINE", None)

    from fastembed import TextEmbedding

    TextEmbedding("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    print("minilm ready")

    from huggingface_hub import hf_hub_download

    nli = models / "nli"
    nli.mkdir(parents=True, exist_ok=True)
    nli_repo = "MoritzLaurer/deberta-v3-xsmall-zeroshot-v1.1-all-33"
    for name in ("config.json", "tokenizer.json", "tokenizer_config.json", "onnx/model_quantized.onnx"):
        hf_hub_download(nli_repo, name, local_dir=str(nli))
    print("nli ready", nli)


if __name__ == "__main__":
    main()
