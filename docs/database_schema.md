# 数据层与库表结构设计（草案）

本文档依据多租户 AI 客服 SaaS 的产品范围（多租户、模型可迭代、私有知识与检索增强生成、高并发）整理 **产品需求拆解**、**功能点与库表字段的对应关系**、**关系型数据库表结构**、**向量侧载荷约定**、**对象存储与缓存键约定**，供后续开发与评审使用。实现时可按首期范围裁剪表或字段。

---

## 1. 产品需求拆解（markmap）

下列文本可粘贴至 [markmap](https://markmap.js.org/repl) 或支持 markmap 的编辑器中渲染为树状图。

```markdown
markmap

# 多租户 AI 客服 SaaS
- 多租户
    - 租户管理
        - 租户注册/审核/开通
        - 租户套餐管理
        - 租户停用/注销与数据归档
    - 数据隔离
        - 模型租户级隔离
        - 知识库租户级隔离
        - 会话数据租户级隔离
        - 文件存储路径级隔离
    - 用量与计费
        - 对话轮次用量统计
        - Token 消耗计量
        - 知识库存储容量计量
- 模型可迭代
    - 基座模型管理
        - 多基座模型接入（自部署/第三方API）
        - 租户级模型绑定与切换
    - 微调流水线
        - 训练数据采集
        - 训练监控与日志
        - 自动评估
        - 版本控制
- 私有知识 + RAG
    - 知识源管理
        - 文档上传（PDF/Word/Excel/网页/图片）
        - 多模态内容解析（OCR/表格提取）
        - 知识条目手动录入与编辑
        - 知识库启用/停用/版本快照
    - 离线处理流水线
        - 文本清洗与预处理
        - 语义分块（按段落/滑动窗口/递归拆分）
        - 向量化（Embedding模型选择）
        - 索引构建（HNSW）与增量更新
    - 在线检索链路
        - 意图识别与查询改写
        - 向量召回（Top-K 相似度检索）
        - 混合检索（向量 + 关键词 BM25）
        - 重排序（Cross-Encoder 精排）
        - 引用溯源（回答附带知识来源）
    - 会话记忆
        - 短期记忆（滑动窗口 + 摘要压缩）
        - 长期记忆（历史对话向量化检索）
        - 结构化记忆（用户画像/偏好标签）
        - 相关性过滤（按话题衰减无关上下文）
- 高并发
    - 网关层
        - API 网关统一入口
        - WebSocket 长连接（流式输出）
    - 异步与削峰
        - 消息队列
        - 对话/知识处理/微调拆分结构
        - 热点查询缓存
```

---

## 2. 功能需求与库表覆盖总览

| 需求域 | 主要承载表（关系库） | 非关系库或其它 |
|--------|----------------------|----------------|
| 租户注册/审核/开通/套餐/归档 | plan、tenant | 对象存储路径前缀随 tenant_id |
| 模型租户级隔离 | tenant_model_binding、base_model、chat_message（记录实际使用模型） | 向量库载荷 tenant_id |
| 知识库隔离 | knowledge_base、document、knowledge_entry 等全表 tenant_id | 向量库按租户或载荷过滤 |
| 会话隔离 | conversation、chat_message、end_user_profile | Redis 键带 tenant_id |
| 文件存储路径隔离 | document.storage_bucket、storage_key | 对象存储 |
| 用量与计费计量 | usage_event、usage_daily_aggregate | 限额可用 Redis 计数 |
| 基座接入与租户绑定切换 | base_model、tenant_model_binding |  |
| 嵌入模型选择与维度校验 | embedding_model、knowledge_base.embedding_model_id | 向量维度与 embedding_model.vector_dimension 对齐 |
| 微调数据采集/日志/评估/版本 | fine_tune_job | 对象存储数据集与日志文件 |
| 文档与网页等多来源、解析 | document（来源与解析产物键） | OCR 结果可存对象存储 |
| 手工条目 | knowledge_entry、knowledge_entry_chunk | 向量载荷 |
| 离线清洗/分块/向量/索引 | ingestion_job、document_chunk、document（状态与策略） | 向量库、HNSW 为引擎配置 |
| 意图/改写/混合检索/重排/溯源 | chat_message（pipeline_trace、retrieval_refs） | 检索中间结果可部分在 Redis |
| 短期记忆与摘要 | conversation.summary、chat_message；Redis 会话窗口 |  |
| 长期对话记忆检索 | conversation_memory_chunk | 向量库对话历史集合 |
| 用户画像与偏好 | end_user_profile |  |
| 网关与 API 接入身份 | tenant_api_credential |  |
| 流式与高并发 | 主要由应用层与 Redis；计量写入 usage_event | WebSocket 无单独表 |

---

## 3. 功能需求点的字段级应用场景（逐项对照）

### 3.1 多租户

| 功能点 | 应用场景说明 | 主要表与字段 |
|--------|----------------|----------------|
| 租户注册/审核/开通 | 新租户提交资料、运营审核、通过后变为可服务状态 | tenant.status、tenant.review_note、tenant.reviewed_at、tenant.plan_id |
| 租户套餐管理 | 定义各档配额与能力开关，租户订阅某档 | plan.* 限额字段、tenant.plan_id、plan.features |
| 租户停用/注销与归档 | 停止服务或进入只读/归档，便于合规留存 | tenant.status、tenant.archived_at |
| 模型租户级隔离 | 同一平台多模型目录，各租户只使用已绑定模型 | base_model、tenant_model_binding、chat_message.used_base_model_id |
| 知识库租户级隔离 | 知识库与文档仅在本租户内可见与检索 | 各业务表 tenant_id；knowledge_base.tenant_id |
| 会话数据租户级隔离 | 会话与消息列表、统计均按租户隔离 | conversation.tenant_id、chat_message.tenant_id |
| 文件存储路径级隔离 | 原始文件与解析产物键名包含租户语义，防串桶 | document.storage_bucket、document.storage_key |
| 对话轮次用量 | 按次计费或限额 | usage_event.event_type=chat_turn、usage_daily_aggregate.chat_turns |
| Token 消耗计量 | 提示与生成分别统计 | usage_event、chat_message.prompt_tokens、completion_tokens |
| 知识库存储容量计量 | 按文档大小汇总 | usage_event.event_type=storage_bytes、document.size_bytes |

### 3.2 模型可迭代

| 功能点 | 应用场景说明 | 主要表与字段 |
|--------|----------------|----------------|
| 多基座接入 | 平台维护可调用的推理服务条目 | base_model.provider、model_key、extra_config |
| 租户绑定与切换 | 租户默认模型与可选模型列表 | tenant_model_binding.is_default、priority、enabled |
| 训练数据采集 | 微调任务关联数据集对象 | fine_tune_job.dataset_storage_key |
| 训练监控与日志 | 训练过程日志文件存放与排障 | fine_tune_job.log_storage_key、fine_tune_job.status |
| 自动评估 | 保存指标供对比与门禁 | fine_tune_job.metrics、fine_tune_job.evaluation_summary |
| 版本控制 | 产出模型版本与血缘 | fine_tune_job.version_label、output_model_ref、parent_fine_tune_job_id |

### 3.3 私有知识与 RAG

| 功能点 | 应用场景说明 | 主要表与字段 |
|--------|----------------|----------------|
| 文档上传多格式 | 区分来源与类型，便于解析器选择 | document.source_type、mime_type、original_filename |
| 网页导入 | 记录抓取地址与重抓 | document.source_url |
| 多模态解析 | OCR、表格等侧车文件存放 | document.extracted_aux_storage_key、parse_status |
| 手工条目 | 独立正文与发布状态 | knowledge_entry.*、knowledge_entry_chunk（分块与向量对齐） |
| 知识库启停与快照 | 停用则不参与检索；快照用于回滚 | knowledge_base.status、current_snapshot_id、knowledge_base_snapshot |
| 文本清洗与分块策略 | 记录本次入库采用的策略，便于复现与重建 | document.chunk_profile_json、ingestion_job.job_type |
| 向量化与嵌入模型选择 | 与知识库或任务一致的嵌入模型键 | knowledge_base.embedding_model_key、embedding_model 目录表、document_chunk.embedding_model_key |
| 索引构建与增量 | 任务状态驱动重试与对账 | ingestion_job.*、document.index_status |
| 意图与查询改写 | 在线链路审计，便于运营与排错 | chat_message.pipeline_trace、chat_message.rewritten_query |
| 向量召回与混合检索与重排 | 结构化记录各阶段候选与模型 | chat_message.pipeline_trace（含阶段结果标识）、retrieval_refs |
| 引用溯源 | 助手消息关联到块、文档或手工条目块 | chat_message.retrieval_refs、document_chunk.id、knowledge_entry_chunk.id |
| 短期记忆 | 会话级摘要与最近轮次 | conversation.summary、chat_message、Redis 会话窗口（见第 8 节） |
| 长期记忆 | 历史轮次转向量后的可检索片段 | conversation_memory_chunk、向量库对话记忆载荷 |
| 用户画像与偏好 | 跨会话个性化约束 | end_user_profile.preference_json、tag_json |
| 相关性过滤 | 可由应用层根据 topic 与 pipeline_trace 决策；摘要与画像辅助 | conversation.summary、end_user_profile |

### 3.4 高并发

| 功能点 | 应用场景说明 | 主要表与字段 |
|--------|----------------|----------------|
| API 网关统一入口 | 第三方或开放 API 的密钥与租户绑定 | tenant_api_credential（密钥哈希、租户、启停） |
| WebSocket 流式 | 会话与消息仍落库，流式仅为传输形态 | conversation、chat_message（与 HTTP 一致） |
| 消息队列与异步 | 离线任务与对账 | ingestion_job.worker_task_id、状态机 |
| 热点查询缓存 | 检索结果缓存键与租户隔离 | Redis（第 8 节）；可选与 chat_message 引用同一 query 哈希 |
| 限流与配额 | 与套餐上限对账 | plan 限额、usage_daily_aggregate、Redis 计数键 |

---

## 4. 设计约定

| 约定项 | 说明 |
|--------|------|
| 主键 | 除特别说明外使用无符号整型自增或雪花/UUID 字符串，实现阶段选定一种并全库统一 |
| 多租户 | 所有租户业务表包含租户标识字段；查询默认带租户条件；唯一约束在「租户 + 业务键」范围内定义 |
| 时间 | 统一使用 UTC 存储；应用层按租户或用户时区展示 |
| 软删除 | 需要审计或恢复的实体使用删除时间或状态；硬删除与归档策略单独定义 |
| 金额与计费 | 本文档仅覆盖计量字段；计价规则、账单、支付在后续扩展 |

---

## 5. 关系型数据库表结构

类型说明：`VARCHAR(n)`、`TEXT`、`BIGINT`、`INT`、`DECIMAL(p,s)`、`JSON`、`DATETIME(6)`、`TINYINT`（布尔 0/1）、`ENUM`（实现时可用字符串+约束替代）。

### 5.1 套餐与租户

#### 表：`plan`（套餐定义）

| 字段名 | 类型 | 空 | 说明 |
|--------|------|----|------|
| id | BIGINT | 否 | 主键 |
| code | VARCHAR(64) | 否 | 套餐编码，全局唯一 |
| name | VARCHAR(128) | 否 | 展示名称 |
| description | TEXT | 是 | 说明 |
| max_knowledge_bases | INT | 否 | 允许知识库数量上限，-1 表示不限制 |
| max_documents_total | INT | 否 | 允许文档总数上限 |
| max_storage_bytes | BIGINT | 否 | 知识库存储上限（字节） |
| max_monthly_chat_turns | INT | 否 | 每月对话轮次上限，-1 不限制 |
| max_monthly_tokens | BIGINT | 否 | 每月 Token 上限，-1 不限制 |
| features | JSON | 是 | 功能开关，如是否允许微调、是否允许多模型 |
| is_active | TINYINT | 否 | 是否对外可选 |
| created_at | DATETIME(6) | 否 | 创建时间 |
| updated_at | DATETIME(6) | 否 | 更新时间 |

#### 表：`tenant`（租户）

| 字段名 | 类型 | 空 | 说明 |
|--------|------|----|------|
| id | BIGINT | 否 | 主键 |
| name | VARCHAR(256) | 否 | 租户名称 |
| slug | VARCHAR(64) | 否 | URL 友好标识，全局唯一 |
| status | ENUM | 否 | pending_review、active、suspended、archived |
| contact_email | VARCHAR(255) | 否 | 联系邮箱 |
| plan_id | BIGINT | 是 | 当前套餐，外键指向 plan |
| review_note | TEXT | 是 | 审核备注 |
| reviewed_at | DATETIME(6) | 是 | 审核时间 |
| archived_at | DATETIME(6) | 是 | 归档时间 |
| created_at | DATETIME(6) | 否 | 创建时间 |
| updated_at | DATETIME(6) | 否 | 更新时间 |

索引建议：`slug` 唯一；`status`；`plan_id`。

---

### 5.2 用户与租户成员

#### 表：`user_account`（登录账号，平台级）

| 字段名 | 类型 | 空 | 说明 |
|--------|------|----|------|
| id | BIGINT | 否 | 主键 |
| email | VARCHAR(255) | 否 | 登录邮箱，全局唯一 |
| password_hash | VARCHAR(255) | 是 | 若走外部身份则可空 |
| display_name | VARCHAR(128) | 是 | 展示名 |
| is_active | TINYINT | 否 | 是否可用 |
| last_login_at | DATETIME(6) | 是 | 最近登录 |
| created_at | DATETIME(6) | 否 | 创建时间 |
| updated_at | DATETIME(6) | 否 | 更新时间 |

#### 表：`tenant_membership`（用户在某租户下的成员关系）

| 字段名 | 类型 | 空 | 说明 |
|--------|------|----|------|
| id | BIGINT | 否 | 主键 |
| tenant_id | BIGINT | 否 | 租户，外键 tenant |
| user_account_id | BIGINT | 否 | 账号，外键 user_account |
| role | ENUM | 否 | owner、admin、member、viewer |
| created_at | DATETIME(6) | 否 | 加入时间 |

唯一约束：`(tenant_id, user_account_id)`。

---

### 5.3 嵌入模型目录（与知识库向量化选择对应）

#### 表：`embedding_model`（嵌入模型目录，可与 base_model 独立维护）

| 字段名 | 类型 | 空 | 说明 |
|--------|------|----|------|
| id | BIGINT | 否 | 主键 |
| provider | VARCHAR(64) | 否 | 提供方 |
| model_key | VARCHAR(128) | 否 | 嵌入模型键，与调用侧一致 |
| display_name | VARCHAR(256) | 否 | 展示名称 |
| vector_dimension | INT | 否 | 向量维度，用于校验与建索引 |
| is_active | TINYINT | 否 | 是否可选用 |
| extra_config | JSON | 是 | 批大小、端点等 |
| created_at | DATETIME(6) | 否 | 创建时间 |
| updated_at | DATETIME(6) | 否 | 更新时间 |

唯一约束：`(provider, model_key)`。

说明：`knowledge_base.embedding_model_id` 可外键指向本表；`knowledge_base.embedding_model_key` 仍为快速冗余字段，便于迁移期兼容。

---

### 5.4 基座模型与租户绑定

#### 表：`base_model`（平台可接入的基座模型目录）

| 字段名 | 类型 | 空 | 说明 |
|--------|------|----|------|
| id | BIGINT | 否 | 主键 |
| provider | VARCHAR(64) | 否 | 提供方标识，如 openai、local、azure |
| model_key | VARCHAR(128) | 否 | 调用侧模型名或内部键 |
| display_name | VARCHAR(256) | 否 | 展示名称 |
| modality | VARCHAR(32) | 否 | text、multimodal 等 |
| max_context_tokens | INT | 是 | 上下文长度参考 |
| supports_streaming | TINYINT | 否 | 是否支持流式 |
| is_active | TINYINT | 否 | 是否对租户可选 |
| extra_config | JSON | 是 | 路由、区域等扩展 |
| created_at | DATETIME(6) | 否 | 创建时间 |
| updated_at | DATETIME(6) | 否 | 更新时间 |

唯一约束：`(provider, model_key)`。

#### 表：`tenant_model_binding`（租户选用的模型及默认策略）

| 字段名 | 类型 | 空 | 说明 |
|--------|------|----|------|
| id | BIGINT | 否 | 主键 |
| tenant_id | BIGINT | 否 | 租户 |
| base_model_id | BIGINT | 否 | 基座模型 |
| is_default | TINYINT | 否 | 是否默认用于对话 |
| priority | INT | 否 | 同类型下排序，数值小优先 |
| enabled | TINYINT | 否 | 是否启用 |
| created_at | DATETIME(6) | 否 | 创建时间 |
| updated_at | DATETIME(6) | 否 | 更新时间 |

唯一约束建议：同一租户下最多一条 `is_default=1`（可用部分索引或应用层保证）。

---

### 5.5 租户 API 凭证（网关统一接入与鉴权）

#### 表：`tenant_api_credential`

| 字段名 | 类型 | 空 | 说明 |
|--------|------|----|------|
| id | BIGINT | 否 | 主键 |
| tenant_id | BIGINT | 否 | 租户 |
| name | VARCHAR(128) | 否 | 凭证名称，便于租户区分 |
| key_id | VARCHAR(64) | 否 | 公开展示的密钥标识，全局唯一 |
| secret_hash | VARCHAR(255) | 否 | 密钥哈希，不明文存库 |
| status | ENUM | 否 | active、revoked |
| last_used_at | DATETIME(6) | 是 | 最近使用时间 |
| expires_at | DATETIME(6) | 是 | 过期时间，可空表示长期 |
| created_at | DATETIME(6) | 否 | 创建时间 |
| updated_at | DATETIME(6) | 否 | 更新时间 |

索引：`tenant_id`、`key_id` 唯一。

---

### 5.6 微调流水线（占位，首期可只建表不实现）

#### 表：`fine_tune_job`

| 字段名 | 类型 | 空 | 说明 |
|--------|------|----|------|
| id | BIGINT | 否 | 主键 |
| tenant_id | BIGINT | 否 | 租户 |
| base_model_id | BIGINT | 是 | 起始基座 |
| parent_fine_tune_job_id | BIGINT | 是 | 父任务，用于版本血缘 |
| version_label | VARCHAR(128) | 是 | 产出版本标签，便于与租户模型绑定对接 |
| status | ENUM | 否 | draft、queued、running、succeeded、failed、cancelled |
| dataset_storage_key | VARCHAR(1024) | 是 | 训练数据在对象存储中的键 |
| log_storage_key | VARCHAR(1024) | 是 | 训练日志与监控输出在对象存储中的键 |
| output_model_ref | VARCHAR(512) | 是 | 产出模型引用 |
| metrics | JSON | 是 | 自动评估指标 |
| evaluation_summary | TEXT | 是 | 评估结论摘要，便于人工审阅 |
| error_message | TEXT | 是 | 失败原因 |
| started_at | DATETIME(6) | 是 | 开始时间 |
| finished_at | DATETIME(6) | 是 | 结束时间 |
| created_at | DATETIME(6) | 否 | 创建时间 |
| updated_at | DATETIME(6) | 否 | 更新时间 |

---

### 5.7 知识库与版本快照

#### 表：`knowledge_base`

| 字段名 | 类型 | 空 | 说明 |
|--------|------|----|------|
| id | BIGINT | 否 | 主键 |
| tenant_id | BIGINT | 否 | 租户 |
| name | VARCHAR(256) | 否 | 知识库名称 |
| description | TEXT | 是 | 描述 |
| status | ENUM | 否 | active、inactive |
| embedding_model_id | BIGINT | 是 | 外键 embedding_model.id |
| embedding_model_key | VARCHAR(128) | 是 | 嵌入模型键冗余，便于配置迁移 |
| current_snapshot_id | BIGINT | 是 | 当前生效快照，外键 knowledge_base_snapshot |
| created_at | DATETIME(6) | 否 | 创建时间 |
| updated_at | DATETIME(6) | 否 | 更新时间 |

唯一约束：`(tenant_id, name)` 或业务允许重名则仅索引。

#### 表：`knowledge_base_snapshot`（版本快照，用于回滚与审计）

| 字段名 | 类型 | 空 | 说明 |
|--------|------|----|------|
| id | BIGINT | 否 | 主键 |
| knowledge_base_id | BIGINT | 否 | 知识库 |
| version_label | VARCHAR(64) | 否 | 版本号或标签 |
| notes | TEXT | 是 | 说明 |
| created_by_user_id | BIGINT | 是 | 创建人 |
| created_at | DATETIME(6) | 否 | 创建时间 |

---

### 5.8 文档与入库任务

#### 表：`document`（上传的原始文件元数据）

| 字段名 | 类型 | 空 | 说明 |
|--------|------|----|------|
| id | BIGINT | 否 | 主键 |
| tenant_id | BIGINT | 否 | 租户 |
| knowledge_base_id | BIGINT | 否 | 所属知识库 |
| snapshot_id | BIGINT | 是 | 关联快照，入库完成时写入 |
| source_type | ENUM | 否 | file_upload、url_import、api_push |
| source_url | VARCHAR(2048) | 是 | 网页或远程来源地址 |
| original_filename | VARCHAR(512) | 否 | 原始文件名 |
| storage_bucket | VARCHAR(128) | 是 | 桶名 |
| storage_key | VARCHAR(1024) | 否 | 对象存储键 |
| mime_type | VARCHAR(128) | 是 | 类型 |
| size_bytes | BIGINT | 否 | 大小 |
| content_sha256 | CHAR(64) | 是 | 内容哈希，去重可选 |
| parse_status | ENUM | 否 | pending、processing、ready、failed |
| index_status | ENUM | 否 | pending、processing、ready、failed |
| last_error | TEXT | 是 | 最近错误 |
| chunk_profile_json | JSON | 是 | 分块策略参数，如窗口大小、递归深度 |
| extracted_aux_storage_key | VARCHAR(1024) | 是 | OCR、表格等解析侧车文件在对象存储中的键 |
| created_at | DATETIME(6) | 否 | 上传时间 |
| updated_at | DATETIME(6) | 否 | 更新时间 |

索引：`tenant_id`、`knowledge_base_id`、`parse_status`。

#### 表：`ingestion_job`（离线解析与索引进度）

| 字段名 | 类型 | 空 | 说明 |
|--------|------|----|------|
| id | BIGINT | 否 | 主键 |
| tenant_id | BIGINT | 否 | 租户 |
| document_id | BIGINT | 否 | 文档 |
| job_type | ENUM | 否 | parse、chunk、embed、index、full_pipeline |
| status | ENUM | 否 | queued、running、succeeded、failed、cancelled |
| progress_percent | TINYINT | 是 | 0-100 |
| worker_task_id | VARCHAR(128) | 是 | 异步任务标识 |
| attempt_count | INT | 否 | 重试次数 |
| started_at | DATETIME(6) | 是 | 开始时间 |
| finished_at | DATETIME(6) | 是 | 结束时间 |
| error_detail | TEXT | 是 | 错误详情 |
| created_at | DATETIME(6) | 否 | 创建时间 |
| updated_at | DATETIME(6) | 否 | 更新时间 |

---

### 5.9 文本块镜像（便于溯源与运营，向量仍以向量库为准）

#### 表：`document_chunk`

| 字段名 | 类型 | 空 | 说明 |
|--------|------|----|------|
| id | BIGINT | 否 | 主键 |
| tenant_id | BIGINT | 否 | 租户 |
| document_id | BIGINT | 否 | 文档 |
| chunk_index | INT | 否 | 文档内顺序 |
| text_content | MEDIUMTEXT | 否 | 块全文或截断策略由产品决定 |
| char_count | INT | 否 | 字符数 |
| vector_point_id | VARCHAR(128) | 是 | 向量库中的点或片段标识 |
| embedding_model_key | VARCHAR(128) | 是 | 嵌入模型版本键 |
| snapshot_id | BIGINT | 是 | 所属知识库快照 |
| metadata | JSON | 是 | 页码、标题路径等 |
| created_at | DATETIME(6) | 否 | 创建时间 |

唯一约束：`(document_id, chunk_index)`；索引 `tenant_id`、`vector_point_id`。

---

### 5.10 手工知识条目（可选，与文件型知识并列）

#### 表：`knowledge_entry`

| 字段名 | 类型 | 空 | 说明 |
|--------|------|----|------|
| id | BIGINT | 否 | 主键 |
| tenant_id | BIGINT | 否 | 租户 |
| knowledge_base_id | BIGINT | 否 | 知识库 |
| title | VARCHAR(512) | 是 | 标题 |
| body | MEDIUMTEXT | 否 | 正文 |
| status | ENUM | 否 | draft、published、archived |
| snapshot_id | BIGINT | 是 | 发布时关联快照 |
| created_at | DATETIME(6) | 否 | 创建时间 |
| updated_at | DATETIME(6) | 否 | 更新时间 |

#### 表：`knowledge_entry_chunk`（手工条目分块，与向量库一一对应）

| 字段名 | 类型 | 空 | 说明 |
|--------|------|----|------|
| id | BIGINT | 否 | 主键 |
| tenant_id | BIGINT | 否 | 租户 |
| knowledge_entry_id | BIGINT | 否 | 外键 knowledge_entry |
| chunk_index | INT | 否 | 条目内顺序 |
| text_content | MEDIUMTEXT | 否 | 块全文 |
| char_count | INT | 否 | 字符数 |
| vector_point_id | VARCHAR(128) | 是 | 向量库点标识 |
| embedding_model_key | VARCHAR(128) | 是 | 嵌入版本 |
| snapshot_id | BIGINT | 是 | 所属知识库快照 |
| metadata | JSON | 是 | 章节等 |
| created_at | DATETIME(6) | 否 | 创建时间 |

唯一约束：`(knowledge_entry_id, chunk_index)`。

---

### 5.11 终端用户画像（结构化记忆）

#### 表：`end_user_profile`

| 字段名 | 类型 | 空 | 说明 |
|--------|------|----|------|
| id | BIGINT | 否 | 主键 |
| tenant_id | BIGINT | 否 | 租户 |
| external_user_key | VARCHAR(256) | 否 | 租户侧终端用户唯一标识，与业务系统对齐 |
| display_name | VARCHAR(256) | 是 | 展示名 |
| preference_json | JSON | 是 | 偏好与会话约束 |
| tag_json | JSON | 是 | 标签与画像摘要 |
| created_at | DATETIME(6) | 否 | 创建时间 |
| updated_at | DATETIME(6) | 否 | 更新时间 |

唯一约束：`(tenant_id, external_user_key)`。

---

### 5.12 会话与消息

#### 表：`conversation`

| 字段名 | 类型 | 空 | 说明 |
|--------|------|----|------|
| id | BIGINT | 否 | 主键 |
| tenant_id | BIGINT | 否 | 租户 |
| knowledge_base_id | BIGINT | 是 | 绑定的知识库，可空表示通用 |
| user_account_id | BIGINT | 是 | 内部操作者 |
| end_user_profile_id | BIGINT | 是 | 外键 end_user_profile，终端用户结构化记忆 |
| title | VARCHAR(512) | 是 | 会话标题 |
| summary | TEXT | 是 | 摘要，用于长期记忆与列表 |
| status | ENUM | 否 | open、closed |
| last_message_at | DATETIME(6) | 是 | 最后消息时间 |
| created_at | DATETIME(6) | 否 | 创建时间 |
| updated_at | DATETIME(6) | 否 | 更新时间 |

索引：`tenant_id`、`user_account_id`、`last_message_at`。

#### 表：`chat_message`

| 字段名 | 类型 | 空 | 说明 |
|--------|------|----|------|
| id | BIGINT | 否 | 主键 |
| tenant_id | BIGINT | 否 | 租户 |
| conversation_id | BIGINT | 否 | 会话 |
| sequence | INT | 否 | 会话内顺序 |
| role | ENUM | 否 | user、assistant、system、tool |
| content | MEDIUMTEXT | 否 | 正文，结构化可改 JSON |
| used_base_model_id | BIGINT | 是 | 本跳实际使用的推理基座，便于审计与隔离对账 |
| rewritten_query | TEXT | 是 | 查询改写结果，用于在线检索链路 |
| pipeline_trace | JSON | 是 | 意图、召回、混合检索、重排等阶段摘要，便于排障与审计 |
| prompt_tokens | INT | 是 | 本跳提示 Token |
| completion_tokens | INT | 是 | 本跳生成 Token |
| retrieval_refs | JSON | 是 | 引用片段与 document_chunk、knowledge_entry_chunk 或向量 id |
| created_at | DATETIME(6) | 否 | 创建时间 |

唯一约束：`(conversation_id, sequence)`；索引 `tenant_id`、`conversation_id`。

说明：若消息量极大，可将 `content` 大字段迁移至文档数据库或对象存储，本表仅存键与摘要；首期单库可接受时再拆分。

#### 表：`conversation_memory_chunk`（长期记忆：历史对话片段向量化后的镜像）

| 字段名 | 类型 | 空 | 说明 |
|--------|------|----|------|
| id | BIGINT | 否 | 主键 |
| tenant_id | BIGINT | 否 | 租户 |
| conversation_id | BIGINT | 否 | 会话 |
| source_message_id | BIGINT | 是 | 来源消息，外键 chat_message |
| chunk_index | INT | 否 | 会话内记忆块顺序 |
| text_content | MEDIUMTEXT | 否 | 用于嵌入的文本 |
| vector_point_id | VARCHAR(128) | 是 | 向量库中的点标识 |
| embedding_model_key | VARCHAR(128) | 是 | 嵌入版本 |
| created_at | DATETIME(6) | 否 | 创建时间 |

索引：`tenant_id`、`conversation_id`。

---

### 5.13 用量与计量

#### 表：`usage_event`（原始事件，可异步汇总）

| 字段名 | 类型 | 空 | 说明 |
|--------|------|----|------|
| id | BIGINT | 否 | 主键 |
| tenant_id | BIGINT | 否 | 租户 |
| event_type | ENUM | 否 | chat_turn、prompt_tokens、completion_tokens、storage_bytes、api_call |
| quantity | DECIMAL(20,4) | 否 | 数量，含义随类型 |
| unit | VARCHAR(32) | 否 | turns、tokens、bytes、calls |
| conversation_id | BIGINT | 是 | 关联会话 |
| document_id | BIGINT | 是 | 关联文档 |
| reference_id | VARCHAR(128) | 是 | 外部幂等键 |
| occurred_at | DATETIME(6) | 否 | 发生时间 |
| extra | JSON | 是 | 模型名、接口路径等 |

分区建议：按 `occurred_at` 月分区；索引 `tenant_id`、`occurred_at`。

#### 表：`usage_daily_aggregate`（按日汇总，便于限额与报表）

| 字段名 | 类型 | 空 | 说明 |
|--------|------|----|------|
| id | BIGINT | 否 | 主键 |
| tenant_id | BIGINT | 否 | 租户 |
| bucket_date | DATE | 否 | 自然日 |
| chat_turns | BIGINT | 否 | 对话轮次 |
| prompt_tokens | BIGINT | 否 | 提示 Token |
| completion_tokens | BIGINT | 否 | 生成 Token |
| storage_bytes | BIGINT | 否 | 存储量快照或增量 |
| updated_at | DATETIME(6) | 否 | 更新时间 |

唯一约束：`(tenant_id, bucket_date)`。

---

## 6. 向量数据库侧（非关系表，字段约定）

采用「单集合 + 租户与知识库过滤」或「每租户一集合」二选一；下列为每条向量点建议携带的 **载荷字段**。

| 载荷字段 | 类型 | 说明 |
|----------|------|------|
| tenant_id | 整型或字符串 | 与关系库一致 |
| knowledge_base_id | 整型或字符串 | 知识库范围 |
| snapshot_id | 可空 | 快照版本，便于按版本清理 |
| document_id | 整型 | 来源文档 |
| chunk_id | 整型 | 对应 document_chunk 主键 |
| chunk_index | 整型 | 文档内顺序 |
| text | 文本 | 检索后返回与重排用 |
| embedding_model_key | 字符串 | 嵌入版本，重建索引时区分 |
| source_kind | 字符串 | document_chunk、knowledge_entry_chunk、conversation_memory 等，区分集合或过滤 |
| knowledge_entry_id | 可空 | 手工条目来源 |
| conversation_id | 可空 | 长期对话记忆来源 |

向量维度与距离度量在向量库集合创建时配置；HNSW 等参数属运维与性能调优，不单表存储。

**对话历史记忆专用载荷（可与知识库分集合）**：除 `tenant_id` 外，建议必带 `conversation_id`、`source_message_id` 或 `conversation_memory_chunk.id`，以便长期记忆检索后回溯。

---

## 7. 对象存储约定

| 项 | 说明 |
|----|------|
| 桶 | 可按环境分桶；桶内用前缀隔离租户，如 `tenants/{tenant_id}/documents/{document_id}/original` |
| 训练数据 | `tenants/{tenant_id}/fine_tune/{job_id}/dataset.zip` 等 |
| 训练日志 | `tenants/{tenant_id}/fine_tune/{job_id}/logs/` 等，对应 fine_tune_job.log_storage_key |
| 解析侧车 | OCR、表格等，`document.extracted_aux_storage_key` 指向 |
| 不落库二进制 | 关系库仅存 `storage_bucket`、`storage_key`、`content_sha256` |

---

## 8. Redis 键约定（非表结构）

| 用途 | 键模式示例 | 值含义 | 过期 |
|------|------------|--------|------|
| 会话短期上下文 | `tenant:{tid}:conv:{cid}:ctx` | 最近轮次与摘要序列化 | 与会话生命周期一致或可配置 TTL |
| 检索热点 | `tenant:{tid}:kb:{kid}:q:{hash}` | 检索结果缓存 | 短 TTL |
| 分布式锁 | `lock:ingestion:{job_id}` | 占位 | 秒级 |
| 限流计数 | `rl:tenant:{tid}:{window}` | 计数器 | 滑动窗口周期 |

键名中的标识均为逻辑编号，与关系库主键对应。

---

## 9. 外键与一致性说明

- 删除租户为高危操作：建议 **归档** 为主，物理删除需异步任务清理对象存储、向量点、缓存键。
- `knowledge_base.current_snapshot_id` 与快照表需避免循环依赖：可先插入快照再回写知识库，或使用占位快照 id。
- `document_chunk` 与向量点应 **同事务或最终一致**：以 `ingestion_job` 状态与 `document.index_status` 为权威。
- `knowledge_entry_chunk` 与手工条目发布快照一致；停用知识库时不应再向量化新块。
- `conversation.end_user_profile_id` 与 `end_user_profile` 须同租户；终端用户匿名会话可空。
- `chat_message.used_base_model_id` 应落在该租户 `tenant_model_binding` 允许集合内（应用层或约束校验）。
- `conversation_memory_chunk` 与对话记忆向量点一一对应；删除会话时需异步清理向量与缓存。

---

## 10. 首期落地建议

| 优先级 | 表组 |
|--------|------|
| P0 | tenant、plan、user_account、tenant_membership、knowledge_base、knowledge_base_snapshot、document、ingestion_job、conversation、chat_message、base_model、tenant_model_binding、embedding_model |
| P1 | document_chunk、usage_event、usage_daily_aggregate、knowledge_entry、knowledge_entry_chunk、tenant_api_credential、conversation_memory_chunk、end_user_profile |
| P2 | fine_tune_job 及微调相关扩展 |

---

## 11. 修订记录

| 版本 | 日期 | 说明 |
|------|------|------|
| 0.1 | 2026-04-03 | 初稿，供开发准备与评审 |
| 0.2 | 2026-04-03 | 增补产品 markmap、功能点与表字段对照；新增 embedding_model、tenant_api_credential、knowledge_entry_chunk、end_user_profile、conversation_memory_chunk；扩展 document、fine_tune_job、conversation、chat_message；向量载荷补充对话记忆 |
