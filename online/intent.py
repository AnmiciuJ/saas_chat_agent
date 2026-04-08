"""
意图识别与查询改写。

将用户原始问题转换为更适合检索的查询表达，
同时识别是否需要走知识库检索、闲聊或其他分支。
"""


async def rewrite_query(user_message: str) -> str:
    """
    对用户原始输入进行查询改写。

    当前为直通实现，后续接入大模型进行语义改写。
    """
    # TODO: 接入大模型进行意图识别与查询改写
    return user_message
