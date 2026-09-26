import json
from dataclasses import dataclass
from pathlib import Path

from clean_ia.index.embeddings import TfidfIndex

DEFAULT_DATASET = Path("training") / "examples.jsonl"
OUTPUT_LIMIT = 2000


@dataclass(frozen=True)
class TrainExample:
    instruction: str
    output: str


def dataset_path(path: Path | None = None) -> Path:
    return path or DEFAULT_DATASET


def load_examples(path: Path | None = None) -> list[TrainExample]:
    file = dataset_path(path)
    if not file.is_file():
        return []
    examples = []
    for line in file.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        data = json.loads(raw)
        instruction = str(data.get("instruction") or "").strip()
        output = str(data.get("output") or "").strip()
        if instruction and output:
            examples.append(TrainExample(instruction, output))
    return examples


def add_example(instruction: str, output: str, path: Path | None = None) -> Path:
    file = dataset_path(path)
    file.parent.mkdir(parents=True, exist_ok=True)
    record = {"instruction": instruction.strip(), "output": output.strip()}
    if not record["instruction"] or not record["output"]:
        raise ValueError("instruction et output sont obligatoires.")
    with file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return file


def relevant_examples(query: str, examples: list[TrainExample], limit: int = 3) -> list[TrainExample]:
    if not examples or not query.strip():
        return examples[:limit]
    index = TfidfIndex()
    index.fit([item.instruction for item in examples])
    hits = index.search(query, limit)
    if not hits:
        return examples[:limit]
    return [examples[position] for position, _score in hits]


def format_examples(examples: list[TrainExample]) -> str:
    if not examples:
        return ""
    blocks = ["Exemples d'entraînement à imiter :"]
    for number, item in enumerate(examples, start=1):
        output = item.output if len(item.output) <= OUTPUT_LIMIT else item.output[:OUTPUT_LIMIT] + "…"
        blocks.append(f"### Exemple {number}\nDemande :\n{item.instruction}\nRéponse attendue :\n{output}")
    return "\n\n".join(blocks)
