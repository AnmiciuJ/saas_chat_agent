def split_text(text, size, overlap):
    if size <= 0:
        return []
    if overlap >= size:
        overlap = max(0, size // 4)
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + size, n)
        chunks.append(text[start:end])
        if end >= n:
            break
        start = end - overlap
    return chunks
