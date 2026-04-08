"""
文档解析模块。

从对象存储读取原始文件，根据文件类型选择解析策略，
输出纯文本内容。首期支持纯文本与 PDF 两种格式。
"""

import logging

from app.services.storage import read_file

logger = logging.getLogger(__name__)


async def parse_document(tenant_id: int, document_id: int, storage_key: str, mime_type: str | None) -> str:
    """
    解析指定文档并返回提取后的文本内容。

    参数:
        tenant_id: 租户标识
        document_id: 文档标识
        storage_key: 对象存储键
        mime_type: 文件 MIME 类型
    """
    raw = await read_file(storage_key)

    if mime_type and "pdf" in mime_type:
        return _parse_pdf(raw)

    return _parse_plaintext(raw)


def _parse_plaintext(raw: bytes) -> str:
    """尝试以 UTF-8 解码纯文本，降级为 GBK。"""
    for encoding in ("utf-8", "gbk", "latin-1"):
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, ValueError):
            continue
    return raw.decode("utf-8", errors="replace")


def _parse_pdf(raw: bytes) -> str:
    """使用 PyMuPDF 提取 PDF 文本。若未安装则降级提示。"""
    try:
        import fitz
    except ImportError:
        logger.warning("PyMuPDF(fitz) 未安装，PDF 解析不可用")
        return ""

    text_parts: list[str] = []
    with fitz.open(stream=raw, filetype="pdf") as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n".join(text_parts)
