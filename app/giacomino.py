import hashlib
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

import chromadb
import numpy as np
import yaml
from together import Together


class Giacomino:
    version = "1.0.0"

    def __init__(
        self,
        logger: logging.Logger,
        together_api_key: str,
        chroma_persist_dir: str,
        model_text: str = "meta-llama/Llama-3.2-3B-Instruct-Turbo",
        model_embeddings: str = "BAAI/bge-large-en-v1.5",
        top_k: int = 10,
    ):
        self.logger = logger
        if not together_api_key:
            self.logger.error("TOGETHER_API_KEY environment variable not set")
            sys.exit()
        self.together = Together(api_key=together_api_key)
        self.model_text = model_text
        self.model_embeddings = model_embeddings
        self.top_k = top_k

        self.chroma_client = chromadb.PersistentClient(path=chroma_persist_dir)
        self.collection = self.chroma_client.get_or_create_collection(
            name="documents", embedding_function=None
        )

        self._load_prompts()
        self._load_documents()

    def _load_prompts(self):
        path_to_sys = Path("prompts/system.txt")
        assert path_to_sys.exists()
        with open(path_to_sys, "r") as f:
            self.system_prompt = f.read()
        self.logger.info(f"System prompt loaded from {path_to_sys}")

    def _embed_texts(self, texts: list[str]) -> np.ndarray:
        response = self.together.embeddings.create(
            model=self.model_embeddings, input=texts
        )
        embeddings = [item.embedding for item in response.data]
        return np.array(embeddings).astype("float32")

    def _chunk_id(self, text: str) -> str:
        return f"chunk_{hashlib.sha256(text.encode()).hexdigest()[:12]}"

    def _load_documents(self):
        self.logger.info("Loading docs...")
        docs_file = Path("documents/documents.yaml")
        assert docs_file.exists()
        with open(docs_file, "r", encoding="utf-8") as f:
            self.documents = [chunk.strip() for chunk in yaml.safe_load(f)]

        current = {self._chunk_id(c): c for c in self.documents}
        existing_ids = set(self.collection.get()["ids"])
        new_ids = set(current) - existing_ids
        stale_ids = existing_ids - set(current)

        if stale_ids:
            self.logger.info(f"Removing {len(stale_ids)} stale chunks from Chroma...")
            self.collection.delete(ids=list(stale_ids))

        if new_ids:
            self.logger.info(f"Embedding {len(new_ids)} new/changed chunks...")
            new_docs = [current[i] for i in new_ids]
            embeddings = self._embed_texts(new_docs)
            self.collection.add(
                ids=list(new_ids),
                embeddings=embeddings.tolist(),
                documents=new_docs,
            )

        self.logger.info(
            f"Loaded {len(self.documents)} documents into Chroma collection"
        )

    def retrieve_context(self, query: str) -> list[str]:
        query_vec = self._embed_texts([query])
        results = self.collection.query(
            query_embeddings=query_vec.tolist(), n_results=self.top_k
        )
        return results["documents"][0]

    def _send_chat_completion_request(self, system_prompt, messages) -> str:
        for mex in messages:
            assert mex["role"] in {"system", "assistant", "user"}

        messages = [
            {"role": "system", "content": system_prompt},
        ] + messages

        response = self.together.chat.completions.create(
            model=self.model_text,
            messages=messages,
            max_tokens=512,
            temperature=0.7,
            top_p=0.9,
            stream=False,
        )

        return response.choices[0].message.content.strip()

    def generate_response(self, messages: list) -> str:
        assert isinstance(messages, list) and messages
        assert messages[-1]["role"] == "user"

        # User message
        user_message = messages[-1]["content"]

        # Retrieve context
        context_docs = self.retrieve_context(user_message)
        context = (
            "\n".join(context_docs)
            if context_docs
            else "No specific context available."
        )

        # Format prompt
        system_prompt = self.system_prompt.format(
            context=context, date=time.strftime("%B %-d, %Y")
        )

        # Get model response
        response = self._send_chat_completion_request(system_prompt, messages)

        # Save messages
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        messages.insert(0, {"timestamp": timestamp})
        messages.append({"role": "assistant", "content": response})
        self._save_messages_to_disk(messages)
        return response

    def _save_messages_to_disk(self, messages, filepath="dump/saved_messages.jsonl"):
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(messages) + "\n")

    def get_available_docs(self) -> dict[str, Any]:
        try:
            return {
                "quantity": len(self.documents),
                "status": "available" if self.documents else "empty",
            }
        except Exception as e:  # noqa: BLE001 — intentional safety net, never surfaces internals to the caller
            self.logger.info(f"Error getting docs info: {e}")
            return {"quantity": 0, "status": "error"}
