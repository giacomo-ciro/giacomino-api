import uuid
from typing import Optional

import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings
from together import Together

from app.config import AppConfig, Secrets
from app.utils.logger import MyLogger


class TogetherEmbeddingFunction(EmbeddingFunction):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = Together(api_key=api_key)
        self._model = model

    def __call__(self, input: Documents) -> Embeddings:
        response = self._client.embeddings.create(model=self._model, input=input)
        return [item.embedding for item in response.data]


class DocumentStore:
    COLLECTION_NAME = "documents"

    def __init__(self, secrets: Secrets, config: AppConfig, logger: Optional[MyLogger] = None) -> None:
        self._logger = logger
        self._ef = TogetherEmbeddingFunction(
            api_key=secrets.TOGETHER_API_KEY,
            model=config.embedding_model,
        )
        client = chromadb.PersistentClient(path=config.chroma_db_path)
        self._collection = client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            embedding_function=self._ef,
        )

    def seed_from_file(self, path: str) -> None:
        try:
            with open(path, encoding="utf-8") as f:
                chunks = [c.strip() for c in f.read().split("---") if c.strip()]
        except Exception as e:
            if self._logger:
                self._logger.warning(f"Document seeding failed reading file: {e}")
            return

        existing = {doc["content"] for doc in self.get_all()}
        new_chunks = [c for c in chunks if c not in existing]

        if new_chunks:
            try:
                ids = [str(uuid.uuid4()) for _ in new_chunks]
                self._collection.add(documents=new_chunks, ids=ids)
            except Exception as e:
                if self._logger:
                    self._logger.warning(f"Document seeding failed adding to index: {e}")

        if self._logger:
            self._logger.info(
                f"Document seeding: {len(new_chunks)} new, {len(chunks) - len(new_chunks)} already indexed"
            )

    def query(self, text: str, top_k: int) -> list[str]:
        count = self._collection.count()
        if count == 0:
            return []
        results = self._collection.query(query_texts=[text], n_results=min(top_k, count))
        return results["documents"][0] if results["documents"] else []

    def get_all(self) -> list[dict]:
        result = self._collection.get()
        return [
            {"id": id_, "content": doc, "metadata": meta or {}}
            for id_, doc, meta in zip(
                result["ids"], result["documents"], result["metadatas"]
            )
        ]

    def add(self, content: str, metadata: dict) -> str:
        id_ = str(uuid.uuid4())
        # ChromaDB requires None (not {}) for empty metadata
        self._collection.add(documents=[content], ids=[id_], metadatas=[metadata or None])
        return id_

    def update(self, id_: str, content: str, metadata: Optional[dict]) -> None:
        kwargs: dict = {"ids": [id_], "documents": [content]}
        if metadata is not None:
            kwargs["metadatas"] = [metadata or None]
        self._collection.update(**kwargs)

    def delete(self, id_: str) -> None:
        self._collection.delete(ids=[id_])

    def get_by_id(self, id_: str) -> Optional[dict]:
        result = self._collection.get(ids=[id_])
        if not result["ids"]:
            return None
        return {
            "id": result["ids"][0],
            "content": result["documents"][0],
            "metadata": result["metadatas"][0],
        }
