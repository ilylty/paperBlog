<!-- 
title: 岸听音乐逆向
categories: ["Reverse"]
tags: ["Music", "smali"]
cover_image: ""
summary: "详细介绍如何逆向分析岸听音乐app，包括搜索关键函数、处理请求头和post参数等。"
-->
# 岸听音乐逆向

# ***1，搜索***

## **(1)处理请求头**

![image.png](assets/images/11-AntinMusicReversal/image.png)

`headers`中`Authorization`的值盲猜是`MD5`

![Screenshot_2024-11-11-15-30-27-563_com.junge.algo.png](assets/images/11-AntinMusicReversal/Screenshot_2024-11-11-15-30-27-563_com.junge.algo.png)

查看调用栈，发现一个***关键函数***

![image.png](assets/images/11-AntinMusicReversal/image%201.png)

![image.png](assets/images/11-AntinMusicReversal/image%202.png)

1，`header`方法：

先把post参数中的`sing`和`data`提取出

再交给`splitString` 方法处理

构建字符串并加密

`sing[0] + data[0] + sing[1] + data[1]`

再MD5得到Authorization

2，`splitString` 方法：

- **计算分割长度**：计算 `string` 的一半长度，并存储在 `length` 变量中。
- **子字符串提取**：
    - 使用 `string.substring(0, length)` 提取 `string` 的前半部分，存储为 `substring`。
    - 使用 `string.substring(length)` 提取 `string` 的后半部分，存储为 `substring2`。
- **返回结果**：将前后两个子字符串组成一个数组，并返回该数组。

## (2)处理post中的参数

![image.png](assets/images/11-AntinMusicReversal/image%203.png)

我们先研究sing参数(~~绝不是因为短)~~

### <1>sing参数

看起来像md5，没错

![Screenshot_2024-11-11-16-07-11-154_com.junge.algo.png](assets/images/11-AntinMusicReversal/Screenshot_2024-11-11-16-07-11-154_com.junge.algo.png)

看起来像是对`罗生门0qqB3uz2bToFYDS6E39nTn4hBNojrM2OyL9`进行`md5`

![Screenshot_2024-11-11-16-10-15-019_com.junge.algo.png](assets/images/11-AntinMusicReversal/Screenshot_2024-11-11-16-10-15-019_com.junge.algo.png)

![Screenshot_2024-11-11-16-10-39-861_com.junge.algo.png](assets/images/11-AntinMusicReversal/Screenshot_2024-11-11-16-10-39-861_com.junge.algo.png)

由图找规律 `<关键词>0<平台>B3uz2bToFYDS6E39nTn4hBNojrM2OyL9`

而`B3uz2bToFYDS6E39nTn4hBNojrM2OyL9`每次请求都一样，可以默认写死的

`<平台>`有三种`kuwo`，`qq`，`netease`

对构造的字符串，进行`md5`，转大写即得到`sing`参数

### <2>data参数

![Screenshot_2024-11-11-16-24-15-287_com.junge.algo.png](assets/images/11-AntinMusicReversal/Screenshot_2024-11-11-16-24-15-287_com.junge.algo.png)

密钥就是我们已经解出`sing`

这里的`iv`是一个死值

![image.png](assets/images/11-AntinMusicReversal/image%204.png)

```json
{
    "act":"search",
    "type":"qq",
    "keywords":"%E7%BD%97%E7%94%9F%E9%97%A8",
    "keytype":"0"
}
```

![image.png](assets/images/11-AntinMusicReversal/image%205.png)

加密内容（文本）：

其中`keywords`url解码后是`<关键词>`

我们再看看这个`json`是怎么产生的

来到**堆栈**，发现util跳出后，

来到了一个关键的命名`notifyData`

```java
private final void notifyData() {
  String sing = EncryptUtils.encryptMD5ToString(this.searchStr + '0' + this.searchType + Api.INSTANCE.md5Key());
  byte[] bytes = (
      "{\"act\":\"search\",\"type\":\"" 
      + this.searchType 
      + "\",\"keywords\":\"" 
      + EncodeUtils.urlEncode(this.searchStr) + 
      "\",\"keytype\":\"0\"}"
      ).getBytes(Charsets.UTF_8);
  Intrinsics.checkNotNullExpressionValue(bytes, "this as java.lang.String).getBytes(charset)");
  Intrinsics.checkNotNullExpressionValue(sing, "sing");
    byte[] bytes2 = sing.getBytes(Charsets.UTF_8);
  Intrinsics.checkNotNullExpressionValue(bytes2, "this as java.lang.String).getBytes(charset)");
  byte[] bytes3 = Api.INSTANCE.aesIv().getBytes(Charsets.UTF_8);
  Intrinsics.checkNotNullExpressionValue(bytes3, "this as java.lang.String).getBytes(charset)");
  String encryptAES2HexString = EncryptUtils.encryptAES2HexString(bytes, bytes2, Api.aesForm, bytes3);
  LinearLayout linearLayout = this.emptyView;
```

![image.png](assets/images/11-AntinMusicReversal/image%206.png)

显然唯二的变量只有`this.searchType`和`this.searchStr`

`this.searchType`就是`kuwo`，`qq`，`netease`

`this.searchStr`是经url编码，再大写后的`<关键词>`

json经`AES/CBC/PKCS5Padding` 加密后得`hex`，再大写，就是post的`data`

# *2，解析音乐*

## 接下来分析音乐链接怎么产生的

![image.png](assets/images/11-AntinMusicReversal/image%207.png)

![image.png](assets/images/11-AntinMusicReversal/image%208.png)

这里的·`Authorization`和`1-(1)`中的，

一样需要`post`中的`sing`和`data`参数

## 先看看sing参数的产生，

文本：`14568900091281456890009neteaseB3uz2bToFYDS6E39nTn4hBNojrM2OyL9music` 经`md5`后，再大写，得到`sing`

由前面的分析可以得出

`14568900091281456890009`似乎是音乐`id`

`netease`这首音乐在哪个平台上

`B3uz2bToFYDS6E39nTn4hBNojrM2OyL9`这个是前面的说的**常量**

`music`顾名思义←_←

![Screenshot_2024-11-11-17-14-59-373_com.junge.algo.png](assets/images/11-AntinMusicReversal/Screenshot_2024-11-11-17-14-59-373_com.junge.algo.png)

我们试试在**数据包**中搜索`14568900091281456890009`

*~~啥的搜不出~~*

用我们聪明的大牢想想

发现

`1456890009`

`128`

`1456890009`

而`1456890009`是`netease`平台的音乐`id`

`128` 应该是*音质*吧

## 再看data的产生
... 和上面的差不多   :P