# 本地与开源配置说明

## 新使用者配置

1. 在项目根目录复制模板：`cp backend/.env.example backend/.env`。
2. 填写自己的 `DASHSCOPE_API_KEY` 与 `BOCHA_API_KEY`，密钥不带 `Bearer` 前缀。
3. 从百炼控制台复制自己业务空间的 **OpenAI Compatible** 地址到 `LLM_BASE_URL`。业务空间密钥应搭配对应地址；不要复制其他人的空间地址。
4. 默认模型为 `LLM_MAIN_MODEL=deepseek-v4-pro-0813` 和 `LLM_FAST_MODEL=qwen3.8-flash`。需确认自己的账号有模型权限及额度。
5. 配置数据库和随机 `JWT_SECRET_KEY`，按 `UPLOAD_PREPARATION.md` 启动。
6. 修改配置后重启后端。日志会提示密钥是否配置和来源，不输出密钥值。

## 优先级

默认模式：固定读取 `backend/.env`，文件内同名配置覆盖启动环境中的旧值。未写入文件的变量继续使用环境值。

服务器部署：在启动环境设置 `APP_CONFIG_SOURCE=environment`，则已有环境变量优先，文件仅补充缺少项。此开关必须在启动环境设置，不能放入 `.env` 控制自身加载。

`LLM_BASE_URL` 统一兼容旧模块的 `DASHSCOPE_BASE_URL`、`OPENAI_BASE_URL`；主模型、快速模型分别映射普通聊天和记忆模块的旧变量。DeepResearch 各 Agent 从统一配置读取模型。

## GitHub 上传边界

- 上传源代码、测试、本说明和 `.env.example`；模板中的真实密钥必须留空。
- `.env`、`.local/` 数据库、依赖、日志、备份不上传。旧备份位于项目之外，不要在父目录初始化仓库。
- 首次提交前先检查 `git status --short` 和 `git diff --cached`，确认没有凭证、个人业务数据或包含密钥的截图。
- 项目目前没有初始化 Git，也没有上传远程仓库。本轮仅完成配置和模型迁移。

## 当前验证边界

配置优先级、博查 Bearer 前缀规范化、模型选择可离线验证；模型权限、额度以及接口参数兼容性仍需真实调用验证。本轮没有执行付费 API 调用。

搜索无事实时现在继续生成带明确提示的参考草稿；检查点 Queue 序列化问题已修复并通过本地数据库验证。审核失败状态展示仍需单独处理。完成真实搜索、报告引用、历史恢复测试之后，再录制成功演示。
