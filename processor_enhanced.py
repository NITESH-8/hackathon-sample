import re
import uuid
import os
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Tuple, Any, Optional
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict, Counter
from summarizer import summarize_chunk

class ErrorSeverity(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

class ErrorCategory(Enum):
    SYSTEM = "SYSTEM"
    MEMORY = "MEMORY"
    NETWORK = "NETWORK"
    DATABASE = "DATABASE"
    SECURITY = "SECURITY"
    APPLICATION = "APPLICATION"
    HARDWARE = "HARDWARE"
    KERNEL = "KERNEL"
    UNKNOWN = "UNKNOWN"

@dataclass
class ErrorPattern:
    pattern: re.Pattern
    severity: ErrorSeverity
    category: ErrorCategory
    confidence: float
    description: str
    false_positive_patterns: List[re.Pattern] = None

@dataclass
class ErrorDetection:
    is_error: bool
    severity: ErrorSeverity
    category: ErrorCategory
    confidence: float
    matching_patterns: List[str]
    error_context: str
    false_positive: bool = False

def load_error_keywords(path="backend/error_keywords.txt") -> List[ErrorPattern]:
    """Load error keywords from file and compile enhanced regex patterns with severity and category."""
    # Try multiple possible paths
    possible_paths = [
        path,
        f"backend/{path.split('/')[-1]}",
        f"./{path.split('/')[-1]}",
        path.replace("backend/", "")
    ]
    
    actual_path = None
    for p in possible_paths:
        if os.path.exists(p):
            actual_path = p
            break
    
    if not actual_path:
        print(f"Warning: Could not find error keywords file. Tried: {possible_paths}")
        # Fallback to basic error keywords
        basic_keywords = ["error", "fail", "exception", "crash", "fatal"]
        patterns = []
        for kw in basic_keywords:
            patterns.append(ErrorPattern(
                pattern=re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE),
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.UNKNOWN,
                confidence=0.5,
                description=kw
            ))
        return patterns
    
    patterns = []
    current_category = ErrorCategory.UNKNOWN
    current_severity = ErrorSeverity.MEDIUM
    
    # False positive patterns to filter out common non-errors
    false_positive_patterns = [
        re.compile(r"without any error", re.IGNORECASE),
        re.compile(r"no error", re.IGNORECASE),
        re.compile(r"error.*0", re.IGNORECASE),
        re.compile(r"error.*success", re.IGNORECASE),
        re.compile(r"error.*ok", re.IGNORECASE),
        re.compile(r"error.*complete", re.IGNORECASE),
        re.compile(r"error.*finished", re.IGNORECASE),
        re.compile(r"error.*done", re.IGNORECASE),
        re.compile(r"error.*passed", re.IGNORECASE),
        re.compile(r"error.*working", re.IGNORECASE),
        re.compile(r"error.*normal", re.IGNORECASE),
        re.compile(r"error.*good", re.IGNORECASE),
        re.compile(r"error.*fine", re.IGNORECASE),
        re.compile(r"error.*healthy", re.IGNORECASE),
        re.compile(r"error.*stable", re.IGNORECASE),
        re.compile(r"error.*running", re.IGNORECASE),
        re.compile(r"error.*active", re.IGNORECASE),
        re.compile(r"error.*online", re.IGNORECASE),
        re.compile(r"error.*ready", re.IGNORECASE),
        re.compile(r"error.*available", re.IGNORECASE),
    ]
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#"):
                    # Check for category or severity headers
                    line_lower = line.lower()
                    if "system" in line_lower:
                        current_category = ErrorCategory.SYSTEM
                    elif "memory" in line_lower or "segmentation" in line_lower or "null pointer" in line_lower:
                        current_category = ErrorCategory.MEMORY
                    elif "network" in line_lower:
                        current_category = ErrorCategory.NETWORK
                    elif "database" in line_lower:
                        current_category = ErrorCategory.DATABASE
                    elif "security" in line_lower:
                        current_category = ErrorCategory.SECURITY
                    elif "application" in line_lower:
                        current_category = ErrorCategory.APPLICATION
                    elif "hardware" in line_lower or "thermal" in line_lower or "fan" in line_lower:
                        current_category = ErrorCategory.HARDWARE
                    elif "kernel" in line_lower or "panic" in line_lower or "bug" in line_lower:
                        current_category = ErrorCategory.KERNEL
                    elif "critical" in line_lower:
                        current_severity = ErrorSeverity.CRITICAL
                    elif "high" in line_lower:
                        current_severity = ErrorSeverity.HIGH
                    elif "medium" in line_lower:
                        current_severity = ErrorSeverity.MEDIUM
                    elif "low" in line_lower:
                        current_severity = ErrorSeverity.LOW
                    elif "info" in line_lower:
                        current_severity = ErrorSeverity.INFO
                elif line:
                    # Determine confidence based on pattern specificity
                    confidence = 0.8  # Base confidence
                    if len(line.split()) > 2:  # Multi-word patterns are more specific
                        confidence += 0.1
                    if any(char in line for char in ['[', ']', '(', ')', '{', '}']):  # Technical patterns
                        confidence += 0.1
                    if any(sig in line.upper() for sig in ['SIG', 'SIGSEGV', 'SIGFPE', 'SIGILL', 'SIGBUS', 'SIGABRT']):
                        confidence += 0.1
                    if any(term in line.lower() for term in ['panic', 'fatal', 'critical', 'crash', 'segfault']):
                        confidence += 0.1
                    
                    # Create enhanced pattern with context awareness
                    enhanced_pattern = create_enhanced_pattern(line)
                    
                    patterns.append(ErrorPattern(
                        pattern=enhanced_pattern,
                        severity=current_severity,
                        category=current_category,
                        confidence=min(confidence, 1.0),
                        description=line,
                        false_positive_patterns=false_positive_patterns
                    ))
    except Exception as e:
        print(f"Warning: Could not load error keywords from {path}: {e}")
        # Fallback to basic error keywords
        basic_keywords = ["error", "fail", "exception", "crash", "fatal"]
        for kw in basic_keywords:
            patterns.append(ErrorPattern(
                pattern=re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE),
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.UNKNOWN,
                confidence=0.5,
                description=kw
            ))
    return patterns

def create_enhanced_pattern(keyword: str) -> re.Pattern:
    """Create an enhanced regex pattern with context awareness."""
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
    else:
        # Default pattern with word boundaries
        pattern = rf"\b{escaped}\b"
    
    return re.compile(pattern, re.IGNORECASE | re.MULTILINE)

# Load at startup
ERROR_PATTERNS = load_error_keywords()

def detect_errors_enhanced(chunk: List[str]) -> ErrorDetection:
    """Enhanced error detection with severity, category, and confidence scoring."""
    text = " ".join(chunk)
    matching_patterns = []
    error_contexts = []
    max_severity = ErrorSeverity.INFO
    max_confidence = 0.0
    primary_category = ErrorCategory.UNKNOWN
    is_false_positive = False
    
    # Check for false positives first
    for pattern_obj in ERROR_PATTERNS:
        if pattern_obj.false_positive_patterns:
            for fp_pattern in pattern_obj.false_positive_patterns:
                if fp_pattern.search(text):
                    is_false_positive = True
                    break
        if is_false_positive:
            break
    
    # If not a false positive, check for actual errors
    if not is_false_positive:
        for pattern_obj in ERROR_PATTERNS:
            matches = pattern_obj.pattern.findall(text)
            if matches:
                matching_patterns.extend([pattern_obj.description] * len(matches))
                
                # Update severity (highest wins)
                if pattern_obj.severity.value in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']:
                    severity_order = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']
                    if severity_order.index(pattern_obj.severity.value) < severity_order.index(max_severity.value):
                        max_severity = pattern_obj.severity
                        primary_category = pattern_obj.category
                
                # Update confidence (highest wins)
                if pattern_obj.confidence > max_confidence:
                    max_confidence = pattern_obj.confidence
                
                # Extract error context
                for match in matches:
                    context = extract_error_context(text, match, pattern_obj.description)
                    if context:
                        error_contexts.append(context)
    
    # Determine if this is actually an error
    is_error = bool(matching_patterns) and not is_false_positive and max_confidence > 0.3
    
    # Create error context summary
    error_context = "; ".join(error_contexts[:3]) if error_contexts else "No specific context"
    
    return ErrorDetection(
        is_error=is_error,
        severity=max_severity,
        category=primary_category,
        confidence=max_confidence,
        matching_patterns=list(set(matching_patterns)),
        error_context=error_context,
        false_positive=is_false_positive
    )

def extract_error_context(text: str, match: str, pattern: str) -> str:
    """Extract relevant context around an error match."""
    # Find the position of the match in the text
    match_pos = text.lower().find(match.lower())
    if match_pos == -1:
        return ""
    
    # Extract context around the match (50 chars before and after)
    start = max(0, match_pos - 50)
    end = min(len(text), match_pos + len(match) + 50)
    context = text[start:end].strip()
    
    # Clean up the context
    context = re.sub(r'\s+', ' ', context)  # Normalize whitespace
    
    return context

def is_problem_chunk(chunk: List[str]) -> Tuple[bool, List[str]]:
    """Legacy function for backward compatibility."""
    detection = detect_errors_enhanced(chunk)
    return detection.is_error, detection.matching_patterns

def analyze_error_patterns(results: List[Tuple[int, str, bool]]) -> Dict[str, Any]:
    """Analyze error patterns and provide statistics."""
    severity_counts = defaultdict(int)
    category_counts = defaultdict(int)
    pattern_counts = defaultdict(int)
    
    for _, text, is_problem in results:
        if is_problem:
            # Extract severity and category from the formatted text
            if "CRITICAL ERROR" in text:
                severity_counts["critical"] += 1
            elif "HIGH ERROR" in text:
                severity_counts["high"] += 1
            elif "MEDIUM ERROR" in text:
                severity_counts["medium"] += 1
            elif "LOW ERROR" in text:
                severity_counts["low"] += 1
            else:
                severity_counts["info"] += 1
            
            # Extract category
            if "SYSTEM]" in text:
                category_counts["SYSTEM"] += 1
            elif "MEMORY]" in text:
                category_counts["MEMORY"] += 1
            elif "NETWORK]" in text:
                category_counts["NETWORK"] += 1
            elif "DATABASE]" in text:
                category_counts["DATABASE"] += 1
            elif "SECURITY]" in text:
                category_counts["SECURITY"] += 1
            elif "APPLICATION]" in text:
                category_counts["APPLICATION"] += 1
            elif "HARDWARE]" in text:
                category_counts["HARDWARE"] += 1
            elif "KERNEL]" in text:
                category_counts["KERNEL"] += 1
            else:
                category_counts["UNKNOWN"] += 1
    
    # Get top categories
    top_categories = [cat for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)]
    
    return {
        "critical_count": severity_counts["critical"],
        "high_count": severity_counts["high"],
        "medium_count": severity_counts["medium"],
        "low_count": severity_counts["low"],
        "info_count": severity_counts["info"],
        "top_categories": top_categories,
        "total_errors": sum(severity_counts.values()),
        "category_distribution": dict(category_counts)
    }

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

    # Analyze results for enhanced statistics
    problem_count = sum(1 for r in results if r[2])
    
    # Analyze error patterns and severity distribution
    error_analysis = analyze_error_patterns(results)
    
    # Write processed output
    with open(output_path, "w", encoding="utf-8") as out:
        # Write header with enhanced metadata
        out.write(f"# Processed Log File: {file_name}\n")
        out.write(f"# Size: {file_size:.2f} KB | Total Chunks: {len(chunks)} | Problem Chunks: {problem_count}\n")
        out.write(f"# Error Analysis: {error_analysis['critical_count']} Critical, {error_analysis['high_count']} High, {error_analysis['medium_count']} Medium, {error_analysis['low_count']} Low\n")
        out.write(f"# Top Error Categories: {', '.join(error_analysis['top_categories'][:3])}\n")
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
    detection = detect_errors_enhanced(chunk)
    
    if detection.is_error:
        # For problem chunks, include enhanced error information
        raw = "".join(chunk).strip()
        
        # Create severity emoji
        severity_emoji = {
            ErrorSeverity.CRITICAL: "🚨",
            ErrorSeverity.HIGH: "🔴",
            ErrorSeverity.MEDIUM: "🟡",
            ErrorSeverity.LOW: "🟠",
            ErrorSeverity.INFO: "ℹ️"
        }
        
        # Create category emoji
        category_emoji = {
            ErrorCategory.SYSTEM: "💻",
            ErrorCategory.MEMORY: "🧠",
            ErrorCategory.NETWORK: "🌐",
            ErrorCategory.DATABASE: "🗄️",
            ErrorCategory.SECURITY: "🔒",
            ErrorCategory.APPLICATION: "📱",
            ErrorCategory.HARDWARE: "🔧",
            ErrorCategory.KERNEL: "⚙️",
            ErrorCategory.UNKNOWN: "❓"
        }
        
        emoji = severity_emoji.get(detection.severity, "⚠️")
        cat_emoji = category_emoji.get(detection.category, "❓")
        
        # Format error information
        patterns_str = ", ".join(detection.matching_patterns[:3])
        confidence_pct = int(detection.confidence * 100)
        
        error_header = f"CHUNK {idx} - {emoji} {detection.severity.value} ERROR DETECTED {cat_emoji} [{detection.category.value}]"
        error_details = f"Patterns: {patterns_str} | Confidence: {confidence_pct}%"
        error_context = f"Context: {detection.error_context}" if detection.error_context != "No specific context" else ""
        
        if error_context:
            formatted_text = f"{error_header}\n{error_details}\n{error_context}\n{raw}"
        else:
            formatted_text = f"{error_header}\n{error_details}\n{raw}"
            
        return idx, formatted_text, True
    else:
        # For normal chunks, provide an improved summary
        summary = summarize_chunk(chunk)
        return idx, f"CHUNK {idx} - {summary}", False
