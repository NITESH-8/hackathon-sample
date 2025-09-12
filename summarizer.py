# from collections import Counter
#
# def summarize_chunk(chunk: list[str]) -> str:
#     """
#     Very lightweight summarizer:
#     - Picks most frequent keywords
#     - Builds 1–2 line description
#     """
#     words = []
#     for line in chunk:
#         for w in line.strip().split():
#             if len(w) > 3:  # ignore very short tokens
#                 words.append(w.lower())
#
#     common = [w for w, _ in Counter(words).most_common(3)]
#     if not common:
#         return "No significant events detected."
#
#     return f"Safe chunk summary: contains {', '.join(common)}."

################################
#
# from collections import Counter
# from itertools import islice
#
# STOPWORDS = {"info", "debug", "trace", "service", "started", "successfully", "process"}
#
# def get_ngrams(words, n=2):
#     return [" ".join(words[i:i+n]) for i in range(len(words)-n+1)]
#
# def summarize_chunk(chunk: list[str]) -> str:
#     words = []
#     for line in chunk:
#         for w in line.strip().split():
#             token = w.lower()
#             if len(token) > 3 and token not in STOPWORDS:
#                 words.append(token)
#
#     if not words:
#         return "No significant events detected."
#
#     # Count single + bigrams
#     bigrams = get_ngrams(words, 2)
#     common = Counter(words + bigrams).most_common(5)
#
#     # Pick top keywords/phrases
#     top_phrases = [w for w, _ in islice(common, 3)]
#
#     # Try to pick a representative line
#     best_line = max(chunk, key=lambda l: sum(1 for t in top_phrases if t in l.lower()), default="")
#
#     if best_line:
#         return f"Safe chunk summary: {best_line.strip()}"
#     else:
#         return f"Safe chunk summary: contains {', '.join(top_phrases)}."
##############################################################################
import re
from collections import Counter
from typing import List, Tuple

STOPWORDS = {
    "info", "debug", "trace", "service", "process", "thread", "started",
    "successfully", "running", "initializing", "completed", "ready", "starting",
    "level", "time", "msg", "version", "worker", "entropy", "systemd", "server",
    "daemon", "manager", "device", "socket", "layer", "subsys", "mounted"
}

TIMESTAMP_PATTERN = re.compile(r"\[.*?\]|\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}")
LOG_ID_PATTERN = re.compile(r"\w+\[\d+\]")

def clean_line(line: str) -> str:
    """Remove timestamps and noise."""
    line = TIMESTAMP_PATTERN.sub("", line)
    return line.strip()

def extract_service_names(chunk: List[str]) -> List[str]:
    """Extract service names from log lines (e.g., 'systemd[1]', 'dockerd[600]')."""
    services = []
    for line in chunk:
        matches = LOG_ID_PATTERN.findall(line)
        for match in matches:
            # Extract just the service name without the PID
            service = match.split('[')[0]
            if service and service.lower() not in STOPWORDS:
                services.append(service)
    return services

def find_representative_line(chunk: List[str], keywords: List[str]) -> str:
    """Find the most informative line in the chunk based on keywords."""
    if not chunk or not keywords:
        return ""
    
    # Score each line based on keyword presence and position (later lines often more important)
    scored_lines = []
    for i, line in enumerate(chunk):
        clean = clean_line(line).lower()
        # Score based on keyword matches and line position
        keyword_score = sum(2 for k in keywords if k in clean)
        position_score = i * 0.1  # Slight preference for later lines
        scored_lines.append((keyword_score + position_score, line))
    
    # Get the highest scoring line
    if scored_lines:
        return max(scored_lines, key=lambda x: x[0])[1]
    return ""

def extract_bigrams(words: List[str]) -> List[str]:
    """Extract meaningful bigrams from the word list."""
    if len(words) < 2:
        return []
    return [f"{words[i]} {words[i+1]}" for i in range(len(words)-1)]

def summarize_chunk(chunk: List[str]) -> str:
    """Generate an improved summary of the log chunk."""
    if not chunk:
        return "No log data available."
    
    # Clean and normalize lines
    cleaned = [clean_line(l).lower() for l in chunk if l.strip()]
    
    # Extract service names
    services = extract_service_names(chunk)
    service_counter = Counter(services)
    top_services = [s for s, _ in service_counter.most_common(2)]
    
    # Collect significant words (ignore stopwords)
    words = []
    for line in cleaned:
        for w in line.split():
            if len(w) > 3 and w not in STOPWORDS:
                words.append(w)
    
    if not words and not top_services:
        return "No significant events detected."
    
    # Get word frequency
    word_freq = Counter(words)
    
    # Also consider bigrams for more context
    bigrams = extract_bigrams(words)
    bigram_freq = Counter(bigrams)
    
    # Combine single words and bigrams, prioritizing bigrams
    combined_keywords = []
    
    # First add top bigrams if they exist
    for bigram, _ in bigram_freq.most_common(2):
        combined_keywords.append(bigram)
    
    # Then add top single words not already in bigrams
    for word, _ in word_freq.most_common(5):
        # Check if this word is already part of a selected bigram
        if not any(word in bg for bg in combined_keywords):
            combined_keywords.append(word)
        if len(combined_keywords) >= 4:  # Limit to 4 keywords/phrases
            break
    
    # Find a representative line for context
    rep_line = find_representative_line(chunk, combined_keywords)
    rep_line = clean_line(rep_line)
    
    # Build the summary
    if rep_line:
        # If we have a good representative line, use it as the main summary
        summary = f"Summary: {rep_line}"
        
        # Add service context if available
        if top_services:
            summary += f" [Services: {', '.join(top_services)}]"
            
        # Add key terms if they add value
        if combined_keywords:
            # Only include keywords not already in the representative line
            unique_keywords = [k for k in combined_keywords 
                              if k.lower() not in rep_line.lower()]
            if unique_keywords:
                summary += f" [Key terms: {', '.join(unique_keywords[:2])}]"
    else:
        # Fallback to keyword-based summary
        if top_services:
            service_str = f"Services: {', '.join(top_services)}"
            keyword_str = f"Keywords: {', '.join(combined_keywords[:3])}"
            summary = f"Summary: {service_str} | {keyword_str}"
        else:
            summary = f"Summary: {', '.join(combined_keywords)}"
    
    return summary

