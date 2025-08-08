
<h1 align="center">Telegram Media Downloader</h1>

<p align="center">
<a href="https://github.com/tangyoha/telegram_media_downloader/actions"><img alt="Unittest" src="https://github.com/tangyoha/telegram_media_downloader/workflows/Unittest/badge.svg"></a>
<a href="https://codecov.io/gh/tangyoha/telegram_media_downloader"><img alt="Coverage Status" src="https://codecov.io/gh/tangyoha/telegram_media_downloader/branch/master/graph/badge.svg"></a>
<a href="https://github.com/tangyoha/telegram_media_downloader/blob/master/LICENSE"><img alt="License: MIT" src="https://black.readthedocs.io/en/stable/_static/license.svg"></a>
<a href="https://github.com/python/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
<a href="https://github.com/tangyoha/telegram_media_downloader/releases">
<img alt="Code style: black" src="https://img.shields.io/github/v/release/tangyoha/telegram_media_downloader?display_name=tag"></a>
</p>

<h3 align="center">
  <a href="./README_CN.md">中文</a><span> · </span>
  <a href="https://github.com/tangyoha/telegram_media_downloader/discussions/categories/ideas">Feature request</a>
  <span> · </span>
  <a href="https://github.com/tangyoha/telegram_media_downloader/issues">Report a bug</a>
  <span> · </span>
  Support: <a href="https://github.com/tangyoha/telegram_media_downloader/discussions">Discussions</a>
  <span> & </span>
  <a href="https://t.me/TeegramMediaDownload">Telegram Community</a>
</h3>

## Overview
> Support two default running

* The robot is running, and the command `download` or `forward` is issued from the robot

* Download as a one-time download tool

### UI

#### Web page

> After running, open a browser and visit `localhost:5000`
> If it is a remote machine, you need to configure web_host: 0.0.0.0


<img alt="Code style: black" style="width:100%; high:60%;" src="./screenshot/web_ui.gif"/>

### Robot

> Need to configure bot_token, please refer to [Documentation](https://github.com/tangyoha/telegram_media_downloader/wiki/How-to-Download-Using-Robots)

<img alt="Code style: black" style="width:60%; high:30%; " src="./screenshot/bot.gif"/>

### Support

| Category             | Support                                          |
| -------------------- | ------------------------------------------------ |
| Language             | `Python 3.7` and above                           |
| Download media types | audio, document, photo, video, video_note, voice |

### Version release plan

* [v2.2.0](https://github.com/tangyoha/telegram_media_downloader/issues/2)

## Installation

For *nix os distributions with `make` availability

```sh
git clone https://github.com/tangyoha/telegram_media_downloader.git
cd telegram_media_downloader
make install
```

For Windows which doesn't have `make` inbuilt

```sh
git clone https://github.com/tangyoha/telegram_media_downloader.git
cd telegram_media_downloader
pip3 install -r requirements.txt
```

## Docker
> For more detailed installation tutorial, please check the wiki

Make sure you have **docker** and **docker-compose** installed
```sh
docker pull supresong/telegram_media_downloader:latest
mkdir -p ~/app && mkdir -p ~/app/log/ && cd ~/app
wget https://raw.githubusercontent.com/supresong/telegram_media_downloader/master/docker-compose.yaml -O docker-compose.yaml
wget https://raw.githubusercontent.com/supresong/telegram_media_downloader/master/config.yaml -O config.yaml
wget https://raw.githubusercontent.com/supresong/telegram_media_downloader/master/data.yaml -O data.yaml
# vi config.yaml and docker-compose.yaml
vi config.yaml

# The first time you need to start the foreground
# enter your phone number and code, then exit(ctrl + c)
docker-compose run --rm telegram_media_downloader

# After performing the above operations, all subsequent startups will start in the background
docker-compose up -d

# Upgrade
docker pull supresong/telegram_media_downloader:latest
cd ~/app
docker-compose down
docker-compose up -d
```

## Upgrade installation

```sh
cd telegram_media_downloader
pip3 install -r requirements.txt
```

## Configuration

All the configurations are  passed to the Telegram Media Downloader via `config.yaml` file.

**Getting your API Keys:**
The very first step requires you to obtain a valid Telegram API key (API id/hash pair):

1. Visit  [https://my.telegram.org/apps](https://my.telegram.org/apps)  and log in with your Telegram Account.
2. Fill out the form to register a new Telegram application.
3. Done! The API key consists of two parts:  **api_id**  and  **api_hash**.

**Getting chat id:**

**1. Using web telegram:**

1. Open <https://web.telegram.org/?legacy=1#/im>

2. Now go to the chat/channel and you will see the URL as something like
   - `https://web.telegram.org/?legacy=1#/im?p=u853521067_2449618633394` here `853521067` is the chat id.
   - `https://web.telegram.org/?legacy=1#/im?p=@somename` here `somename` is the chat id.
   - `https://web.telegram.org/?legacy=1#/im?p=s1301254321_6925449697188775560` here take `1301254321` and add `-100` to the start of the id => `-1001301254321`.
   - `https://web.telegram.org/?legacy=1#/im?p=c1301254321_6925449697188775560` here take `1301254321` and add `-100` to the start of the id => `-1001301254321`.

**2. Using bot:**

1. Use [@username_to_id_bot](https://t.me/username_to_id_bot) to get the chat_id of
    - almost any telegram user: send username to the bot or just forward their message to the bot
    - any chat: send chat username or copy and send its joinchat link to the bot
    - public or private channel: same as chats, just copy and send to the bot
    - id of any telegram bot

### config.yaml

```yaml
api_hash: your_api_hash
api_id: your_api_id
chat:
- chat_id: telegram_chat_id
  last_read_message_id: 0
  download_filter: message_date >= 2022-12-01 00:00:00 and message_date <= 2023-01-17 00:00:00
- chat_id: telegram_chat_id_2
  last_read_message_id: 0
# note we remove ids_to_retry to data.yaml
ids_to_retry: []
media_types:
- audio
- document
- photo
- video
- voice
- animation #gif
file_formats:
  audio:
  - all
  document:
  - pdf
  - epub
  video:
  - mp4
save_path: D:\telegram_media_downloader
file_path_prefix:
- chat_title
- media_datetime
upload_drive:
  # required
  enable_upload_file: true
  # required
  remote_dir: drive:/telegram
  # required
  upload_adapter: rclone
  # option,when config upload_adapter rclone then this config are required
  rclone_path: D:\rclone\rclone.exe
  # option,when config upload_adapter pan123 then this config are required
  client_id: your_123pan_client_id
  client_secret: your_123pan_client_secret
  # option
  before_upload_file_zip: True
  # option
  after_upload_file_delete: True
hide_file_name: true
file_name_prefix:
- message_id
- file_name
file_name_prefix_split: ' - '
max_download_task: 5
web_host: 127.0.0.1
web_port: 5000
language: EN
web_login_secret: 123
allowed_user_ids:
- 'me'
date_format: '%Y_%m'
enable_download_txt: false
```

- **api_hash**  - The api_hash you got from telegram apps
- **api_id** - The api_id you got from telegram apps
- **bot_token** - Your bot token
- **chat** - Chat list
  - `chat_id` -  The id of the chat/channel you want to download media. Which you get from the above-mentioned steps.
  - `download_filter` - Download filter, see [How to use Filter](https://github.com/tangyoha/telegram_media_downloader/wiki/How-to-use-Filter)
  - `last_read_message_id` - If it is the first time you are going to read the channel let it be `0` or if you have already used this script to download media it will have some numbers which are auto-updated after the scripts successful execution. Don't change it.
  - `ids_to_retry` - `Leave it as it is.` This is used by the downloader script to keep track of all skipped downloads so that it can be downloaded during the next execution of the script.
- **media_types** - Type of media to download, you can update which type of media you want to download it can be one or any of the available types.
- **file_formats** - File types to download for supported media types which are `audio`, `document` and `video`. Default format is `all`, downloads all files.
- **save_path** - The root directory where you want to store downloaded files.
- **file_path_prefix** - Store file subfolders, the order of the list is not fixed, can be randomly combined.
  - `chat_title`      - Channel or group title, it will be chat id if not exist title.
  - `media_datetime`  - Media date.
  - `media_type`      - Media type, also see `media_types`.
- **upload_drive** - You can upload file to cloud drive.
  - `enable_upload_file` - Enable upload file, default `false`.
  - `remote_dir` - Where you upload, like `drive_id/drive_name`.
  - `upload_adapter` - Upload file adapter, which can be `rclone`, `aligo`, `pan123`. If it is `rclone`, it supports all `rclone` servers that support uploading. If it is `aligo`, it supports uploading `Ali cloud disk`. If it is `pan123`, it supports uploading to `123云盘`.
  - `rclone_path` - RClone exe path, see [How to use rclone](https://github.com/tangyoha/telegram_media_downloader/wiki/Rclone)
  - `client_id` - 123云盘开放平台应用的Client ID，当`upload_adapter`为`pan123`时必填
  - `client_secret` - 123云盘开放平台应用的Client Secret，当`upload_adapter`为`pan123`时必填
  - `before_upload_file_zip` - Zip file before upload, default `false`.
  - `after_upload_file_delete` - Delete file after upload success, default `false`.
- **file_name_prefix** - Custom file name, use the same as **file_path_prefix**
  - `message_id` - Message id
  - `file_name` - File name (may be empty)
  - `caption` - The title of the message (may be empty)
- **file_name_prefix_split** - Custom file name prefix symbol, the default is `-`
- **max_download_task** - The maximum number of task download tasks, the default is 5.
- **hide_file_name** - Whether to hide the web interface file name, default `false`
- **web_host** - Web host
- **web_port** - Web port
- **language** - Application language, the default is English (`EN`), optional `ZH`(Chinese),`RU`,`UA`
- **web_login_secret** - Web page login password, if not configured, no login is required to access the web page
- **log_level** - see `logging._nameToLevel`.
- **forward_limit** - Limit the number of forwards per minute, the default is 33, please do not modify this parameter by default.
- **allowed_user_ids** - Who is allowed to use the robot? The default login account can be used. Please add single quotes to the name with @.
- **date_format** Support custom configuration of media_datetime format in file_path_prefix.see [python-datetime](https://docs.python.org/3/library/datetime.html)
- **enable_download_txt** Enable download txt file, default `false`

## Execution

```sh
python3 media_downloader.py
```

All downloaded media will be stored at the root of `save_path`.
The specific location reference is as follows:

The complete directory of video download is: `save_path`/`chat_title`/`media_datetime`/`media_type`.
The order of the list is not fixed and can be randomly combined.
If the configuration is empty, all files are saved under `save_path`.

## Proxy

`socks4, socks5, http` proxies are supported in this project currently. To use it, add the following to the bottom of your `config.yaml` file

```yaml
proxy:
  scheme: socks5
  hostname: 127.0.0.1
  port: 1234
  username: your_username(delete the line if none)
  password: your_password(delete the line if none)
```

If your proxy doesn't require authorization you can omit username and password. Then the proxy will automatically be enabled.

## 123云盘配置说明 (123pan Cloud Drive Configuration)

### 申请123云盘开发者账号

1. 访问 [123云盘开放平台](https://www.123pan.com/developer)
2. 注册并登录开发者账号
3. 创建应用，获取 `Client ID` 和 `Client Secret`

### 配置示例

```yaml
upload_drive:
  enable_upload_file: true
  upload_adapter: pan123
  remote_dir: "/telegram"
  client_id: "your_123pan_client_id"
  client_secret: "your_123pan_client_secret"
  before_upload_file_zip: false
  after_upload_file_delete: true
```

### 功能特性

- ✅ **秒传检测** - 基于MD5校验，相同文件无需重复上传
- ✅ **分片上传** - 支持大文件(≥1GB)自动分片上传
- ✅ **单步上传** - 小文件(<1GB)直接上传，速度更快
- ✅ **进度监控** - 实时显示上传进度
- ✅ **自动重试** - 网络异常时自动重试上传
- ✅ **路径映射** - 自动创建远程目录结构
- ✅ **文件压缩** - 支持上传前压缩文件
- ✅ **自动清理** - 上传成功后可选择删除本地文件

### 配置参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `enable_upload_file` | boolean | 是 | 启用文件上传功能 |
| `upload_adapter` | string | 是 | 设置为 "pan123" |
| `remote_dir` | string | 是 | 云盘根目录，如 "/telegram" |
| `client_id` | string | 是 | 123云盘应用的Client ID |
| `client_secret` | string | 是 | 123云盘应用的Client Secret |
| `before_upload_file_zip` | boolean | 否 | 上传前是否压缩文件 |
| `after_upload_file_delete` | boolean | 否 | 上传成功后是否删除本地文件 |

### 注意事项

1. **API限制** - 123云盘API有频率限制，请勿频繁调用
2. **文件大小** - 单文件最大支持10GB（开发者权限）
3. **存储空间** - 请确保123云盘有足够的存储空间
4. **网络环境** - 建议在稳定的网络环境下使用

## Contributing

### Contributing Guidelines

Read through our [contributing guidelines](https://github.com/tangyoha/telegram_media_downloader/blob/master/CONTRIBUTING.md) to learn about our submission process, coding rules and more.

### Want to Help?

Want to file a bug, contribute some code, or improve documentation? Excellent! Read up on our guidelines for [contributing](https://github.com/tangyoha/telegram_media_downloader/blob/master/CONTRIBUTING.md).

### Code of Conduct

Help us keep Telegram Media Downloader open and inclusive. Please read and follow our [Code of Conduct](https://github.com/tangyoha/telegram_media_downloader/blob/master/CODE_OF_CONDUCT.md).


### Sponsor

[PayPal](https://paypal.me/tangyoha?country.x=C2&locale.x=zh_XC)

<p>
<img alt="Code style: black" style="width:30%" src="./screenshot/alipay.JPG">
<img alt="Code style: black" style="width:30%" src="./screenshot/wechat.JPG">
</p>
