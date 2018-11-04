# A-Python-Interpreter-Written-in-Python-Interpreted-in-Chinese
#### 将500 Lines or Less 中的A Python Interpreter Written in Python项目手动实现，并用中文逐行注释代码
### 目的
[500 Lines or Less](http://aosabook.org/en/index.html)是在互联网上备受推崇的一个项目集合，强调用不到500行的代码实现一个特定的功能。其中的[A Python Interpreter Written in Python](http://aosabook.org/en/500L/a-python-interpreter-written-in-python.html#fnref1)用很少的Python代码实现了一个简洁但复制了CPython主要结构的解释器。

基于巩固Python语言基础、并适当了解Python解释器结构原理的目的，我根据文章手动实现了大部分代码，但原文中作者仅简单阐述了解释器的设计原理及实现的部分步骤，大部分代码都没有进行注释，个别初学者（像我这种）很难理解代码的具体实现步骤，因此我根据自己的理解为绝大部分代码加上了中文注释，希望对大家有点帮助。

### 注意
- 绝大部分代码实现了中文注释，方便中文初学者理解代码的具体实现
- 本项目是作者[Allison Kaptur](akaptur.com)参与的Byterun项目的微缩版本，部分代码在简化过程中有遗漏或错误，我对发现的错误进行了修正（同时修正了中文翻译版的部分代码笔误）
- 由于本人初学Python且英语能力不佳，部分代码注释可能有误或用词不规范、不准确，希望你可以理解，并欢迎通过pull request或Issues参与改正
- 原文基于Python3.5及更早版本实现，由于Python3.6版本对字节码进行了小改动，本项目代码无法在Python3.6或3.7中完整实现，但不影响学习其实现原理，有兴趣者可自己尝试自修改代码适配新版本
- 代码中使用了dis, sys, collections, operator, types, inspect等Python内置库，但原文中未提及
### 地址
- 原文地址:[http://aosabook.org/en/500L/a-python-interpreter-written-in-python.html](http://aosabook.org/en/500L/a-python-interpreter-written-in-python.html) 作者：Allison Kaptur
- Byterun项目地址:[https://github.com/nedbat/byterun](https://github.com/nedbat/byterun)
- 中文翻译版地址:[https://linux.cn/article-7753-1.html](https://linux.cn/article-7753-1.html) 译者：qingyunha
### 解释器主要结构图示
（待补充）

### 联系作者
- 邮箱：ampedee@gmail.com

### 许可证
<a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/3.0/"><img alt="知识共享许可协议" style="border-width:0" src="https://i.creativecommons.org/l/by-nc-sa/3.0/88x31.png" /></a><br />本作品采用<a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/3.0/">知识共享署名-非商业性使用-相同方式共享 3.0 未本地化版本许可协议</a>进行许可。
