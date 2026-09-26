import math
import re

_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|\d+")
_STOP = {
    "the",
    "and",
    "for",
    "from",
    "with",
    "self",
    "none",
    "true",
    "false",
    "return",
    "def",
    "class",
    "import",
    "if",
    "else",
    "elif",
    "while",
    "try",
    "except",
    "pass",
    "this",
    "const",
    "let",
    "var",
    "function",
}


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for match in _TOKEN.findall(text):
        pieces = re.sub(r"([a-z])([A-Z])", r"\1 \2", match).replace("_", " ").lower().split()
        tokens.extend(piece for piece in pieces if len(piece) > 1 and piece not in _STOP)
    return tokens


class TfidfIndex:
    def __init__(self) -> None:
        self._docs: list[dict[str, float]] = []
        self._idf: dict[str, float] = {}

    def fit(self, texts: list[str]) -> None:
        bags = [tokenize(text) for text in texts]
        df: dict[str, int] = {}
        for bag in bags:
            for token in set(bag):
                df[token] = df.get(token, 0) + 1
        total = max(len(bags), 1)
        self._idf = {token: math.log((1 + total) / (1 + count)) + 1 for token, count in df.items()}
        self._docs = [self._vector(bag) for bag in bags]

    def transform(self, text: str) -> dict[str, float]:
        return self._vector(tokenize(text))

    def search(self, text: str, limit: int) -> list[tuple[int, float]]:
        query = self.transform(text)
        if not query:
            return []
        scored = [(index, _cosine(query, doc)) for index, doc in enumerate(self._docs)]
        scored = [item for item in scored if item[1] > 0]
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:limit]

    def _vector(self, bag: list[str]) -> dict[str, float]:
        counts: dict[str, int] = {}
        for token in bag:
            counts[token] = counts.get(token, 0) + 1
        total = max(len(bag), 1)
        return {
            token: (count / total) * self._idf.get(token, 0.0)
            for token, count in counts.items()
            if self._idf.get(token, 0.0)
        }


def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if len(left) > len(right):
        left, right = right, left
    dot = sum(value * right.get(key, 0.0) for key, value in left.items())
    if dot == 0:
        return 0.0
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)
