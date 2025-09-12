import re
import uuid
import os
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Tuple, Any
from collections import defaultdict
from summarizer import summarize_chunk

def load_error_keywords(path="error_keywords.txt") -> Tuple[List[re.Pattern], List[re.Pattern]]:
    """Load error keywords from file and compile enhanced regex patterns with false positive filtering."""
    patterns = []
    false_positive_patterns = []
    
    # Common false positive patterns
    false_positive_keywords = [
        r"without any error",
        r"no error",
        r"error.*0",
        r"error.*success",
        r"error.*ok",
        r"error.*complete",
        r"error.*finished",
        r"error.*done",
        r"error.*passed",
        r"error.*working",
        r"error.*normal",
        r"error.*good",
        r"error.*fine",
        r"error.*healthy",
        r"error.*stable",
        r"error.*running",
        r"error.*active",
        r"error.*online",
        r"error.*ready",
        r"error.*available",
        r"error.*count.*0",
        r"error.*rate.*0",
        r"error.*free",
        r"error.*clean",
        r"error.*clear",
        r"error.*resolved",
        r"error.*fixed",
        r"error.*repaired",
        r"error.*restored",
        r"error.*recovered"
    ]
    
    # Compile false positive patterns
    for fp_keyword in false_positive_keywords:
        false_positive_patterns.append(re.compile(fp_keyword, re.IGNORECASE))
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    # Create enhanced pattern with context awareness
                    enhanced_pattern = create_enhanced_pattern(line)
                    patterns.append(enhanced_pattern)
    except Exception as e:
        print(f"Warning: Could not load error keywords from {path}: {e}")
        # Fallback to basic error keywords
        basic_keywords = ["error", "fail", "exception", "crash", "fatal"]
        for kw in basic_keywords:
            patterns.append(re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE))
    return patterns, false_positive_patterns

def create_enhanced_pattern(keyword: str) -> re.Pattern:
    """Create an enhanced regex pattern with context awareness for better error detection."""
    # Escape special regex characters
    escaped = re.escape(keyword)
    
    # Add context patterns for better detection
    if keyword.lower() in ['segfault', 'segmentation fault', 'sigsegv']:
        # Look for segmentation fault patterns with addresses, process IDs, etc.
        pattern = rf"(?:segfault|segmentation\s+fault|SIGSEGV).*?(?:\d+|0x[0-9a-fA-F]+|process\s+\d+)"
    elif keyword.lower() in ['kernel panic', 'panic']:
        # Look for kernel panic with context
        pattern = rf"(?:kernel\s+panic|panic).*?(?:not\s+syncing|fatal|exception|oops)"
    elif keyword.lower() in ['null pointer', 'null pointer dereference']:
        # Look for null pointer with context
        pattern = rf"(?:null\s+pointer|NULL\s+pointer).*?(?:dereference|exception|at\s+0x[0-9a-fA-F]+)"
    elif keyword.lower() in ['core dump', 'core dumped']:
        # Look for core dump patterns
        pattern = rf"(?:core\s+dump|core\s+dumped).*?(?:/tmp/|process\s+\d+|signal\s+\d+)"
    elif keyword.lower() in ['bug', 'bug_on', 'warn_on']:
        # Look for BUG patterns with context
        pattern = rf"(?:BUG|BUG_ON|WARN_ON).*?(?:triggered|detected|at\s+[^:]+:\d+)"
    elif keyword.lower() in ['out of memory', 'oom']:
        # Look for OOM patterns
        pattern = rf"(?:out\s+of\s+memory|OOM).*?(?:kill\s+process|allocation\s+failed|exhausted)"
    elif keyword.lower() in ['buffer overflow', 'stack overflow']:
        # Look for overflow patterns
        pattern = rf"(?:buffer\s+overflow|stack\s+overflow).*?(?:detected|in\s+stack|smashing)"
    elif keyword.lower() in ['deadlock', 'hung task']:
        # Look for deadlock patterns
        pattern = rf"(?:deadlock|hung\s+task).*?(?:detected|blocked|between\s+processes)"
    elif keyword.lower() in ['timeout', 'timed out']:
        # Look for timeout patterns
        pattern = rf"(?:timeout|timed\s+out).*?(?:connection|request|operation|failed)"
    elif keyword.lower() in ['connection refused', 'refused']:
        # Look for connection refused patterns
        pattern = rf"(?:connection\s+refused|refused).*?(?:connect|bind|listen|accept)"
    elif keyword.lower() in ['permission denied', 'access denied']:
        # Look for permission denied patterns
        pattern = rf"(?:permission\s+denied|access\s+denied).*?(?:file|directory|resource|operation)"
    elif keyword.lower() in ['file not found', 'not found']:
        # Look for file not found patterns
        pattern = rf"(?:file\s+not\s+found|not\s+found).*?(?:/|\\|path|directory)"
    elif keyword.lower() in ['syntax error', 'parse error']:
        # Look for syntax error patterns
        pattern = rf"(?:syntax\s+error|parse\s+error).*?(?:line|column|position|at)"
    elif keyword.lower() in ['database error', 'sql error']:
        # Look for database error patterns
        pattern = rf"(?:database\s+error|sql\s+error).*?(?:query|table|constraint|deadlock)"
    elif keyword.lower() in ['network error', 'socket error']:
        # Look for network error patterns
        pattern = rf"(?:network\s+error|socket\s+error).*?(?:bind|listen|accept|connect|send|receive)"
    elif keyword.lower() in ['memory leak', 'leak']:
        # Look for memory leak patterns
        pattern = rf"(?:memory\s+leak|leak).*?(?:detected|bytes|allocation|freed)"
    elif keyword.lower() in ['corruption', 'corrupted']:
        # Look for corruption patterns
        pattern = rf"(?:corruption|corrupted).*?(?:data|file|memory|disk|database)"
    elif keyword.lower() in ['fatal', 'critical']:
        # Look for fatal/critical patterns
        pattern = rf"(?:fatal|critical).*?(?:error|exception|failure|abort|terminate)"
    elif keyword.lower() in ['exception', 'thrown']:
        # Look for exception patterns
        pattern = rf"(?:exception|thrown).*?(?:caught|handled|unhandled|at\s+[^:]+:\d+)"
    elif keyword.lower() in ['crash', 'crashed']:
        # Look for crash patterns
        pattern = rf"(?:crash|crashed).*?(?:application|process|service|system)"
    elif keyword.lower() in ['abort', 'aborted']:
        # Look for abort patterns
        pattern = rf"(?:abort|aborted).*?(?:signal|process|operation|transaction)"
    elif keyword.lower() in ['halt', 'halted']:
        # Look for halt patterns
        pattern = rf"(?:halt|halted).*?(?:system|process|execution|operation)"
    else:
        # Default pattern with word boundaries and context
        pattern = rf"\b{escaped}\b"
    
    return re.compile(pattern, re.IGNORECASE | re.MULTILINE)

# Load at startup
ERROR_PATTERNS, FALSE_POSITIVE_PATTERNS = load_error_keywords()

def is_problem_chunk(chunk: List[str]) -> Tuple[bool, List[str]]:
    """Enhanced error detection with false positive filtering and context awareness.
    Returns a tuple of (is_problem, matching_keywords).
    """
    text = " ".join(chunk)
    matching_keywords = []
    
    # First check for false positives
    is_false_positive = False
    for fp_pattern in FALSE_POSITIVE_PATTERNS:
        if fp_pattern.search(text):
            is_false_positive = True
            break
    
    # If it's a false positive, don't consider it an error
    if is_false_positive:
        return False, []
    
    # Check for actual error patterns
    for pattern in ERROR_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            # Add unique keywords to the list
            for match in matches:
                if match.lower() not in [k.lower() for k in matching_keywords]:
                    matching_keywords.append(match)
    
    return bool(matching_keywords), matching_keywords

def process_log_file(file_path: str, chunk_size: int = 5) -> str:
    """Process log file → returns path of final processed file."""
    output_id = str(uuid.uuid4())
    output_path = f"processed_{output_id}.txt"

    try:
        with open(file_path, "r", errors="ignore") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return f"Error: Could not process file - {str(e)}"

    # Get file stats for metadata
    try:
        file_size = os.path.getsize(file_path) / 1024  # KB
        file_name = os.path.basename(file_path)
    except Exception:
        file_size = 0
        file_name = "unknown"

    # Create chunks with overlap for better context
    chunks = []
    for i in range(0, len(lines), chunk_size):
        # Add one line of overlap when possible (except for first chunk)
        start = max(0, i-1) if i > 0 else 0
        end = min(len(lines), i + chunk_size)
        chunks.append((i//chunk_size + 1, lines[start:end]))

    # Process chunks in parallel
    results = []
    with ThreadPoolExecutor() as executor:
        futures = []
        for idx, chunk in chunks:
            futures.append(executor.submit(process_chunk, idx, chunk))

        for fut in futures:
            results.append(fut.result())

    # Preserve order
    results.sort(key=lambda x: x[0])

    # Count problem chunks for summary
    problem_count = sum(1 for r in results if r[2])
    
    # Write processed output
    with open(output_path, "w", encoding="utf-8") as out:
        # Write header with metadata
        out.write(f"# Processed Log File: {file_name}\n")
        out.write(f"# Size: {file_size:.2f} KB | Total Chunks: {len(chunks)} | Problem Chunks: {problem_count}\n")
        out.write(f"# Generated: {uuid.uuid4()}\n")
        out.write("#" + "-" * 80 + "\n\n")
        
        # Write each chunk result
        for _, text, is_problem in results:
            prefix = "⚠️ " if is_problem else "✓ "
            out.write(prefix + text + "\n\n")

    return output_path


def process_chunk(idx: int, chunk: List[str]):
    """Process individual chunk → summary or raw log with enhanced error detection.
    Returns (index, formatted_text, is_problem_chunk)
    """
    is_problem, matching_keywords = is_problem_chunk(chunk)
    
    if is_problem:
        # For problem chunks, include enhanced error information
        raw = "".join(chunk).strip()
        
        # Categorize error types
        error_categories = categorize_errors(matching_keywords)
        category_str = ", ".join(error_categories[:2]) if error_categories else "Unknown"
        
        # Format error information
        keyword_str = ", ".join(matching_keywords[:3])
        
        # Extract context around errors
        error_context = extract_error_context(raw, matching_keywords)
        
        error_header = f"CHUNK {idx} - ⚠️ ERROR DETECTED [{category_str}]"
        error_details = f"Patterns: {keyword_str}"
        
        if error_context:
            formatted_text = f"{error_header}\n{error_details}\nContext: {error_context}\n{raw}"
        else:
            formatted_text = f"{error_header}\n{error_details}\n{raw}"
            
        return idx, formatted_text, True
    else:
        # For normal chunks, provide an improved summary
        summary = summarize_chunk(chunk)
        return idx, f"CHUNK {idx} - {summary}", False

def categorize_errors(keywords: List[str]) -> List[str]:
    """Categorize error keywords into meaningful categories."""
    categories = []
    
    for keyword in keywords:
        keyword_lower = keyword.lower()
        if any(term in keyword_lower for term in ['segfault', 'segmentation', 'sigsegv', 'null pointer', 'memory', 'buffer', 'stack']):
            categories.append("Memory")
        elif any(term in keyword_lower for term in ['kernel', 'panic', 'bug', 'oops', 'fatal']):
            categories.append("Kernel")
        elif any(term in keyword_lower for term in ['network', 'timeout', 'connection', 'socket', 'refused']):
            categories.append("Network")
        elif any(term in keyword_lower for term in ['database', 'sql', 'deadlock', 'constraint']):
            categories.append("Database")
        elif any(term in keyword_lower for term in ['security', 'unauthorized', 'permission', 'access']):
            categories.append("Security")
        elif any(term in keyword_lower for term in ['hardware', 'thermal', 'fan', 'disk', 'i/o']):
            categories.append("Hardware")
        elif any(term in keyword_lower for term in ['application', 'crash', 'exception', 'abort']):
            categories.append("Application")
        elif any(term in keyword_lower for term in ['system', 'service', 'daemon', 'process']):
            categories.append("System")
    
    return list(set(categories))

def extract_error_context(text: str, keywords: List[str]) -> str:
    """Extract relevant context around error keywords."""
    if not keywords:
        return ""
    
    # Find the first error keyword in the text
    first_error = None
    first_pos = len(text)
    
    for keyword in keywords:
        pos = text.lower().find(keyword.lower())
        if pos != -1 and pos < first_pos:
            first_pos = pos
            first_error = keyword
    
    if first_error is None:
        return ""
    
    # Extract context around the first error (100 chars before and after)
    start = max(0, first_pos - 100)
    end = min(len(text), first_pos + len(first_error) + 100)
    context = text[start:end].strip()
    
    # Clean up the context
    context = re.sub(r'\s+', ' ', context)  # Normalize whitespace
    
    return context
