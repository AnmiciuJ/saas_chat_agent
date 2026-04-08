"""
向量索引写入模块。

将向量化结果写入或增量更新至向量数据库，
同时回写关系库中的块镜像记录。
"""


async def write_to_index(
    tenant_id: int,
    document_id: int,
    chunks: list[str],
    vectors: list[list[float]],
) -> None:
    """
    将块文本与对应向量写入向量数据库，并同步关系库镜像。

    载荷字段按数据库设计草案约定携带租户、知识库与文档标识。
    """
    # TODO: 对接 Milvus / 其他向量数据库完成 upsert
    # TODO: 批量写入 document_chunk 镜像表
    pass
