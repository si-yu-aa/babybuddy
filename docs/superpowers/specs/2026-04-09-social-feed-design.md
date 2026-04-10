# Baby Buddy 家庭社交动态功能设计

## 概述

在 Baby Buddy 中新增一个独立的社交模块，允许家庭成员发布混合内容（文字+照片+视频）的动态，其他成员可以点赞和评论，并接收实时推送通知。

**场景**：家庭内部（完全可信），全局 feed，不与现有追踪系统关联。

---

## 技术方案

使用 **Django + Django Channels (WebSocket)** 实现实时推送。

**新增依赖**：
- `channels` - WebSocket 支持
- `channels-redis` - Channel Layer（消息广播）
- 复用现有的 `django-imagekit` 处理图片缩略图

**架构**：
```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                               │
│   ┌──────────────┐    WebSocket    ┌──────────────────┐   │
│   │  Baby Buddy   │ ←──────────────→│  Django Channels  │   │
│   │  Templates    │                 │  Consumer         │   │
│   └──────────────┘                 └─────────┬────────┘   │
└──────────────────────────────────────────────│─────────────┘
                                               │
                                       ┌───────▼───────┐
                                       │  Redis        │
                                       │  (Channel     │
                                       │   Layer)      │
                                       └───────────────┘
```

---

## 数据模型

### 新增 App：`social`

```
social/
├── models.py
├── views.py
├── serializers.py      # DRF serializers
├── consumers.py         # Channels consumer
├── routing.py           # WebSocket URL routing
└── templates/social/
```

### Post（动态）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | AutoField | 主键 |
| author | ForeignKey(User) | 发布者 |
| content | TextField | 文字内容（可选） |
| media_type | CharField | `image` / `video` / `none` |
| media | ImageField/URLField | 媒体文件 |
| created_at | DateTimeField | 发布时间 |

- 不关联 Child，与现有追踪系统完全独立
- 按 `created_at` 倒序展示

### Comment（评论）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | AutoField | 主键 |
| post | ForeignKey(Post) | 所属动态 |
| author | ForeignKey(User) | 评论者 |
| content | TextField | 评论内容 |
| created_at | DateTimeField | 评论时间 |

### Like（点赞）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | AutoField | 主键 |
| post | ForeignKey(Post) | 所属动态 |
| user | ForeignKey(User) | 点赞者 |
| created_at | DateTimeField | 点赞时间 |

- 同一用户对同一动态只能点赞一次（unique_together）
- 不需要 unlike，用户可以取消点赞

---

## API 设计

### Endpoints

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/social/posts/` | 获取动态列表 |
| POST | `/api/social/posts/` | 发布动态 |
| DELETE | `/api/social/posts/{id}/` | 删除自己的动态 |
| POST | `/api/social/posts/{id}/like/` | 点赞/取消点赞 |
| GET | `/api/social/posts/{id}/comments/` | 获取评论列表 |
| POST | `/api/social/posts/{id}/comments/` | 添加评论 |
| DELETE | `/api/social/comments/{id}/` | 删除自己的评论 |

### Response Format

```json
// GET /api/social/posts/
{
  "results": [
    {
      "id": 1,
      "author": {
        "id": 1,
        "username": "dad",
        "display_name": "爸爸"
      },
      "content": "宝宝今天会走路了！",
      "media_type": "image",
      "media_url": "/media/posts/2026/04/09/baby.jpg",
      "like_count": 2,
      "comment_count": 1,
      "is_liked_by_me": true,
      "created_at": "2026-04-09T10:30:00Z"
    }
  ],
  "next": null
}
```

---

## WebSocket 设计

### 连接路径

```
ws://your-server/ws/social/feed/
```

### Consumer 行为

1. 用户连接时，从 session 获取 user
2. 加入该用户的个人 notification group
3. 接收两种消息：
   - `new_post` - 新动态通知（显示给所有其他在线用户）
   - `new_comment` - 新评论通知（只发给动态作者）

### 消息格式

```json
// 新动态通知（广播给所有在线家庭成员）
{
  "type": "new_post",
  "post": {
    "id": 1,
    "author_username": "mom",
    "author_display": "妈妈",
    "content": "...",
    "media_type": "image",
    "media_url": "...",
    "created_at": "..."
  }
}

// 新评论通知（只发给动态作者）
{
  "type": "new_comment",
  "post_id": 1,
  "comment": {
    "id": 1,
    "author_username": "dad",
    "author_display": "爸爸",
    "content": "太棒了！",
    "created_at": "..."
  }
}
```

---

## 页面/UI 设计

### Feed 页面 (`/social/`)

```
┌─────────────────────────────────────────────────────────┐
│  🏠 Baby Buddy    [Dashboard] [Timeline] [Social]  👤 ▼  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │ [发布新动态]                                      │    │
│  │ 想说点什么？（也可以发照片或视频）                  │    │
│  │                                                 │    │
│  │ [📷 添加图片]  [🎬 添加视频]     [发布]          │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │ 👤 妈妈                              10分钟前    │    │
│  │                                                 │    │
│  │ 宝宝今天第一次自己吃饭！弄得到处都是～            │    │
│  │                                                 │    │
│  │ [图片: baby_eating.jpg]                         │    │
│  │                                                 │    │
│  │ ❤️ 3 赞    💬 2 评论                             │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │ 👤 爸爸                               1小时前   │    │
│  │ 刚量完身高，75cm了！                             │    │
│  │                                                 │    │
│  │ ❤️ 1 赞    💬 0 评论                             │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 实时通知（弹窗）

```
┌──────────────────────────────┐
│ 📢 妈妈发了一条新动态         │
│ "宝宝今天第一次自己吃饭..."   │
│            [查看] [忽略]      │
└──────────────────────────────┘
```

- 通知在屏幕右下角出现
- 3 秒后自动消失（或点击"查看"跳转到 feed）
- 通知仅发给**其他**在线成员，不发给自己

---

## 文件存储

- **图片**：使用现有 `django-imagekit` 处理，存储到 `media/posts/`
- **视频**：存储到 `media/posts/videos/`
- 配置 `ALLOW_UPLOADS=True`（默认已开启）

---

## URL 结构

| 路径 | 说明 |
|------|------|
| `/social/` | Feed 页面（登录后可见） |
| `/api/social/` | REST API |
| `/ws/social/feed/` | WebSocket 连接 |

---

## 权限控制

- 只有登录用户可以访问
- 家庭成员：所有登录用户（由 Baby Buddy 用户系统管理）
- 用户只能删除/编辑自己发布的动态和评论
- 管理员（staff）可以删除任何动态/评论

---

## 实现步骤概述

1. 安装依赖（channels, channels-redis）
2. 配置 Django Channels（settings.py, asgi.py）
3. 创建 `social` Django app
4. 实现 models（Post, Comment, Like）
5. 实现 DRF ViewSets + Serializers
6. 实现 Channels Consumer + Routing
7. 创建前端模板页面
8. 实现 WebSocket 实时通知
9. 添加单元测试

---

## 待确认

- [ ] 是否需要敏感词/内容过滤？（家庭内部场景暂不需要）
- [ ] 视频文件大小限制？（建议 100MB 以内）
- [ ] 是否需要@提及功能？（暂不需要）
