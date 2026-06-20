"""
RAG (Retrieval Augmented Generation) module
Enables semantic search and Q&A over building regulations
"""
import os
import json
from typing import List, Optional, Tuple
import numpy as np
from models import RAGQuery


class KnowledgeBase:
    """
    Simple knowledge base with building regulations and standards
    In production, this would be loaded from a vector database
    """
    
    # Sample building regulations and standards
    REGULATIONS = [
        {
            "id": "reg_001",
            "title": "Structural Safety Requirements",
            "content": "All structural elements must meet minimum safety factors. Load-bearing walls must be designed for 1.5x design load. Foundations must be checked for settlement and bearing capacity.",
            "category": "structural",
            "source": "EU Building Standards EN 1990"
        },
        {
            "id": "reg_002",
            "title": "Water Tightness Standards",
            "content": "Buildings must be water-tight at all penetrations. Roofs must have minimum pitch of 10 degrees or use proper waterproofing. Basements require damp-proof membranes.",
            "category": "moisture",
            "source": "ISO 7783 - Water Tightness"
        },
        {
            "id": "reg_003",
            "title": "Electrical Safety Codes",
            "content": "All electrical installations must comply with IEC 60364. Protection against electric shock is mandatory. Grounding systems must be verified annually. Circuits must be protected with appropriate breakers.",
            "category": "electrical",
            "source": "IEC 60364"
        },
        {
            "id": "reg_004",
            "title": "Crack Assessment Guidelines",
            "content": "Cracks less than 0.3mm are typically cosmetic. Cracks 0.3-1mm require monitoring. Cracks greater than 1mm require structural assessment. Vertical cracks in load-bearing walls are more critical than horizontal cracks.",
            "category": "structural",
            "source": "BS 8103-1"
        },
        {
            "id": "reg_005",
            "title": "Mold and Moisture Prevention",
            "content": "Indoor humidity should be maintained between 30-50%. Adequate ventilation is required in all rooms. Condensation should be eliminated within 1 hour. Mold prevention requires proper insulation and moisture control.",
            "category": "health",
            "source": "WHO Guidelines"
        },
        {
            "id": "reg_006",
            "title": "Inspection Frequency Requirements",
            "content": "Buildings should be inspected every 2-3 years. High-risk buildings require annual inspection. After repairs, follow-up inspection within 30 days is required. Critical defects require emergency inspection.",
            "category": "maintenance",
            "source": "ISO 13822"
        }
    ]
    
    def __init__(self):
        """Initialize knowledge base"""
        self.regulations = self.REGULATIONS
        self.embeddings = self._create_embeddings()
    
    def _create_embeddings(self) -> List[np.ndarray]:
        """
        Create simple text embeddings (in production use proper embedding models)
        
        Returns:
            List of embeddings
        """
        embeddings = []
        for reg in self.regulations:
            # Simple embedding: create a feature vector from word frequencies
            text = (reg["title"] + " " + reg["content"]).lower()
            embedding = self._simple_embedding(text)
            embeddings.append(embedding)
        
        return embeddings
    
    def _simple_embedding(self, text: str) -> np.ndarray:
        """
        Create simple embedding (in production use OpenAI embeddings or similar)
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        # Simple TF-IDF style embedding
        words = set(text.split())
        
        # Create feature vector based on keywords
        keywords = {
            "structural": 1, "load-bearing": 1, "foundation": 1, "crack": 0.5,
            "water": 1, "moisture": 1, "leak": 0.5, "damp": 0.5,
            "electrical": 1, "safety": 0.5, "hazard": 0.5,
            "inspection": 1, "maintenance": 0.5,
            "compliance": 0.5, "standard": 0.5
        }
        
        vector = np.zeros(len(keywords))
        for i, keyword in enumerate(keywords.keys()):
            if keyword in text:
                vector[i] = keywords[keyword]
        
        return vector
    
    def search(self, query: str, top_k: int = 3) -> List[dict]:
        """
        Search knowledge base for relevant regulations
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of relevant regulations
        """
        query_embedding = self._simple_embedding(query.lower())
        
        # Calculate similarity scores
        scores = []
        for i, embedding in enumerate(self.embeddings):
            similarity = np.dot(query_embedding, embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(embedding) + 1e-10
            )
            scores.append((similarity, i))
        
        # Sort by similarity and return top_k
        scores.sort(reverse=True)
        results = [self.regulations[idx] for _, idx in scores[:top_k]]
        
        return results


class RAGEngine:
    """
    RAG engine for Q&A over regulations and building knowledge
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize RAG engine
        
        Args:
            api_key: OpenAI API key
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.knowledge_base = KnowledgeBase()
        self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize LLM client"""
        try:
            from openai import OpenAI
            self.llm_client = OpenAI(api_key=self.api_key) if self.api_key else None
        except ImportError:
            self.llm_client = None
    
    def answer_question(self, query: RAGQuery) -> dict:
        """
        Answer question using RAG approach
        
        Args:
            query: RAG query
            
        Returns:
            Dict with answer, sources, and confidence
        """
        # Retrieve relevant regulations
        retrieved_docs = self.knowledge_base.search(query.question, top_k=3)
        
        if not retrieved_docs:
            return {
                "question": query.question,
                "answer": "No relevant regulations found in knowledge base.",
                "sources": [],
                "confidence": 0.0
            }
        
        # Prepare context from retrieved documents
        context = self._prepare_context(retrieved_docs)
        
        # Generate answer using LLM or fallback
        if self.llm_client:
            answer = self._generate_answer_with_llm(query.question, context)
        else:
            answer = self._generate_answer_heuristic(query.question, retrieved_docs)
        
        return {
            "question": query.question,
            "answer": answer,
            "sources": [
                {
                    "title": doc["title"],
                    "source": doc["source"],
                    "category": doc["category"]
                }
                for doc in retrieved_docs
            ],
            "confidence": 0.85
        }
    
    def _prepare_context(self, docs: List[dict]) -> str:
        """
        Prepare context from retrieved documents
        
        Args:
            docs: Retrieved documents
            
        Returns:
            Context string
        """
        context = "Based on the following building standards:\n\n"
        for doc in docs:
            context += f"- {doc['title']} ({doc['source']}):\n"
            context += f"  {doc['content']}\n\n"
        
        return context
    
    def _generate_answer_with_llm(self, question: str, context: str) -> str:
        """
        Generate answer using LLM
        
        Args:
            question: User question
            context: Retrieved context
            
        Returns:
            Generated answer
        """
        try:
            prompt = f"""{context}

Question: {question}

Provide a clear, accurate answer based on the standards above. Be specific and reference the relevant standard where applicable."""
            
            response = self.llm_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert building inspector assistant with deep knowledge of building codes and regulations."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            print(f"LLM generation failed: {e}")
            return self._generate_answer_heuristic(question, [])
    
    def _generate_answer_heuristic(self, question: str, docs: List[dict]) -> str:
        """
        Generate answer using heuristic method
        
        Args:
            question: User question
            docs: Retrieved documents (unused in heuristic)
            
        Returns:
            Heuristic answer
        """
        question_lower = question.lower()
        
        if "compliant" in question_lower or "comply" in question_lower:
            return (
                "To determine compliance, verify that your project meets the relevant "
                "building standards listed in the sources. Consider conducting a professional "
                "inspection to identify any defects or non-compliance issues."
            )
        elif "safe" in question_lower or "safety" in question_lower:
            return (
                "Safety requirements vary by building type and jurisdiction. "
                "Consult the relevant building codes and conduct professional inspections "
                "to ensure all safety standards are met."
            )
        elif "crack" in question_lower:
            return (
                "Cracks should be assessed based on their size and location. "
                "Small cracks (< 0.3mm) are typically cosmetic, while larger cracks may indicate "
                "structural issues and should be evaluated by a professional engineer."
            )
        elif "water" in question_lower or "leak" in question_lower or "moisture" in question_lower:
            return (
                "Water tightness is critical for building longevity. All penetrations must be sealed, "
                "proper drainage must be maintained, and damp-proof membranes should be installed where needed."
            )
        elif "inspection" in question_lower:
            return (
                "Regular inspections are essential for building maintenance. Most buildings should be "
                "inspected every 2-3 years, with high-risk buildings requiring annual inspections."
            )
        else:
            return (
                "For specific compliance questions, please consult with a professional building inspector "
                "or engineer who can evaluate your specific situation against applicable building codes."
            )

