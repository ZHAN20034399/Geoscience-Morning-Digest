# Daily-Ai-Digest

## 🛠️ 使用说明

在使用本项目之前，需要在 GitHub 仓库中配置 **Secrets**。

### 配置路径
进入仓库：
- `Settings` → `Security` → `Secrets and variables` → `Actions`
- 点击 **New repository secret** 创建新的条目

### 必须创建的 Secrets
请创建以下条目：

- **DEEPSEEK_API_KEY**  
  - 用于调用 AI 摘要生成  
  - 可以使用你自己的 API Key  
  - 推荐使用 **OpenAI** 或 **DeepSeek**  
  - 如果使用其他 AI，需要修改 `scripts/` 中的相关代码

- **EMAIL_USER**  
  - 邮箱账号（发件人）

- **EMAIL_PASS**  
  - 邮箱密码或授权码（发件人）

- **SMTP_SERVER**  
  - 邮件服务器地址  
  - 例如：`mail.cugb.edu.cn`

- **SMTP_PORT**  
  - 邮件服务器端口  
  - 常见值：`465` (SSL) 或 `587` (TLS)

---

## 📧 说明
- 邮件会从 `EMAIL_USER` 发送到你指定的收件人（默认就是 `EMAIL_USER` 本身）。  
- 如果需要多人订阅，可以在代码中支持多收件人，或配置邮件列表。  
