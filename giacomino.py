import os
import json
import time
import logging
from typing import List, Dict, Any
from pathlib import Path
from together import Together
import faiss
import numpy as np

logger = logging.getLogger(__name__)

class Giacomino:
    def __init__(
        self,
        model_text="meta-llama/Llama-3.2-3B-Instruct-Turbo",
        model_embeddings="BAAI/bge-large-en-v1.5",
    ):
        self.version = "1.0.0"
        self.together_api_key = os.getenv('TOGETHER_API_KEY')
        if not self.together_api_key:
            raise ValueError("TOGETHER_API_KEY environment variable not set")

        self.together = Together(api_key=self.together_api_key)
        self.model_text = model_text
        self.model_embeddings = model_embeddings

        self.index_file = "faiss_index.index"
        self.doc_file = "faiss_docs.pkl"

        self._load_prompts()
        self._load_documents()

    def _load_prompts(self):
        path_to_sys = Path("./system.txt")
        assert path_to_sys.exists()
        with open(path_to_sys, "r") as f:
            self.system_prompt = f.read()
        logger.info("Loaded system prompt")

    def _embed_texts(self, texts: List[str]) -> np.ndarray:
        response = self.together.embeddings.create(
            model=self.model_embeddings,
            input=texts
        )
        embeddings = [item.embedding for item in response.data]
        return np.array(embeddings).astype('float32')

    def _load_documents(self):
        docs_file = Path("documents.txt")
        assert docs_file.exists()
        with open(docs_file, "r", encoding="utf-8") as f:
            self.documents = [line.strip() for line in f if line.strip()]

        embeddings = self._embed_texts(self.documents)
        self.index = faiss.IndexFlatL2(embeddings.shape[1])
        self.index.add(embeddings)
        faiss.write_index(self.index, self.index_file)

        logger.info(f"Loaded {len(self.documents)} documents into FAISS index")

    def retrieve_context(self, query: str, k: int = 3) -> List[str]:
        query_vec = self._embed_texts([query])
        distances, indices = self.index.search(query_vec, k)
        return [self.documents[i] for i in indices[0] if i < len(self.documents)]

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
        context_docs = self.retrieve_context(user_message, k=3)
        context = "\n".join(context_docs) if context_docs else "No specific context available."
        print(f"Retrieved documents:\n{context}\n"+"-"*20)
        
        # Format prompt
        system_prompt = self.system_prompt.format(
            context=context,
            date=time.strftime("%B %-d, %Y")
        )

        # Get model response
        response = self._send_chat_completion_request(system_prompt, messages)

        # Save messages
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        messages.insert(0, {"timestamp":timestamp})
        messages.append({"role":"assistant", "content":response})
        self._save_messages_to_disk(
            messages
        )
        return response


    def _save_messages_to_disk(self, messages, filepath="saved_messages.jsonl"):
        print(messages)
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(messages) + "\n")


    def get_available_docs(self) -> Dict[str, Any]:
        try:
            return {
                "total_documents": len(self.documents),
                "status": "available" if self.documents else "empty"
            }
        except Exception as e:
            logger.error(f"Error getting docs info: {e}")
            return {"total_documents": 0, "status": "error"}
