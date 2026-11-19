# 本地脚本使用

依赖：Python 3.10 或以上。除图片工具外只使用Python标准库。先将工作目录切到本Skill文件夹，或把命令中的相对路径替换为实际绝对路径。下述输出文件/目录必须尚不存在；重试时使用新路径，原输入和旧结果都保留。

```sh
python scripts/check_mapping.py references/mapping.csv --inventory references/old-urls.txt --output mapping-result.json
```

## 输入与示例预期

CSV必须含old_url,new_url，要求完整HTTP(S)地址。示例描述中的/a等只是缩写，实际输入需有站点域名。inventory每行一个完整旧URL。示例应识别循环、冲突和/f遗漏。

## 能力边界

图身份仅规范协议/主机大小写、默认端口及根路径，保留原始行、查询参数和路径大小写。不验证线上跳转、页面相关性或目标状态。many_to_one_review是人工复核项。

所有样例使用example.com及虚构资料，不能当客户实测。脚本不含遥测或付费API，不会发布内容。发现问题会写入报告，不代表执行异常；命令参数或输入格式错误返回退出码2。图片工具有文件处理失败时返回1并保留manifest；跳过动画会记录原因。
