#python3 项目
# m3u8_downloader
m3u8（HLS流）下载，实现了AES解密、合并、多线程、批量下载

# 1、开车姿势
## 1.1、导入源码中依赖的库（Python3）
     beautifulsoup4、m3u8、pycryptodome、requests、threadpool
     并且还要安装ffmpeg 命令行工具,方便将影片转化为mp4;
## 1.2、m3u8_input.txt文件格式
&emsp;&emsp;本下载器支持批量下载，m3u8连接需要放在一个txt文本文件（utf-8编码）中，格式如下：
```python
视频名称1,https://www.aaaa.com/bbbb/cccc/index.m3u8
视频名称2,https://www.xxxx.com/yyyy/zzzz/index.m3u8
视频名称3,https://www.uuuu.com/vvvv/wwww/index.m3u8
...
```
## 1.3、根据实际情况修改下载配置
```python
###############################配置信息################################
# m3u8链接批量输入文件(必须是utf-8编码)
m3u8InputFilePath = "m3u8_input.txt"
# 设置视频保存路径
saveRootDirPath = "output"
# 下载出错的m3u8保存文件
errorM3u8InfoDirPath = "error.txt"
# m3u8文件、key文件下载尝试次数，ts流默认无限次尝试下载，直到成功
m3u8TryCountConf = 10
# 线程数（同时下载的分片数）
processCountConf = 50
######################################################################
```
##要将下载的 url 写入到 "m3u8_input.txt" 文件中
#####  m3u8_input.txt 文本中的格式, 一行表示一个要下载的记录,使用逗号分隔,前面是要保存的名字,后面是m3u8的url地址
#title_1,m3u8_url_1     
#title_2,m3u8_url_2
#实例:
wojiaxiang,https://good.jieshuo-okzy.com/20201231/9024_b5d80d38/1200k/hls/index.m3u8

###再直接执行  pyhton3 m3u8_downloader.py  就可 下载文件;

####也可以使用命令行快速下载单个视频
#实例:
python3 m3u8_downloader.py -i "https://good.jieshuo-okzy.com/20201231/9024_b5d80d38/1200k/hls/index.m3u8" -o "outname"

