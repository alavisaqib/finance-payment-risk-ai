"""Local lexical RAG: stable citations, rank-then-pack, and corpus versioning."""
import hashlib
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .config import ROOT

class KnowledgeBase:
    def __init__(self):
        self.chunks = []
        for path in sorted((ROOT / 'data/knowledge').glob('*.md')):
            for index, paragraph in enumerate(path.read_text(encoding='utf-8').split('\n\n')):
                paragraph = paragraph.strip()
                # Headings and provenance notices are metadata, not supporting evidence.
                if len(paragraph) >= 100 and not paragraph.startswith('#'):
                    self.chunks.append({'id': f'{path.stem}:{index + 1}', 'source': path.name,
                                        'text': paragraph, 'sha256': hashlib.sha256(paragraph.encode()).hexdigest()})
        if not self.chunks:
            raise ValueError('Knowledge base is empty')
        self.version = hashlib.sha256(json.dumps(self.chunks, sort_keys=True).encode()).hexdigest()
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
        self.matrix = self.vectorizer.fit_transform([item['text'] for item in self.chunks])

    def search(self, query, top_k=4, budget=1600):
        scores = cosine_similarity(self.vectorizer.transform([query]), self.matrix).ravel()
        found, used, seen = [], 0, set()
        for index in scores.argsort()[::-1]:
            if scores[index] <= 0:
                continue
            item = dict(self.chunks[index], score=round(float(scores[index]), 5))
            size = len(json.dumps(item, ensure_ascii=False).encode('utf-8'))
            if item['sha256'] in seen or used + size > budget:
                continue
            found.append(item)
            used += size
            seen.add(item['sha256'])
            if len(found) == top_k:
                break
        return found
