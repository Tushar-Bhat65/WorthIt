def is_match(title: str, query: str) -> bool:
    """
    Returns True if all query words are present in title, case-insensitive.
    Excludes results that are variants (like 'Pro' if not asked).
    """
    query_words = query.lower().split()
    title_lower = title.lower()

    # All words in query must be present in the title
    return all(word in title_lower for word in query_words)
