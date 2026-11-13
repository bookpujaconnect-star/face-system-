"""
Facial Recognition Engine using Deep Learning FaceNet (InceptionResnetV1)
Extracts 512-dimensional L2-normalized embeddings, computes cosine similarity,
and performs rapid Rank-1 student matching with an in-memory vector cache.
"""

import time
import cv2
import torch
import numpy as np
from PIL import Image
from torchvision import transforms
from facenet_pytorch import InceptionResnetV1
from database import get_students_collection

class FaceRecognizer:
    _instance = None

    def __init__(self, device: str = None):
        self.device = torch.device(device or ("mps" if torch.backends.mps.is_available() else "cpu"))
        self.model = InceptionResnetV1(pretrained="vggface2").eval().to(self.device)

        # Standard FaceNet preprocessing pipeline (160x160 RGB, normalized to [-1, 1])
        self.transform = transforms.Compose([
            transforms.Resize((160, 160)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
        ])

        # In-memory embedding cache: {student_id: {"name": ..., "reg_no": ..., "dept": ..., "embedding": np.ndarray}}
        self.enrolled_cache = {}
        self.last_cache_update = 0
        self.reload_cache()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = FaceRecognizer()
        return cls._instance

    def reload_cache(self):
        """Load all enrolled student embeddings from MongoDB Atlas into RAM."""
        try:
            col = get_students_collection()
            cursor = col.find({"is_enrolled": True, "embedding": {"$exists": True, "$ne": None}})
            new_cache = {}
            for doc in cursor:
                s_id = str(doc["_id"])
                emb = np.array(doc["embedding"], dtype=np.float32)
                # Ensure L2 normalized
                norm = np.linalg.norm(emb)
                if norm > 0:
                    emb = emb / norm
                new_cache[s_id] = {
                    "id": s_id,
                    "student_name": doc.get("name", "Unknown"),
                    "reg_no": doc.get("reg_no", ""),
                    "department": doc.get("department", ""),
                    "academic_year": doc.get("academic_year", ""),
                    "status": doc.get("status", "Active"),
                    "photo_url": doc.get("photo_url", ""),
                    "embedding": emb
                }
            self.enrolled_cache = new_cache
            self.last_cache_update = time.time()
            print(f"FaceRecognizer: Cache updated with {len(self.enrolled_cache)} enrolled student embeddings.")
        except Exception as e:
            print(f"Error reloading embedding cache: {e}")

    def extract_embedding(self, face_bgr: np.ndarray) -> np.ndarray:
        """
        Compute 512-d normalized facial embedding from a BGR face crop.
        Returns 512-dim numpy array.
        """
        if face_bgr is None or face_bgr.size == 0:
            return None

        # Convert BGR to RGB PIL Image
        rgb = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        tensor = self.transform(pil_img).unsqueeze(0).to(self.device)

        with torch.no_grad():
            emb = self.model(tensor)
            # Normalize to unit sphere (L2 norm = 1.0)
            emb = torch.nn.functional.normalize(emb, p=2, dim=1)
            emb_np = emb.squeeze(0).cpu().numpy().astype(np.float32)

        return emb_np

    def identify_face(self, face_bgr: np.ndarray, similarity_threshold: float = 0.68) -> dict:
        """
        Identify face against registered students using Cosine Similarity.
        Returns:
            dict containing:
                status: "Identified" or "Unknown"
                similarity_score: float
                student: dict or None
                response_time_ms: float
                rank_matches: list of top candidates
        """
        start_time = time.perf_counter()

        embedding = self.extract_embedding(face_bgr)
        if embedding is None:
            return {
                "status": "Unknown",
                "similarity_score": 0.0,
                "student": None,
                "response_time_ms": 0.0,
                "rank_matches": []
            }

        if not self.enrolled_cache:
            # Try reloading once in case students were just added
            self.reload_cache()

        if not self.enrolled_cache:
            # No enrolled students in database
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return {
                "status": "Unknown",
                "similarity_score": 0.0,
                "student": None,
                "response_time_ms": round(elapsed, 2),
                "rank_matches": []
            }

        # Vectorized Cosine Similarity computation
        student_ids = list(self.enrolled_cache.keys())
        embeddings_matrix = np.stack([self.enrolled_cache[sid]["embedding"] for sid in student_ids])

        # Since embeddings are L2 normalized, cosine similarity is just dot product
        similarities = np.dot(embeddings_matrix, embedding)

        # Sort matches in descending order of similarity
        sorted_indices = np.argsort(similarities)[::-1]
        top_k = min(5, len(sorted_indices))

        rank_matches = []
        for i in range(top_k):
            idx = sorted_indices[i]
            sid = student_ids[idx]
            cand = self.enrolled_cache[sid]
            rank_matches.append({
                "student_id": sid,
                "name": cand["student_name"],
                "reg_no": cand["reg_no"],
                "department": cand["department"],
                "similarity": round(float(similarities[idx]), 4)
            })

        best_idx = sorted_indices[0]
        best_similarity = float(similarities[best_idx])
        best_student = self.enrolled_cache[student_ids[best_idx]]

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        if best_similarity >= similarity_threshold:
            return {
                "status": "Identified",
                "similarity_score": round(best_similarity, 4),
                "student": {
                    "student_id": best_student["id"],
                    "name": best_student["student_name"],
                    "reg_no": best_student["reg_no"],
                    "department": best_student["department"],
                    "academic_year": best_student["academic_year"],
                    "status": best_student["status"],
                    "photo_url": best_student["photo_url"]
                },
                "response_time_ms": round(elapsed_ms, 2),
                "rank_matches": rank_matches
            }
        else:
            return {
                "status": "Unknown",
                "similarity_score": round(best_similarity, 4) if best_similarity > 0 else 0.0,
                "student": None,
                "response_time_ms": round(elapsed_ms, 2),
                "rank_matches": rank_matches
            }
