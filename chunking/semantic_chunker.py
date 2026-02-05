from .base_chunker import BaseChunker
import nltk
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer


class ProtonxSemanticChunker(BaseChunker):
    def __init__(self, threshold=0.3, model="keepitreal/vietnamese-sbert"):
        self.threshold = threshold
        self.model = model

        nltk.download("punkt_tab", quiet=True)
    
    def embed_function(self, sentences):
        encoder = self.model if isinstance(self.model, SentenceTransformer) else SentenceTransformer(self.model)
        return encoder.encode(sentences)
    
        
    def split_text(self, text):
        sentences = nltk.sent_tokenize(text)  # Extract sentences
        sentences = [item for item in sentences if item and item.strip()]
        if not len(sentences):
            return []

        vectors = self.embed_function(sentences)

        similarities = cosine_similarity(vectors)

        chunks = [[sentences[0]]]

        for i in range(1, len(sentences)):
            sim_score = similarities[i-1, i]

            if sim_score >= self.threshold:
                chunks[-1].append(sentences[i])
            else:
                chunks.append([sentences[i]])

        return [' '.join(chunk) for chunk in chunks]


