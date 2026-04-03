def merge_scores(vector_chunk_scores, keyword_chunk_ids, vec_weight=0.65, kw_weight=0.35):
    merged = {}
    for cid, s in vector_chunk_scores.items():
        merged[cid] = merged.get(cid, 0.0) + vec_weight * float(s)
    boost = kw_weight * 1.0
    for cid in keyword_chunk_ids:
        merged[cid] = merged.get(cid, 0.0) + boost
    return sorted(merged.items(), key=lambda x: -x[1])
