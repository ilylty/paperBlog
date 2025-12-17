<!-- 
title: "博客访问统计功能"
categories: ["建站"]
tags: ["Cloudflare", "Pages", "KV", "JavaScript", "博客优化"]
cover_image: ""
summary: "利用 Cloudflare Pages 和 KV 存储，实现日志记录和阅读量统计功能。"
-->
# 一个博客访问日志功能

最近刚弄好一个博客，总感觉缺了点什么，想加个访问日志的功能。

本来想着自己搞个后端，但摸摸口袋没钱买域名。于是转头看了看赛博皇帝 Cloudflare，主要有两个路子：
1.  **Worker**
2.  **Pages**

奈何 Worker 的被墙，普通用户一般也不会科学上网，所以最后选了 **Pages**。虽然 Pages 的 Functions 有点难用，但为了访问速度忍了。

构思了一下数据结构，打算直接把数据存在 **KV** 里。
API 方面大概是这样：
*   有个 `stat` 接口用来触发记录功能。
*   `post-info` 获取单篇文章阅读量。
*   `home-info` 获取全站总数。
*   还得有个获取 KV 所有数据的接口，加个 UUID 当密钥，顺便用 SSE 流式传输，这样端侧处理快一点。

于是让 AI 帮我细化一下接口。

## 1. 接口列表

### 记录访问 (上报)
用于在页面加载时记录访客数据（自动记录 IP、UA、国家、时间戳）。

- **URL**: `/stat`
- **Method**: `POST`
- **Header**: `Content-Type: application/json`
- **Body**:
  ```json
  {
    "url": "/posts/hello-world"  // 当前页面的路径
  }
  ```
- **Response**:
  ```json
  { "status": "ok" }
  ```

### 获取单页访问量
用于在文章标题下显示“阅读量”。

- **URL**: `/post-info`
- **Method**: `GET`
- **Params**:
  - `url`: 需要查询的页面路径 (例如 `/posts/hello-world`)
- **Response**:
  ```json
  {
    "url": "/posts/hello-world",
    "count": 1024
  }
  ```

### 获取全站总访问量
用于在页脚显示“本站总访客”。

- **URL**: `/home-info`
- **Method**: `GET`
- **Response**:
  ```json
  {
    "total": 5000
  }
  ```

### 导出所有数据 (管理员)
流式返回所有存储的 KV 数据（包含日志明细）。

- **URL**: `/<你的SECRET_UUID>`
- **Method**: `GET`
- **Format**: Server-Sent Events (SSE)
- **Response**: 流式 JSON 文本

---

## 2. 实现过程

接着直接让 Gemini 一把梭。
结果……瞎写。Gemini 瞎写 Pages 的结构，给我整了个 `functions/[[path]].js` 这种目录结构。
```bash
index.html
functions/[[path]].js
```
测了几次都不行，路由通不了。

我上网找了个 Page 的通用模板，打算基于这个改。
这个模板是这样的：

```javascript
/**
 * Universal Cloudflare Pages Template (_worker.js)
 *
 * - Intercepts all requests for the project.
 * - Provides httpbin.org-like functionality for /get and /post.
 * - Returns a JSON 404 for any other route.
 * - Perfect for building APIs on Cloudflare Pages.
 */

export default {
  /**
   * The main fetch handler for all incoming requests.
   * @param {Request} request The incoming request object
   * @param {object} env Environment variables and bindings (KV, D1, etc.)
   * @param {object} ctx Execution context
   * @returns {Promise<Response>} A response promise
   */
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;
    const method = request.method;

    // --- Main Router ---
    if (path === '/get' && method === 'GET') {
      return handleGetRequest(request);
    }

    if (path === '/post' && method === 'POST') {
      return await handlePostRequest(request);
    }

    // --- 404 Not Found Handler for all other routes ---
    return JsonResponse({
        error: 'Not Found',
        message: `The route '${path}' with method '${method}' was not found.`,
      },
      404
    );
  },
};

/**
 * Handles GET requests to /get
 * @param {Request} request
 * @returns {Response}
 */
function handleGetRequest(request) {
  const url = new URL(request.url);
  const responseData = {
    args: Object.fromEntries(url.searchParams),
    headers: Object.fromEntries(request.headers),
    origin: request.headers.get('cf-connecting-ip'),
    url: request.url,
  };
  return JsonResponse(responseData);
}

/**
 * Handles POST requests to /post
 * @param {Request} request
 * @returns {Promise<Response>}
 */
async function handlePostRequest(request) {
  const url = new URL(request.url);
  const baseResponse = {
    args: Object.fromEntries(url.searchParams),
    headers: Object.fromEntries(request.headers),
    origin: request.headers.get('cf-connecting-ip'),
    url: request.url,
    json: null,
    form: {},
    data: '',
  };

  const contentType = request.headers.get('content-type') || '';

  try {
    if (contentType.includes('application/json')) {
      baseResponse.json = await request.json();
    } else if (contentType.includes('application/x-www-form-urlencoded')) {
      const formData = await request.formData();
      baseResponse.form = Object.fromEntries(formData);
    } else {
      // For multipart/form-data or plain text
      baseResponse.data = await request.text();
    }
  } catch (error) {
    return JsonResponse({
      error: 'Invalid body content',
      message: error.message
    }, 400);
  }

  return JsonResponse(baseResponse);
}

/**
 * A helper function to create a JSON response.
 * @param {object} data The data to serialize as JSON.
 * @param {number} status The HTTP status code.
 * @returns {Response}
 */
function JsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: {
      'Content-Type': 'application/json',
      // Add CORS headers for API accessibility
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}
```

## 3. 最终代码实现

把上面这个模板和我的 API 需求喂给 AI，最终代码就有了：

```javascript
/**
 * Blog Stats API using Cloudflare Pages Advanced Mode (_worker.js)
 *
 * Required Cloudflare Pages Settings:
 * 1. KV Namespace Binding:
 *    - Variable name: BLOG_STATS
 *    - KV namespace: (select your created KV namespace)
 * 2. Environment Variable:
 *    - Variable name: SECRET_UUID
 *    - Value: (your secret UUID for data export)
 */

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;
    const method = request.method;

    // Handle CORS preflight requests
    if (method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders() });
    }

    try {
      // --- Main Router ---
      if (path === '/stat' && method === 'POST') {
        return await handleStatRequest(request, env, ctx);
      }

      if (path === '/post-info' && method === 'GET') {
        return await handlePostInfoRequest(request, env);
      }

      if (path === '/home-info' && method === 'GET') {
        return await handleHomeInfoRequest(request, env);
      }
      
      if (env.SECRET_UUID && path === `/${env.SECRET_UUID}`) {
        return handleExportRequest(request, env, ctx);
      }

      // --- 404 Not Found Handler ---
      return JsonResponse({
          error: 'Not Found',
          message: `The route '${path}' does not exist.`
        }, 404);
        
    } catch (e) {
      console.error(e);
      return JsonResponse({ error: 'Internal Server Error', message: e.message }, 500);
    }
  },
};

// --- Route Handlers ---

async function handleStatRequest(request, env, ctx) {
  let body;
  try {
    body = await request.json();
  } catch (e) {
    return JsonResponse({ error: "Invalid JSON in request body" }, 400);
  }

  const targetUrl = body.url;
  if (!targetUrl) {
    return JsonResponse({ error: "Missing 'url' in request body" }, 400);
  }

  const ip = request.headers.get("CF-Connecting-IP") || "unknown";
  const ua = request.headers.get("User-Agent") || "unknown";
  const country = request.cf ? request.cf.country : "unknown";
  const timestamp = Date.now();
  const pageKey = getPageKey(targetUrl);

  // Use ctx.waitUntil to perform tasks after the response has been sent
  ctx.waitUntil(Promise.all([
    incrementCounter(env, "site_total"),
    incrementCounter(env, `page_view::${pageKey}`),
    env.BLOG_STATS.put(
      `log::${timestamp}::${crypto.randomUUID().split('-')[0]}`,
      JSON.stringify({ ts: timestamp, ip, ua, ref: pageKey, loc: country }),
      { expirationTtl: 60 * 60 * 24 * 30 } // Expire logs after 30 days
    )
  ]));

  return JsonResponse({ status: "ok" });
}

async function handlePostInfoRequest(request, env) {
  const url = new URL(request.url);
  const targetUrl = url.searchParams.get("url");
  if (!targetUrl) {
    return JsonResponse({ error: "Missing 'url' query parameter" }, 400);
  }
  
  const pageKey = getPageKey(targetUrl);
  const count = await env.BLOG_STATS.get(`page_view::${pageKey}`);
  
  return JsonResponse({ url: pageKey, count: Number(count || 0) });
}

async function handleHomeInfoRequest(request, env) {
  const total = await env.BLOG_STATS.get("site_total");
  return JsonResponse({ total: Number(total || 0) });
}

function handleExportRequest(request, env, ctx) {
  const { readable, writable } = new TransformStream();
  const writer = writable.getWriter();
  const encoder = new TextEncoder();

  // Stream all KV data in the background
  ctx.waitUntil((async () => {
    try {
      let cursor = null;
      let listComplete = false;
      while (!listComplete) {
        const listResult = await env.BLOG_STATS.list({ limit: 1000, cursor });
        for (const key of listResult.keys) {
          const value = await env.BLOG_STATS.get(key.name);
          const msg = JSON.stringify({ key: key.name, value: parseValue(value) });
          await writer.write(encoder.encode(`data: ${msg}\n\n`));
        }
        if (listResult.list_complete) {
          listComplete = true;
        } else {
          cursor = listResult.cursor;
        }
      }
      await writer.write(encoder.encode("event: close\ndata: end\n\n"));
    } catch (e) {
      await writer.write(encoder.encode(`event: error\ndata: ${e.message}\n\n`));
    } finally {
      await writer.close();
    }
  })());

  return new Response(readable, {
    status: 200,
    headers: {
      ...corsHeaders(),
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "Connection": "keep-alive",
    },
  });
}


// --- Helper Functions ---

/**
 * Creates a JSON response with appropriate headers.
 * @param {object} data The data to serialize.
 * @param {number} status The HTTP status code.
 * @returns {Response}
 */
function JsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: {
      ...corsHeaders(),
      'Content-Type': 'application/json',
    },
  });
}

/**
 * Returns a standard set of CORS headers.
 * @returns {object}
 */
function corsHeaders() {
    return {
      'Access-Control-Allow-Origin': '*', // For production, lock this down to your blog's domain
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    };
}

async function incrementCounter(env, key) {
  const current = await env.BLOG_STATS.get(key);
  await env.BLOG_STATS.put(key, (Number(current || 0) + 1).toString());
}

function parseValue(val) {
  try {
    return JSON.parse(val);
  } catch (e) {
    return val;
  }
}

function getPageKey(urlStr) {
  try {
    // A dummy base is needed if the URL is just a path like "/about/"
    const u = new URL(urlStr, "http://dummy.com"); 
    let pathname = u.pathname;
    // Normalize by removing trailing slash if it's not the root
    if (pathname.length > 1 && pathname.endsWith("/")) {
      pathname = pathname.slice(0, -1);
    }
    return pathname === "" ? "/" : pathname;
  } catch (e) {
    return "unknown_path";
  }
}
```

这边我命名 `_worker.js`, 再压个 `.zip` 包。

这边我们记一下 KV 名和变量名，后面要配置。
![](assets/images/17-BlogStats/Pasted%20image%2020251217233218.png)

## 4. 部署操作

接着打开 Cloudflare：
```bash
https://dash.cloudflare.com/
```

### 第一步：创建 KV
先创建一个 KV，命名空间名称随便取，把名称记住。

| ![](assets/images/17-BlogStats/Pasted%20image%2020251217231640.png) | ![](assets/images/17-BlogStats/Pasted%20image%2020251217231730.png) |
| ------------------------------------ | ------------------------------------ |
| ![](assets/images/17-BlogStats/Pasted%20image%2020251217231832.png) |                                      |

### 第二步：创建 Pages
再创建一个 Page 项目，侧栏打开计算与 AI 菜单，进入 Workers 和 Pages，然后看图。

| ![](assets/images/17-BlogStats/Pasted%20image%2020251217225233.png) | ![](assets/images/17-BlogStats/Pasted%20image%2020251217225328.png) |
| ------------------------------------ | ------------------------------------ |
| ![](assets/images/17-BlogStats/Pasted%20image%2020251217225410.png) | ![](assets/images/17-BlogStats/Pasted%20image%2020251217225447.png) |

这里起个名字，点击创建项目。
把之前的 `.zip` 拖进去，再部署站点。
![](assets/images/17-BlogStats/Pasted%20image%2020251217230103.png)

### 第三步：配置变量
接着点击继续处理项目，配一下环境，添加这个环境变量 `SECRET_UUID`，uuid 网上随便生成一个，添加后，保存。

| ![](assets/images/17-BlogStats/Pasted%20image%2020251217230419.png) | ![](assets/images/17-BlogStats/Pasted%20image%2020251217230517.png) |
| ------------------------------------ | ------------------------------------ |
| ![](assets/images/17-BlogStats/Pasted%20image%2020251217231050.png) |                                      |

### 第四步：绑定 KV
接下来，绑定 kv。

| ![](assets/images/17-BlogStats/Pasted%20image%2020251217232216.png) | ![](assets/images/17-BlogStats/Pasted%20image%2020251217232256.png) |
| ------------------------------------ | ------------------------------------ |
| ![](assets/images/17-BlogStats/Pasted%20image%2020251217232410.png) |                                      |

然后保存。

### 第五步：重新部署
接着重新部署来刷新环境变量。

![](assets/images/17-BlogStats/Pasted%20image%2020251217232712.png)

重复之前的上传过程就好了。

接着进入部署页面，cloudflare 会分配一个 page 域，通过这个域就能访问了。

![](assets/images/17-BlogStats/Pasted%20image%2020251217232918.png)

## 5. 测试一下

我们来用 curl 测试一下效果。

**模拟上报：**
```bash
curl -X POST -H "Content-Type: application/json" -d "{\"url\": \"https://ilylty.github.io/paperBlog/post/my-first-post\"}" https://blog-stats-test1.pages.dev/stat
```
返回：
```json
{
  "status": "ok"
}
```

**获取单页阅读量：**
```bash
curl "https://blog-stats-test1.pages.dev/post-info?url=https://ilylty.github.io/paperBlog/post/my-first-post"
```
返回：
```json
{
  "url": "/paperBlog/post/my-first-post",
  "count": 1
}
```

**获取全站总数：**
```bash
curl "https://blog-stats-test1.pages.dev/home-info"
```
返回：
```json
{
  "total": 1
}
```

**导出流数据 (SSE)：**
```bash
curl "https://blog-stats-test1.pages.dev/12345678-1234-5678-abcd-12345678abcd"
```
返回：
```json
data: {"key":"log::1765986052805::057a8f14","value":{"ts":1765986052805,"ip":"xx","ua":"curl/8.9.1","ref":"/paperBlog/post/my-first-post","loc":"xx"}}

data: {"key":"page_view::/paperBlog/post/my-first-post","value":1}

data: {"key":"site_total","value":1}

event: close
data: end
```