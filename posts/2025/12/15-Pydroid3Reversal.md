<!-- 
title: Pydroid3简单破解
categories: ["Reverse"]
tags: ["simplehookr"]
cover_image: ""
summary: "使用simpleHookR简单破解Pydroid3"
-->
先来看看没破解前，是啥样的

| ![](assets/images/15-Pydroid3Reversal/badd9f423e8dc46c32e14c8365526161%201.jpg)       | 这有个 get premium的选项<br>如果我们是premium用户，你觉得还会出现这个选项吗？<br>所以入手点，可以尝试搜索premium字符串 |
| ------------------------------------------------- | ---------------------------------------------------------------------------- |
| ![](assets/images/15-Pydroid3Reversal/657a517ace2825e0bbc2dfb760c6b655.jpg)<br><br> | 先看看有没有壳，很好，没壳                                                                |

```bash
jadx -d output_dir "Pydroid 3_8.22_arm64.apk"
```
![](assets/images/15-Pydroid3Reversal/Pasted%20image%2020251216165618.png)

搜索**premium**
<br><br>
![](assets/images/15-Pydroid3Reversal/Pasted%20image%2020251216165915.png)<br><br>
可以看见很多premium
但是有个可疑的<br><br>
![](assets/images/15-Pydroid3Reversal/Pasted%20image%2020251216170106.png)<br><br>
进入mainActivity.X0
![](assets/images/15-Pydroid3Reversal/Pasted%20image%2020251216170342.png)<br><br>
继续进入super.X0
![](assets/images/15-Pydroid3Reversal/Pasted%20image%2020251216170543.png)<br><br>
![](assets/images/15-Pydroid3Reversal/Pasted%20image%2020251216170602.png)<br><br>
![](assets/images/15-Pydroid3Reversal/Pasted%20image%2020251216170619.png)<br><br>
![](assets/images/15-Pydroid3Reversal/Pasted%20image%2020251216170909.png)<br><br>
可以看出，在启动时调用X0，X0返回默认的false，接着给了z2（私有方法）<br><br>
然后z2就没被调用了，z2应该是刷新啥的，<br><br>
接着ctrl+左键看看X0的引用<br><br>
![](assets/images/15-Pydroid3Reversal/Pasted%20image%2020251216171746.png)<br><br>
 挺多的，应该是其他代码判断premium的关键函数，我们直接让X0返回true试试

接下来使用simpleHookR修改返回值
类名:s4.G
方法:X0
返回true

启动pydroid3
成功破解

| ![](assets/images/15-Pydroid3Reversal/681be7aa12a4204ebf3209197227f99d.jpg) | ![](assets/images/15-Pydroid3Reversal/ca65eae3d652b23af2c997ed3b581f0f%201.jpg) |
| ----------------------------------------- | ------------------------------------------- |

