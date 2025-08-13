"""Text processing service using Unstructured for content parsing and cleaning."""

import re
import asyncio
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor

from unstructured.partition.auto import partition
from unstructured.cleaners.core import clean_extra_whitespace, clean_non_ascii_chars
from unstructured.staging.base import convert_to_dict

from app.core.logging import get_logger

logger = get_logger(__name__)


class TextProcessingService:
    """Service for processing and cleaning text content from SolarWinds solutions."""
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)
        
    async def process_solution_content(self, content: str, title: str = "") -> str:
        """
        Process and clean solution content.
        
        Args:
            content: Raw solution content from SolarWinds
            title: Solution title for context
            
        Returns:
            Cleaned and processed content
        """
        if not content or not content.strip():
            return ""
        
        try:
            # Run CPU-intensive processing in thread pool
            loop = asyncio.get_event_loop()
            cleaned_content = await loop.run_in_executor(
                self.executor,
                self._process_content_sync,
                content,
                title
            )
            
            logger.debug(f"Processed content", extra={
                "original_length": len(content),
                "processed_length": len(cleaned_content),
                "title": title[:50] + "..." if len(title) > 50 else title,
            })
            
            return cleaned_content
            
        except Exception as e:
            logger.error(f"Error processing content: {str(e)}", extra={
                "title": title,
                "content_length": len(content),
            })
            # Fallback to basic cleaning if Unstructured fails
            return self._basic_text_cleaning(content)
    
    def _process_content_sync(self, content: str, title: str = "") -> str:
        """
        Synchronous content processing using Unstructured.
        
        Args:
            content: Raw content to process
            title: Title for context
            
        Returns:
            Cleaned content
        """
        try:
            # Try to partition the content using Unstructured
            elements = partition(text=content)
            
            # Convert elements to text and clean
            processed_parts = []
            for element in elements:
                element_text = str(element).strip()
                if element_text:
                    # Clean whitespace and non-ASCII characters
                    cleaned = clean_extra_whitespace(element_text)
                    cleaned = clean_non_ascii_chars(cleaned)
                    processed_parts.append(cleaned)
            
            # Join all parts with proper spacing
            processed_content = "\n\n".join(processed_parts)
            
            # Apply additional custom cleaning
            processed_content = self._apply_custom_cleaning(processed_content)
            
            return processed_content.strip()
            
        except Exception as e:
            logger.warning(f"Unstructured processing failed, using fallback: {str(e)}")
            return self._basic_text_cleaning(content)
    
    def _apply_custom_cleaning(self, content: str) -> str:
        """
        Apply custom cleaning rules specific to SolarWinds content.
        
        Args:
            content: Content to clean
            
        Returns:
            Cleaned content
        """
        # Remove excessive newlines
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # Remove common SolarWinds metadata patterns
        content = re.sub(r'Created by:.*?\n', '', content, flags=re.IGNORECASE)
        content = re.sub(r'Last updated:.*?\n', '', content, flags=re.IGNORECASE)
        content = re.sub(r'Solution ID:.*?\n', '', content, flags=re.IGNORECASE)
        content = re.sub(r'Category:.*?\n', '', content, flags=re.IGNORECASE)
        
        # Remove HTML-like tags if any remain
        content = re.sub(r'<[^>]+>', '', content)
        
        # Clean up common formatting artifacts
        content = re.sub(r'\s*\|\s*', ' | ', content)  # Fix table separators
        content = re.sub(r'_{3,}', '---', content)     # Fix underline separators
        content = re.sub(r'-{4,}', '---', content)     # Fix dash separators
        
        # Remove excessive spaces
        content = re.sub(r' {3,}', '  ', content)
        
        # Normalize step numbering
        content = re.sub(r'^\s*(\d+)[\.\)]\s+', r'\1. ', content, flags=re.MULTILINE)
        
        return content
    
    def _basic_text_cleaning(self, content: str) -> str:
        """
        Basic text cleaning fallback when Unstructured is not available.
        
        Args:
            content: Content to clean
            
        Returns:
            Cleaned content
        """
        # Remove HTML tags
        content = re.sub(r'<[^>]+>', '', content)
        
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r'\n\s*\n', '\n\n', content)
        
        # Remove non-printable characters but keep useful ones
        content = re.sub(r'[^\x20-\x7E\n\r\t]', '', content)
        
        return content.strip()
    
    async def extract_keywords(self, content: str, max_keywords: int = 10) -> List[str]:
        """
        Extract keywords from solution content.
        
        Args:
            content: Content to analyze
            max_keywords: Maximum number of keywords to return
            
        Returns:
            List of extracted keywords
        """
        if not content:
            return []
        
        try:
            # Simple keyword extraction based on frequency and relevance
            # This is a basic implementation - could be enhanced with NLP libraries
            
            # Split into words and clean
            words = re.findall(r'\b[a-zA-Z]{3,}\b', content.lower())
            
            # Common stop words to filter out
            stop_words = {
                'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'her', 'was', 'one',
                'our', 'had', 'have', 'has', 'will', 'this', 'that', 'with', 'from', 'they', 'she',
                'been', 'said', 'each', 'which', 'their', 'time', 'more', 'very', 'when', 'come',
                'may', 'use', 'your', 'way', 'about', 'many', 'then', 'them', 'these', 'some',
                'what', 'would', 'make', 'like', 'into', 'him', 'could', 'two', 'first', 'after',
                'back', 'other', 'many', 'than', 'then', 'them', 'these', 'some', 'how', 'its'
            }
            
            # Count word frequencies
            word_counts = {}
            for word in words:
                if word not in stop_words and len(word) > 2:
                    word_counts[word] = word_counts.get(word, 0) + 1
            
            # Sort by frequency and return top keywords
            keywords = sorted(word_counts.keys(), key=lambda w: word_counts[w], reverse=True)
            
            return keywords[:max_keywords]
            
        except Exception as e:
            logger.error(f"Error extracting keywords: {str(e)}")
            return []
    
    async def create_summary(self, content: str, max_length: int = 200) -> str:
        """
        Create a summary of the solution content.
        
        Args:
            content: Content to summarize
            max_length: Maximum length of summary
            
        Returns:
            Content summary
        """
        if not content:
            return ""
        
        try:
            # Simple extractive summarization
            sentences = re.split(r'[.!?]+', content)
            sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
            
            if not sentences:
                return content[:max_length] + "..." if len(content) > max_length else content
            
            # Take first few sentences up to max_length
            summary = ""
            for sentence in sentences:
                if len(summary + sentence) <= max_length:
                    summary += sentence + ". "
                else:
                    break
            
            return summary.strip()
            
        except Exception as e:
            logger.error(f"Error creating summary: {str(e)}")
            return content[:max_length] + "..." if len(content) > max_length else content
    
    async def validate_content(self, content: str) -> Dict[str, Any]:
        """
        Validate and analyze content quality.
        
        Args:
            content: Content to validate
            
        Returns:
            Dictionary with validation results
        """
        if not content:
            return {
                "is_valid": False,
                "issues": ["Content is empty"],
                "word_count": 0,
                "estimated_reading_time": 0,
            }
        
        issues = []
        
        # Check minimum length
        if len(content.strip()) < 50:
            issues.append("Content is too short")
        
        # Check for meaningful content
        word_count = len(content.split())
        if word_count < 10:
            issues.append("Content has too few words")
        
        # Check for excessive repetition
        words = content.lower().split()
        unique_words = set(words)
        if len(unique_words) / len(words) < 0.3:  # Less than 30% unique words
            issues.append("Content appears to be repetitive")
        
        # Estimate reading time (average 200 words per minute)
        reading_time = max(1, word_count / 200)
        
        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "word_count": word_count,
            "unique_word_ratio": len(unique_words) / len(words) if words else 0,
            "estimated_reading_time": reading_time,
            "character_count": len(content),
        }
    
    async def batch_process_solutions(
        self, 
        solutions: List[Dict[str, Any]], 
        batch_size: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Process multiple solutions in batches.
        
        Args:
            solutions: List of solution dictionaries
            batch_size: Number of solutions to process concurrently
            
        Returns:
            List of processed solutions
        """
        processed_solutions = []
        
        for i in range(0, len(solutions), batch_size):
            batch = solutions[i:i + batch_size]
            
            # Process batch concurrently
            tasks = [
                self._process_single_solution(solution)
                for solution in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Error processing solution in batch: {str(result)}")
                else:
                    processed_solutions.append(result)
        
        logger.info(f"Processed {len(processed_solutions)} solutions")
        return processed_solutions
    
    async def _process_single_solution(self, solution: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single solution."""
        content = solution.get("content", "")
        title = solution.get("title", "")
        
        # Process content
        processed_content = await self.process_solution_content(content, title)
        
        # Extract metadata
        keywords = await self.extract_keywords(processed_content)
        summary = await self.create_summary(processed_content)
        validation = await self.validate_content(processed_content)
        
        # Return enhanced solution
        return {
            **solution,
            "processed_content": processed_content,
            "keywords": keywords,
            "summary": summary,
            "content_validation": validation,
        }


# Global service instance
text_processing_service = TextProcessingService()