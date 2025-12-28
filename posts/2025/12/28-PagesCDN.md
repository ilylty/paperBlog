<!-- 
title: "Cloudflare Pages 代理加速"
categories: ["网络加速"]
tags: ["Cloudflare", "Pages", "Clash", "CDN", "规则集"]
cover_image: ""
summary: "通过 Cloudflare Pages 部署脚本服务，并结合 Clash 与自定义规则集，将视频、图片等高流量资源定向到指定节点."
-->
# 利用 Cloudflare Pages 实现加速访问网络

通过 Cloudflare Pages 部署脚本，并结合 Clash Meta，用于提升特定网络资源的访问速度.

---

## 一、准备脚本文件

首先将你的脚本保存为 `index.js`：

```javascript
import { connect } from 'cloudflare:sockets';


var USER_ID = '';



const proxyIPs = [
    { region: 'US', domain: 'ProxyIP.US.CMLiussss.net', port: 443 },
    { region: 'SG', domain: 'ProxyIP.SG.CMLiussss.net', port: 443 },
    { region: 'JP', domain: 'ProxyIP.JP.CMLiussss.net', port: 443 },
    { region: 'KR', domain: 'ProxyIP.KR.CMLiussss.net', port: 443 },
    { region: 'DE', domain: 'ProxyIP.DE.CMLiussss.net', port: 443 },
    { region: 'SE', domain: 'ProxyIP.SE.CMLiussss.net', port: 443 },
    { region: 'NL', domain: 'ProxyIP.NL.CMLiussss.net', port: 443 },
    { region: 'FI', domain: 'ProxyIP.FI.CMLiussss.net', port: 443 },
    { region: 'GB', domain: 'ProxyIP.GB.CMLiussss.net', port: 443 },
    { region: 'Oracle', domain: 'ProxyIP.Oracle.cmliussss.net', port: 443 },
    { region: 'DigitalOcean', domain: 'ProxyIP.DigitalOcean.CMLiussss.net', port: 443 },
    { region: 'Vultr', domain: 'ProxyIP.Vultr.CMLiussss.net', port: 443 },
    { region: 'Multacom', domain: 'ProxyIP.Multacom.CMLiussss.net', port: 443 }
];

export default {
    async fetch(request, env, ctx) {
        try {
            USER_ID = env.USER_ID || '';
            const upgrade = request.headers.get('Upgrade');
            if (!upgrade || upgrade !== 'websocket') {
                if (!USER_ID) {
                    return new Response('env.USER_ID is required', { status: 200 });
                }

                const url = new URL(request.url);
                const headers = {};
                for (const [k, v] of request.headers.entries()) headers[k] = v;
                return new Response(JSON.stringify({
                    args: Object.fromEntries(url.searchParams),
                    headers,
                    origin: request.headers.get('cf-connecting-ip') || request.headers.get('x-forwarded-for') || '',
                    url: url.toString()
                }, null, 2), {
                    status: 200,
                    headers: { 'content-type': 'application/json' }
                });
            }
            
            
            const url = new URL(request.url);
            const pathRegion = url.pathname.replace('/', '').toUpperCase();

            return await handleWsRequest(request, pathRegion);
        } catch (err) {
            return new Response(err.toString(), { status: 500 });
        }
    },
};


async function handleWsRequest(request, targetRegion) {
    const wsPair = new WebSocketPair();
    const [clientSock, serverSock] = Object.values(wsPair);
    serverSock.accept();

    let remoteConnWrapper = { socket: null };
    let isDnsQuery = false;
    let protocolType = null;

    const earlyData = request.headers.get('sec-websocket-protocol') || '';
    const readable = makeReadableStream(serverSock, earlyData);

    readable.pipeTo(new WritableStream({
        async write(chunk) {
            if (isDnsQuery) return await forwardUDP(chunk, serverSock, null);
            
            if (remoteConnWrapper.socket) {
                const writer = remoteConnWrapper.socket.writable.getWriter();
                await writer.write(chunk);
                writer.releaseLock();
                return;
            }

            if (!protocolType) {
                
                if (chunk.byteLength >= 24) {
                    const vlessResult = parseWsPacketHeader(chunk, USER_ID);
                    if (!vlessResult.hasError) {
                        protocolType = 'vless';
                        const { addressType, port, hostname, rawIndex, version, isUDP } = vlessResult;
                        
                        
                        if (isUDP) {
                            if (port === 53) isDnsQuery = true;
                            else {
                                serverSock.close(); 
                                return;
                            }
                        }

                        
                        const respHeader = new Uint8Array([version[0], 0]);
                        const rawData = chunk.slice(rawIndex);

                        if (isDnsQuery) return forwardUDP(rawData, serverSock, respHeader);

                        
                        await forwardTCP(hostname, port, rawData, serverSock, respHeader, remoteConnWrapper, targetRegion);
                        return;
                    }
                }
                
                serverSock.close();
            }
        },
    })).catch((err) => { serverSock.close(); });

    return new Response(null, { status: 101, webSocket: clientSock });
}

async function forwardTCP(host, portNum, rawData, ws, respHeader, remoteConnWrapper, targetRegion) {
    
    async function connectAndSend(address, port) {
        const remoteSock = connect({ hostname: address, port: port });
        const writer = remoteSock.writable.getWriter();
        await writer.write(rawData);
        writer.releaseLock();
        return remoteSock;
    }

    
    async function retryConnection() {
        let backupHost = host;
        let backupPort = portNum;

        
        const selectedNode = proxyIPs.find(p => p.region === targetRegion) || proxyIPs[0];
        
        if (selectedNode) {
            backupHost = selectedNode.domain;
            backupPort = selectedNode.port;
        }

        try {
            const fallbackSocket = await connectAndSend(backupHost, backupPort);
            remoteConnWrapper.socket = fallbackSocket;
            
            fallbackSocket.closed.catch(() => {}).finally(() => closeSocketQuietly(ws));
            connectStreams(fallbackSocket, ws, respHeader, null);
        } catch (fallbackErr) {
            closeSocketQuietly(ws);
        }
    }

    
    try {
        const initialSocket = await connectAndSend(host, portNum);
        remoteConnWrapper.socket = initialSocket;
        connectStreams(initialSocket, ws, respHeader, retryConnection);
    } catch (err) {
        
        retryConnection();
    }
}

async function connectStreams(remoteSocket, webSocket, headerData, retryFunc) {
    let header = headerData;
    let hasData = false;

    await remoteSocket.readable.pipeTo(
        new WritableStream({
            async write(chunk, controller) {
                hasData = true;
                if (webSocket.readyState !== 1) {
                    controller.error('WS closed');
                    return;
                }
                
                if (header) {
                    const combined = new Uint8Array(header.length + chunk.length);
                    combined.set(header);
                    combined.set(chunk, header.length);
                    webSocket.send(combined);
                    header = null;
                } else {
                    webSocket.send(chunk);
                }
            },
        })
    ).catch(() => { closeSocketQuietly(webSocket); });
    if (!hasData && retryFunc) {
        retryFunc();
    }
}

function parseWsPacketHeader(chunk, targetID) {
    if (chunk.byteLength < 24) return { hasError: true };
    
    const version = new Uint8Array(chunk.slice(0, 1));
    const idBytes = new Uint8Array(chunk.slice(1, 17));
    
    if (stringifyUuid(idBytes) !== targetID) {
        return { hasError: true };
    }

    const optLen = new Uint8Array(chunk.slice(17, 18))[0];
    const cmd = new Uint8Array(chunk.slice(18 + optLen, 19 + optLen))[0];
    
    let isUDP = cmd === 2;
    
    if (cmd !== 1 && cmd !== 2) return { hasError: true };

    const portIdx = 19 + optLen;
    const port = new DataView(chunk.slice(portIdx, portIdx + 2)).getUint16(0);
    
    let addrIdx = portIdx + 2;
    let addrValIdx = addrIdx + 1;
    let hostname = '';
    let addrLen = 0;
    
    const addressType = new Uint8Array(chunk.slice(addrIdx, addrValIdx))[0];

    switch (addressType) {
        case 1: 
            addrLen = 4;
            hostname = new Uint8Array(chunk.slice(addrValIdx, addrValIdx + addrLen)).join('.');
            break;
        case 2: 
            addrLen = new Uint8Array(chunk.slice(addrValIdx, addrValIdx + 1))[0];
            addrValIdx += 1;
            hostname = new TextDecoder().decode(chunk.slice(addrValIdx, addrValIdx + addrLen));
            break;
        case 3: 
            addrLen = 16;
            const ipv6 = [];
            const ipv6View = new DataView(chunk.slice(addrValIdx, addrValIdx + addrLen));
            for (let i = 0; i < 8; i++) ipv6.push(ipv6View.getUint16(i * 2).toString(16));
            hostname = ipv6.join(':');
            break;
        default:
            return { hasError: true };
    }

    if (!hostname) return { hasError: true };

    return { 
        hasError: false, 
        addressType, 
        port, 
        hostname, 
        isUDP, 
        rawIndex: addrValIdx + addrLen, 
        version 
    };
}

async function forwardUDP(udpChunk, webSocket, respHeader) {
    try {
        const tcpSocket = connect({ hostname: '8.8.4.4', port: 53 });
        let header = respHeader;
        const writer = tcpSocket.writable.getWriter();
        await writer.write(udpChunk);
        writer.releaseLock();
        
        await tcpSocket.readable.pipeTo(new WritableStream({
            async write(chunk) {
                if (webSocket.readyState === 1) {
                    if (header) {
                        const combined = new Uint8Array(header.length + chunk.length);
                        combined.set(header);
                        combined.set(chunk, header.length);
                        webSocket.send(combined);
                        header = null;
                    } else {
                        webSocket.send(chunk);
                    }
                }
            },
        }));
    } catch (error) {}
}

function makeReadableStream(socket, earlyDataHeader) {
    let cancelled = false;
    return new ReadableStream({
        start(controller) {
            socket.addEventListener('message', (event) => { if (!cancelled) controller.enqueue(event.data); });
            socket.addEventListener('close', () => { if (!cancelled) { closeSocketQuietly(socket); controller.close(); } });
            socket.addEventListener('error', (err) => controller.error(err));
            const { earlyData } = base64ToArray(earlyDataHeader);
            if (earlyData) controller.enqueue(earlyData);
        },
        cancel() { cancelled = true; closeSocketQuietly(socket); }
    });
}

function base64ToArray(b64Str) {
    if (!b64Str) return { earlyData: null };
    try { 
        b64Str = b64Str.replace(/-/g, '+').replace(/_/g, '/'); 
        const bin = atob(b64Str);
        const u8 = new Uint8Array(bin.length);
        for (let i=0; i<bin.length; i++) u8[i] = bin.charCodeAt(i);
        return { earlyData: u8.buffer }; 
    }
    catch (error) { return { earlyData: null }; }
}

function closeSocketQuietly(socket) { 
    try { if (socket.readyState === 1 || socket.readyState === 2) socket.close(); } catch (error) {} 
}

const byteToHex = [];
for (let i = 0; i < 256; ++i) byteToHex.push((i + 0x100).toString(16).substr(1));
function stringifyUuid(arr) {
    return (
        byteToHex[arr[0]] + byteToHex[arr[1]] + byteToHex[arr[2]] + byteToHex[arr[3]] + '-' +
        byteToHex[arr[4]] + byteToHex[arr[5]] + '-' +
        byteToHex[arr[6]] + byteToHex[arr[7]] + '-' +
        byteToHex[arr[8]] + byteToHex[arr[9]] + '-' +
        byteToHex[arr[10]] + byteToHex[arr[11]] + byteToHex[arr[12]] + byteToHex[arr[13]] + byteToHex[arr[14]] + byteToHex[arr[15]]
    ).toLowerCase();
}
```

由于 Cloudflare 会拦截部分明显的反向代理脚本，因此需要对 JavaScript 进行**轻度混淆**处理.

---

## 二、对脚本进行混淆处理

### 1. 安装混淆工具

确保已安装 Node.js，然后执行：

```bash
npm install -g javascript-obfuscator
```

### 2. 生成混淆后的脚本

在 `index.js` 所在目录执行：

```bash
javascript-obfuscator index.js --output _worker.js --compact true --self-defending false --string-array true --string-array-encoding 'rc4' --identifier-names-generator mangled --rename-globals true
```

执行完成后会生成 `_worker.js` 文件.

### 3. 打包文件

将 `_worker.js` 压缩为一个 `.zip` 文件，后续上传到 Cloudflare Pages.

---

## 三、部署到 Cloudflare Pages

### 1. 进入 Cloudflare 控制台

访问：

```text
https://dash.cloudflare.com/
```

### 2. 创建 Pages 项目

依次操作：

* 左侧菜单进入「计算和 AI」 → 「Workers 和 Pages」
* 右上角点击「创建应用程序」
* 点击下方小字 **“Looking to deploy Pages? Get started”**
* 在「拖放文件」区域右侧点击「开始使用」
* 项目名称可以设置得稍微长一些，然后创建项目

### 3. 上传并部署

将之前打包好的 `.zip` 文件拖入页面，上传完成后点击「部署站点」.

---

## 四、配置环境变量

部署完成后，继续配置项目.

### 1. 进入设置页面

在项目页面中，点击导航栏的「设置」，进入「变量和机密」.

### 2. 生成 UUID

打开 UUID 生成网站：

```text
https://www.uuidgenerator.net/version4
```

生成一个 UUID，例如：

```text
db27b24f-735d-4ceb-a8aa-4fccb4b3210a
```

### 3. 添加环境变量

在「变量和机密」新增一个**文本变量**：

* 变量名：`USER_ID`
* 值：刚刚生成的 UUID

### 4. 重新部署以生效变量

点击右上角「创建部署」，再次拖入 `.zip` 文件，保存并部署.

---

## 五、确认部署是否成功

部署成功后会显示一个访问地址，例如：

```text
https://xxxxxxxxxxxxx.pages.dev
```

访问该地址，如果页面返回类似如下内容，说明部署成功：

```json
{
  "args": {},
  "headers": {
    "accept": "...",
    "accept-encoding": "...",
    ...
    ...
    ...
  }
}
```

---

## 六、配置 Clash

### 1. 添加代理节点

在 Clash 配置文件的 `proxies` 组中添加：

```yaml
  - name: "HK-CDN"
    type: vless
    server: xxxxxxxxxxxxx.pages.dev
    port: 443
    uuid: 12345678-1234-5678-abcd-12345678abcd
    encryption: none
    tls: true
    servername: xxxxxxxxxxxxx.pages.dev
    skip-cert-verify: true
    network: ws
    ws-opts:
      path: "/?ed=2048"
      headers:
        Host: xxxxxxxxxxxxx.pages.dev
```

注意：
`server`、`servername`、`Host` 必须替换为你自己部署得到的 Pages 域名.
`uuid` 替换为你在环境变量中设置的 UUID.

---

## 七、添加规则集

### 1. 配置 rule-providers

在 `rule-providers` 组中添加（如不存在请新建）：

```yaml
  ilylty-hk-domain:
    type: http
    behavior: domain
    url: "https://cdn.jsdelivr.net/gh/ilylty/HK-CDN-Rules/rules/hk-domain.txt"
    path: ./ruleset/ilylty-hk-domain.yaml
    interval: 86400

  ilylty-direct:
    type: http
    behavior: domain
    url: "https://cdn.jsdelivr.net/gh/ilylty/HK-CDN-Rules/rules/direct.txt"
    path: ./ruleset/ilylty-direct.yaml
    interval: 86400
```

### 2. 添加规则

在 `rules` 部分的顶部添加：

```yaml
  - RULE-SET,ilylty-hk-domain,HK-CDN
  - RULE-SET,ilylty-direct,DIRECT
```

---

## 八、完成

**重要提示：**

由于原版 Clash 不支持 VLESS 协议，请使用支持 VLESS 协议的 Clash 衍生版本，例如 [Clash Meta](https://github.com/hiddify/HiddifyClashDesktop) 或 [Mihomo](https://github.com/MetaCubeX/mihomo).请根据你使用的操作系统下载对应的客户端.

保存配置并重载 Clash 配置即可生效.

