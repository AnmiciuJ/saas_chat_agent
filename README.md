# 多租户 AI 客服 SaaS（设计说明）

1. 业务目标：设计一个支持多租户的AI客服SaaS系统，要求能够支持模型迭代微调，私有知识库上传（RAG），保证数据隔离，并能应对高并发。
2. 需求梳理：
![需求地图：多租户 AI 客服 SaaS 功能分解](project_design/demand_map.png)

3. 在线服务与离线服务：

**在线服务** ：**用户问题 → 意图理解与查询表达 → 知识检索（含向量索引查询）→ 重排序 → 大模型推理 → 结果输出**。

![在线服务链路示意](project_design/online_service.png)

**离线服务** ：**原始文件落盘 → 异步任务拉取 → 解析与清洗 → 语义分块 → 向量化 → 写入或更新向量索引**。该链路与租户绑定

![离线服务链路示意](project_design/offline_service.png)
4. 会话管理

将 **近期上下文**（滑动窗口与摘要压缩）、**历史要点检索**（向量或检索服务）、**结构化画像**（偏好与约束）与 **相关性过滤**设计进图

![会话管理与记忆组装示意](project_design/session_management.png)

5. 系统结构总览

![系统结构总览](project_design/system_structure.png)
