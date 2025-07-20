import os
import json
import time
from typing import List, Dict, Any
from pathlib import Path
from together import Together
import faiss
import numpy as np

from utils import MyLogger

class Giacomino:
    version = "1.0.0"
    def __init__(
        self,
        logger:MyLogger,
        model_text:str="meta-llama/Llama-3.2-3B-Instruct-Turbo",
        model_embeddings:str="BAAI/bge-large-en-v1.5",
    ):  
        self.logger = logger
        self.together_api_key = os.getenv('TOGETHER_API_KEY')
        if not self.together_api_key:
            self.logger.error("TOGETHER_API_KEY environment variable not set")
            exit()

        self.together = Together(api_key=self.together_api_key)
        self.model_text = model_text
        self.model_embeddings = model_embeddings

        self.index_file = "faiss_index.index"
        self.doc_file = "faiss_docs.pkl"

        self.top_k = int(os.environ.get("RETRIEVE_TOP_K"))
        self._load_prompts()
        self._load_documents()

    def _load_prompts(self):
        path_to_sys = Path("./system.txt")
        assert path_to_sys.exists()
        with open(path_to_sys, "r") as f:
            self.system_prompt = f.read()
        self.logger.info(f"System prompt loaded:\n\n---\n{self.system_prompt}\n---\n")

    def _embed_texts(self, texts: List[str]) -> np.ndarray:
        response = self.together.embeddings.create(
            model=self.model_embeddings,
            input=texts
        )
        embeddings = [item.embedding for item in response.data]
        return np.array(embeddings).astype('float32')

    def _load_documents(self):
        self.logger.info("Loading docs...")
        docs_file = Path("documents.txt")
        assert docs_file.exists()
        with open(docs_file, "r", encoding="utf-8") as f:
            content = f.read()
            # Split by "---" and strip whitespace
            self.documents = [chunk.strip() for chunk in content.split("---") if chunk.strip()]
        if os.getenv("FLASK_ENV") != "production":
            self.documents = self.documents[:]
        
        self.logger.info("Embedding docs...")
        embeddings = self._embed_texts(self.documents)
        
        self.logger.info("Writing index...")
        self.index = faiss.IndexFlatL2(embeddings.shape[1])
        self.index.add(embeddings)
        faiss.write_index(self.index, self.index_file)

        self.logger.info(f"Loaded {len(self.documents)} documents into FAISS index")

    def retrieve_context(self, query: str) -> List[str]:
        query_vec = self._embed_texts([query])
        distances, indices = self.index.search(query_vec, self.top_k)
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
        context_docs = self.retrieve_context(user_message)
        context = "\n".join(context_docs) if context_docs else "No specific context available."
        
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
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(messages) + "\n")


    def get_available_docs(self) -> Dict[str, Any]:
        try:
            return {
                "total_documents": len(self.documents),
                "status": "available" if self.documents else "empty"
            }
        except Exception as e:
            self.logger.info(f"Error getting docs info: {e}")
            return {"total_documents": 0, "status": "error"}
