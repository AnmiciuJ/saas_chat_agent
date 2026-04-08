"""
文档解析模块。

从对象存储读取原始文件，根据文件类型选择解析策略，
输出纯文本或结构化文本片段。
"""


async def parse_document(tenant_id: int, document_id: int) -> str:
    """
    解析指定文档并返回提取后的文本内容。

    支持 PDF / Word / 纯文本等格式，后续扩展 OCR 与表格提取。
    """
    # TODO: 从对象存储下载文件
    # TODO: 根据 MIME 类型分发至对应解析器
    return ""
