# Telegram 每日自动签到

**简体中文** | [English](README.en.md)

每天手动给机器人发签到指令，容易忘，也有点麻烦。这个小工具用你的 **Telegram 个人账号**，每天自动向指定聊天发送签到指令。不同机器人可以配置不同指令，一次设置，之后由 GitHub Actions 定时运行。

默认时间：**每天墨尔本时间 00:00**（`Australia/Melbourne`，自动适配夏令时）。无需 Telegram Premium，也不用让电脑一直开机。

## 功能介绍

- **个人账号发送**：通过 Telethon 登录你的账号，不需要创建 Telegram Bot。
- **分别配置指令**：每个接收方都可以设置自己的消息，例如 `/qd`、`/sign`、`/checkin`。
- **每天自动运行**：GitHub Actions 负责定时启动，发送结束后退出。
- **按顺序发送**：相邻两次发送间隔 10 秒，最多配置 20 个接收方。
- **先检查，再启用**：默认命令只检查配置；新部署需要设置开关后才会发送。

## 快速开始

### 1. 准备项目

将项目放到你自己的 **GitHub 私有仓库**，文件位于仓库根目录。记得保留隐藏目录 `.github` 和文件 `.gitignore`，定时任务在 `.github/workflows/daily.yml` 中。

本地准备 Python 3.12 或更新版本，在项目目录执行：

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### 2. 获取 Telegram API 信息

打开 [my.telegram.org](https://my.telegram.org)，登录后进入 **API development tools**，创建应用，记下 `api_id` 和 `api_hash`。

这两项用于连接 Telegram。不要写进代码，也不要提交到仓库。

### 3. 生成登录会话

在自己的电脑上执行：

```sh
python check_in.py --setup
```

按提示输入 API ID、API hash、带国家区号的手机号、Telegram 登录验证码，以及两步验证密码（如已开启）。输入时不会显示字符，正常输入后按回车即可。

登录成功后，会生成 `session-secret.txt`。文件保存的是 **StringSession 登录会话**，后续任务可以复用它，不用每天输入验证码。这个步骤只登录，不发送消息。

**会话相当于账号的登录凭证。** 不要发给别人、粘贴到聊天中，或上传到仓库。脚本会以仅当前用户可读写的权限创建文件，`.gitignore` 也已将它排除。

### 4. 配置签到指令

编辑 [config.json](config.json)，将用户名和对应指令写入 `recipients`：

```json
{
  "recipients": {
    "@alice": "/qd",
    "@bobbb": "/sign",
    "me": "/checkin"
  }
}
```

以上是格式示例，请换成你要使用的接收方。`me` 表示自己的“收藏夹”（Saved Messages）。当前项目已有配置，使用前核对即可。

- 支持公开 `@用户名` 和 `me`，不支持手机号或数字 ID。
- 用户名不区分大小写；相同用户名、相同消息会合并，消息冲突则报错。
- 每条消息不能为空，长度上限为 4096 个 UTF-16 代码单元。
- 消息按纯文本发送，不启用链接预览。
- 用户名可能变更或转让，请及时更新配置。

如果不想把接收方写进仓库，可以使用下方的 `TELEGRAM_RECIPIENTS` Secret 覆盖配置。本地也可复制一份为 `config.local.json`，再执行 `python check_in.py --config config.local.json`；这个文件已被 Git 忽略。

### 5. 添加 GitHub Secrets

进入仓库的 **Settings → Secrets and variables → Actions → Secrets**，点击 **New repository secret**，添加：

| 名称 | 填写内容 | 是否必填 |
| --- | --- | --- |
| `TELEGRAM_API_ID` | Telegram API ID | 是 |
| `TELEGRAM_API_HASH` | Telegram API hash | 是 |
| `TELEGRAM_SESSION` | `session-secret.txt` 的完整内容 | 是 |
| `TELEGRAM_RECIPIENTS` | 用户名与消息组成的 JSON 对象，如 `{"@alice":"/qd"}` | 否 |

`TELEGRAM_RECIPIENTS` 非空时，会整体替换 `config.json` 中的接收方配置；未设置或为空时，使用文件中的配置。

在 macOS 上，可以用下面的命令复制会话，不必在终端显示内容：

```sh
pbcopy < session-secret.txt
```

粘贴到 GitHub Secret 并保存后，删除本地 `session-secret.txt`。手机号、验证码和两步验证密码不需要上传到 GitHub；API 信息和会话也只能放在 Secrets 中，不能提交到代码里。

### 6. 检查并开启自动签到

先在本地检查：

```sh
python -m unittest -v
python check_in.py
```

这两条命令都不会连接 Telegram，也不会发送消息。

然后打开仓库的 **Actions → Daily Telegram check-in → Run workflow**，先不要勾选 **Send real messages**，运行一次配置检查。

检查通过后，进入 **Settings → Secrets and variables → Actions → Variables**，新建仓库变量：

| 名称 | 值 |
| --- | --- |
| `CHECK_IN_ENABLED` | `true` |

设置后，下一次定时任务就会发送。需要立即测试时，再手动运行工作流，并勾选 **Send real messages**；只有开关为 `true` 且勾选发送时，手动运行才会发消息。

## 修改签到时间

编辑 [.github/workflows/daily.yml](.github/workflows/daily.yml) 中的：

```yaml
schedule:
  - cron: '0 0 * * *'
    timezone: Australia/Melbourne
```

当前配置为每天墨尔本时间 00:00。修改 `cron` 即可调整时间；时区设置会自动处理夏令时。

GitHub 定时任务可能延迟，繁忙时也可能漏跑，**不保证准点到秒**。工作流必须放在默认分支。公开仓库连续 60 天没有活动时，定时任务可能被自动停用；私有仓库不受这一闲置规则影响。运行费用取决于你的 GitHub Actions 额度和计费设置。

## 常见问题

### 怎么暂停？

把仓库变量 `CHECK_IN_ENABLED` 改为 `false`，或在 Actions 页面停用工作流。已经开始运行的任务需要单独取消。

### 显示发送成功，就代表签到成功了吗？

不一定。发送成功表示 Telegram 接受了消息；机器人是否签到成功、是否发放奖励，要以聊天中的回复为准。脚本不会读取或判断机器人回复。

### 发送失败会自动重试吗？

脚本会先解析全部接收方，再开始发送。如果 Telegram 返回不超过 60 秒的 FloodWait，会等待后重试一次；等待时间过长、再次限流或遇到其他错误时，会停止本次任务。

失败前可能已有部分消息发出，网络中断也可能导致发送结果不确定。**重试前先检查聊天记录**，避免重复发送。GitHub 的“重新运行”会跳过发送步骤，但新建一次手动运行仍可能重复发送当天的指令。脚本没有自动补签，也不保证每条消息恰好发送一次。

### 登录会话失效怎么办？

在本地重新运行 `python check_in.py --setup`，生成新会话，再更新 `TELEGRAM_SESSION`。如果旧的 `session-secret.txt` 仍在，需要先移走或删除它。若要撤销会话，可在 Telegram 的 **设置 → 设备** 中终止对应登录。

### 能在本地直接发送吗？

可以。通过安全方式设置 `TELEGRAM_API_ID`、`TELEGRAM_API_HASH` 和 `TELEGRAM_SESSION` 环境变量后，执行：

```sh
python check_in.py --send
```

这条命令会真实发送消息。不要把凭证直接写进命令参数或 Shell 历史记录。

## 相关文档

- [GitHub Actions 定时任务](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [Telethon 登录会话](https://docs.telethon.dev/en/stable/concepts/sessions.html)
- [Telethon FloodWait 处理](https://docs.telethon.dev/en/stable/quick-references/faq.html#how-can-i-except-floodwaiterror)
