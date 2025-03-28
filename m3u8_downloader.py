#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: By 空道



import os,shutil
import sys
import m3u8
import time
import requests
import traceback
import threadpool
import getopt,re
from Crypto.Cipher import AES
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
import ssl
from urllib.parse import urlparse
from urllib.request import urlopen
import pyperclip,subprocess

###关闭警告
requests.packages.urllib3.disable_warnings()
headers = {
    "Accept": "*/*",
    #"Connection": "Keep-Alive",
    "Accept-Encoding": "gzip;q=1.0, deflate, identity",
    #"Accept-Language": "zh-CN,zh;q=0.9",
    "User-Agent": "Mozilla/5.0 (Linux; U; Android 5.0; zh-CN; HTC 802t Build/KTU84L) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/57.0.2987.108 Quark/4.3.3.145 Mobile Safari/537.36"
}

class MyAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(num_pools=connections,
                                       maxsize=maxsize,
                                       block=block,
                                       ssl_version=ssl.PROTOCOL_TLSv1)
s = requests.Session()
s.mount('https://', MyAdapter())
###############################配置信息################################
# m3u8链接批量输入文件(必须是utf-8编码)
m3u8InputFilePath = "m3u8_input.txt"
#####  m3u8_input.txt 文本中的格式, 一行表示一个要下载的记录,使用逗号分隔,前面是要保存的名字,后面是m3u8的url地址
#title_1,m3u8_url_1     
#title_2,m3u8_url_2
#实例:
#wojiaxiang,https://good.jieshuo-okzy.com/20201231/9024_b5d80d38/1200k/hls/index.m3u8
# 设置视频保存路径
saveRootDirPath = "output"
# 下载出错的m3u8保存文件
errorM3u8InfoDirPath = "error.txt"
# m3u8文件、key文件下载尝试次数，ts流默认无限次尝试下载，直到成功
m3u8TryCountConf = 10
# 线程数（同时下载的分片数）
processCountConf = 50
######################################################################


# 全局变量
# 全局线程池
taskThreadPool = None
# 当前下载的m3u8 url
m3u8Url = None
# url前缀
rootUrlPath = None
# title
title = None
# ts count
sumCount = 0
# 已处理的ts
doneCount = 0
# cache path
cachePath = saveRootDirPath + "/cache" + str(int(time.time()))
# log path
logPath = cachePath + "/log.log"
# log file
logFile = None
# download bytes(0.5/1 s)
downloadedBytes = 0
# download speed
downloadSpeed = 0


def hexStringTobytes(str):
    if sys.version > '3':
        str = str.replace(" ", "")
        return bytes.fromhex(str)
    else:
        return str.decode('hex')
def m3u8_is_variant(instr):
    for rowData in instr.split('\n'):
            ## 删除不可见
            rowData = rowData.strip()
            # 寻找响应内容的中的m3u8
            if rowData.endswith(".m3u8"):
                return True
    return False
# 1、下载m3u8文件
def getM3u8Info():
    global m3u8Url
    global logFile
    global rootUrlPath
    tryCount = m3u8TryCountConf
    while True:
        if tryCount < 0:
            print("\t{0}下载失败！".format(m3u8Url))
            logFile.write("\t{0}下载失败！".format(m3u8Url))
            return None
        tryCount = tryCount - 1
        try:
            response = requests.get(m3u8Url, headers=headers, timeout=20, verify=False)
            if response.status_code == 301:
                nowM3u8Url = response.headers["location"]
                print("\t{0}重定向至{1}！".format(m3u8Url, nowM3u8Url))
                logFile.write("\t{0}重定向至{1}！\n".format(m3u8Url, nowM3u8Url))
                m3u8Url = nowM3u8Url
                o = urlparse(m3u8Url)
                rootUrlPath = o.scheme + "://" + o.hostname;
                #rootUrlPath = m3u8Url[0:m3u8Url.rindex('/')]
                continue
            #print(response.headers)
            #print(response.content)
            #expected_length = int(response.headers.get('Content-Length'))
            actual_length = len(response.content)
            #if expected_length > actual_length:
            #    raise Exception("m3u8下载不完整")
            print("\t{0}下载成功！".format(m3u8Url))
            logFile.write("\t{0}下载成功！".format(m3u8Url))
            #o = urlparse(m3u8Url)
            #rootUrlPath = o.scheme + "://" + o.hostname;
            rootUrlPath = m3u8Url[0:m3u8Url.rindex('/')]
            break
        except:
            print("\t{0}下载失败！正在重试".format(m3u8Url))
            logFile.write("\t{0}下载失败！正在重试".format(m3u8Url))
    # 解析m3u8中的内容
    m3u8Info = m3u8.loads(response.text)
    # 有可能m3u8Url是一个多级码流
    if m3u8Info.is_variant or m3u8_is_variant(response.text):
        print("\t{0}为多级码流！".format(m3u8Url))
        logFile.write("\t{0}为多级码流！".format(m3u8Url))
        for rowData in response.text.split('\n'):
            ## 删除不可见
            rowData = rowData.strip()
            # 寻找响应内容的中的m3u8
            if rowData.endswith(".m3u8"):
                o = urlparse(m3u8Url)
                if '/' == rowData[0:1]:
                    m3u8Url = m3u8Url[0:m3u8Url.find(o.path)] + rowData
                elif rowData.startswith('https://') or rowData.startswith('http://'):
                    m3u8Url = rowData
                else:
                    m3u8Url = m3u8Url[0:m3u8Url.rindex('/')] + '/' + rowData
                #m3u8Url = m3u8Url.replace("index.m3u8", rowData)
                rootUrlPath = m3u8Url[0:m3u8Url.rindex('/')]
                return getM3u8Info()
        # 遍历未找到就返回None
        print("\t{0}响应未寻找到m3u8！".format(response.text))
        logFile.write("\t{0}响应未寻找到m3u8！".format(response.text))
        return None
    else:
        return m3u8Info

# 2、下载key文件
def getKey(keyUrl):
    global logFile
    tryCount = m3u8TryCountConf
    while True:
        if tryCount < 0:
            print("\t{0}下载失败！".format(keyUrl))
            logFile.write("\t{0}下载失败！".format(keyUrl))
            return None
        tryCount = tryCount - 1
        try:
            response = requests.get(keyUrl, headers=headers, timeout=20, allow_redirects=True,verify=False)
            if response.status_code == 301:
                nowKeyUrl = response.headers["location"]
                print("\t{0}重定向至{1}！".format(keyUrl, nowKeyUrl))
                logFile.write("\t{0}重定向至{1}！\n".format(keyUrl, nowKeyUrl))
                keyUrl = nowKeyUrl
                continue
            # expected_length = int(response.headers.get('Content-Length'))
            # actual_length = len(response.content)
            # if expected_length > actual_length:
            #     raise Exception("key下载不完整")
            print(response.content);
            #print("\t{0}下载成功！key = {1}".format(keyUrl, response.content.decode("utf-8")))
            #logFile.write("\t{0}下载成功！ key = {1}".format(keyUrl, response.content.decode("utf-8")))
            break
        except Exception as exception:
            print(exception)

            print("\t{0}下载失败！".format(keyUrl))
            logFile.write("\t{0}下载失败！".format(keyUrl))
    return response.content

# 3、多线程下载ts流
def mutliDownloadTs(playlist):
    global logFile
    global sumCount
    global doneCount
    global taskThreadPool
    global downloadedBytes
    global downloadSpeed
    taskList = []
    # 每个ts单独作为一个task
    for index in range(len(playlist)):
        dict = {"playlist": playlist, "index": index}
        taskList.append((None, dict))
    # 重新设置ts数量，已下载的ts数量
    doneCount = 0
    sumCount = len(taskList)
    printProcessBar(sumCount, doneCount, 50)
    # 构造thread pool
    requests = threadpool.makeRequests(downloadTs, taskList)
    [taskThreadPool.putRequest(req) for req in requests]
    # 等待所有任务处理完成
    while doneCount < sumCount:
        # 统计1秒钟下载的byte
        beforeDownloadedBytes = downloadedBytes
        time.sleep(1)
        downloadSpeed = downloadedBytes - beforeDownloadedBytes
        # 计算网速后打印一次
        printProcessBar(sumCount, doneCount, 50, True)
    print("")
    return True
# 4、下载单个ts playlists[index]
def downloadTs(playlist, index):
    magic_head = [bytes([0x89,0x47,0x49,0x46]),    ###gif
                  bytes([0x67,0x69,0x66]),    ###GIF
                  bytes([0x70,0x6e,0x67]),    ###png
                  bytes([0x89,0x50,0x4e,0x47]),    ###PNG
                  bytes([0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46]), ####jpeg
                  ]
    #######通过查找下面两个特征码来定位 ts 的偏移;
    #### FFmpeg
    ffpmeg_magic = bytes([0x46, 0x46, 0x6D, 0x70, 0x65, 0x67])
    #### FFFF
    FFFF_magic = b'\xff' * 0x20

    find_head_flags = False
    ##
    global logFile
    global sumCount
    global doneCount
    global cachePath
    global rootUrlPath
    global downloadedBytes
    succeed = False
    while not succeed:
        # 文件名格式为 "00000001.ts"，index不足8位补充0
        outputPath = cachePath + "/" + "{0:0>8}.ts".format(index)
        outputFp = open(outputPath, "wb+")
        if playlist[index].startswith("http"):
            tsUrl = playlist[index]
        else:
            if playlist[index][0:1] != '/':
                tsUrl = rootUrlPath + "/" + playlist[index]
            else:
                o = urlparse(rootUrlPath)
                tsUrl = o.scheme + "://" + o.hostname + playlist[index]
        try:
            #print("tsUrl:" + tsUrl)
            response = requests.get(tsUrl, timeout=5, headers=headers, stream=True, verify=False)
            if response.status_code == 200:
                expected_length = int(response.headers.get('Content-Length'))
                actual_length = len(response.content)
                # 累计下载的bytes
                downloadedBytes += actual_length
                if expected_length > actual_length:
                    raise Exception("分片下载不完整")
                
                #### 判断是否是图片的文件头
                for magickey in magic_head:
                    magiclen = len(magickey)
                    find_head_flags = response.content[0:magiclen] == magickey
                    if find_head_flags:
                        break
                ###删除图片文件头
                if find_head_flags:
                    findres = response.content.find(ffpmeg_magic)
                    if findres < 0:
                        findres = response.content.find(FFFF_magic)
                    if findres > 0:
                        outputFp.write(response.content[findres:])
                    else:
                        outputFp.write(response.content)
                else:
                    outputFp.write(response.content)
                doneCount += 1
                printProcessBar(sumCount, doneCount, 50, isPrintDownloadSpeed=True)
                logFile.write("\t分片{0:0>8} url = {1} 下载成功！".format(index, tsUrl))
                succeed = True
        except Exception as exception:
            logFile.write("\t分片{0:0>8} url = {1} 下载失败！正在重试...msg = {2}".format(index, tsUrl, exception))
        outputFp.close()

# 5、合并ts
def mergeTs(tsFileDir, outputFilePath, cryptor, count):
    global logFile
    outputFp = open(outputFilePath, "wb+")
    for index in range(count):
        printProcessBar(count, index + 1, 50)
        logFile.write("\t{0}\n".format(index))
        inputFilePath = tsFileDir + "/" + "{0:0>8}.ts".format(index)
        if not os.path.exists(outputFilePath):
            print("\n分片{0:0>8}.ts, 不存在，已跳过！".format(index))
            logFile.write("分片{0:0>8}.ts, 不存在，已跳过！\n".format(index))
            continue
        inputFp = open(inputFilePath, "rb")
        fileData = inputFp.read()
        try:
            if cryptor is None:
                outputFp.write(fileData)
            else:
                outputFp.write(cryptor.decrypt(fileData))
        except Exception as exception:
            #inputFp.close()
            #outputFp.close()
            print(exception)
            #return False
        inputFp.close()
    print("")
    outputFp.close()
    return True

# 6、删除ts文件
def removeTsDir(tsFileDir):
    # 先清空文件夹
    for root, dirs, files in os.walk(tsFileDir, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(tsFileDir)
    return True

# 7、convert to mp4（调用了FFmpeg，将合并好的视频内容放置到一个mp4容器中）
def ffmpegConvertToMp4(inputFilePath, ouputFilePath):
    global logFile
    if not os.path.exists(inputFilePath):
        print(inputFilePath + " 路径不存在！")
        logFile.write(inputFilePath + " 路径不存在！\n")
        return False
    cmd = r'ffmpeg -i "{0}" -vcodec copy -acodec copy "{1}"'.format(inputFilePath, ouputFilePath)
    if os.system(cmd) == 0:
        print(inputFilePath + "转换成功！")
        logFile.write(inputFilePath + "转换成功！\n")
        return True
    else:
        print(inputFilePath + "转换失败！")
        logFile.write(inputFilePath + "转换失败！\n")
        return False

# 8、模拟输出进度条(默认不打印网速)
def printProcessBar(sumCount, doneCount, width, isPrintDownloadSpeed=False):
    global downloadSpeed
    precent = doneCount / sumCount
    useCount = int(precent * width)
    spaceCount = int(width - useCount)
    precent = precent*100
    if isPrintDownloadSpeed:
        # downloadSpeed的单位是B/s, 超过1024*1024转换为MiB/s, 超过1024转换为KiB/s
        if downloadSpeed > 1048576:
            print('\r\t{0}/{1} {2}{3} {4:.2f}% {5:>7.2f}MiB/s'.format(sumCount, doneCount, useCount * '■', spaceCount * '□', precent, downloadSpeed / 1048576),
                  file=sys.stdout, flush=True, end='')
        elif downloadSpeed > 1024:
            print('\r\t{0}/{1} {2}{3} {4:.2f}% {5:>7.2f}KiB/s'.format(sumCount, doneCount, useCount * '■', spaceCount * '□', precent, downloadSpeed / 1024),
                  file=sys.stdout, flush=True, end='')
        else:
            print('\r\t{0}/{1} {2}{3} {4:.2f}% {5:>7.2f}B/s  '.format(sumCount, doneCount, useCount * '■', spaceCount * '□', precent, downloadSpeed),
                  file=sys.stdout, flush=True, end='')
    else:
        print('\r\t{0}/{1} {2}{3} {4:.2f}%'.format(sumCount, doneCount, useCount*'■', spaceCount*'□', precent), file=sys.stdout, flush=True, end='')

# m3u8下载器
def m3u8VideoDownloader():
    global title
    global logFile
    global m3u8Url
    global cachePath
    global downloadedBytes
    global downloadSpeed
    global rootUrlPath
    # 1、下载m3u8
    print("\t1、开始下载m3u8...")
    #cachePath += str(int(time.time()))
    logFile.write("\t1、开始下载m3u8...\n")
    m3u8Info = getM3u8Info()
    if m3u8Info is None:
        return False
    tsList = []
    for playlist in m3u8Info.segments:
        tsList.append(playlist.uri)
    # 2、获取key
    keyText = ""
    cryptor = None
    # 判断是否加密
    if (len(m3u8Info.keys) != 0) and (m3u8Info.keys[0] is not None):
        # 默认选择第一个key，且AES-128算法
        key = m3u8Info.keys[0]
        if key.method != "AES-128":
            print("\t{0}不支持的解密方式！".format(key.method))
            logFile.write("\t{0}不支持的解密方式！\n".format(key.method))
            return False
        # 如果key的url是相对路径，加上m3u8Url的路径
        keyUrl = key.uri
        keyText = None
        print("\t2、开始下载key...")
        logFile.write("\t2、开始下载key...\n")
        if not keyUrl.startswith("http"):
            if '/' == keyUrl[0:1]:
                o = urlparse(m3u8Url)
                #keyUrl = m3u8Url.replace("index.m3u8", keyUrl)
                keyUrl = o.scheme + "://" + o.hostname + keyUrl
            else:
                keyUrl = m3u8Url[0:m3u8Url.rindex('/') + 1] +keyUrl

            keyText = getKey(keyUrl)
        else:
            keyText = getKey(keyUrl)
        if keyText is None:
            return False
        # 判断是否有偏移量
        if key.iv is not None:
            aesiv = None
            if(key.iv[0:2] == '0x'):
                aesiv = hexStringTobytes(key.iv[2:])
            else:
                aesiv = bytes(key.iv, encoding='utf8')
                
            cryptor = AES.new(keyText, AES.MODE_CBC, aesiv)
        else:
            cryptor = AES.new(keyText, AES.MODE_CBC, keyText)
    # 3、下载ts
    print("\t3、开始下载ts...")
    logFile.write("\t3、开始下载ts...\n")
    # 清空bytes计数器
    downloadSpeed = 0
    downloadedBytes = 0
    #print(tsList)
    if mutliDownloadTs(tsList):
        logFile.write("\tts下载完成---------------------\n")
    # 4、合并ts
    print("\t4、开始合并ts...")
    logFile.write("\t4、开始合并ts...\n")
    if mergeTs(cachePath, cachePath + "/cache.flv", cryptor, len(tsList)):
        logFile.write("\tts合并完成---------------------\n")
    else:
        print(keyText)
        print("\tts合并失败！")
        logFile.write("\tts合并失败！\n")
        return False
    # 5、开始转换成mp4
    print("\t5、开始mp4转换...")
    logFile.write("\t5、开始mp4转换...\n")
    ### 当碰到ts 后缀 不转化mp4
    if title[-4:] == '.flv':
        #os.system('mv ' + cachePath + "/cache.flv" + ' ' + saveRootDirPath + "/" + title)
        shutil.move(cachePath + "/cache.flv", saveRootDirPath + "/" + title)
    else:
        if not ffmpegConvertToMp4(cachePath + "/cache.flv", saveRootDirPath + "/" + title + ".mp4"):
            return False
    # 6.清空cache 文件
    if sys.platform.startswith("win"):
        logFile.close()
    removeTsDir(cachePath)
    return True

def donwloadUrl(url_path, outfile):
    global title
    global logFile
    global m3u8Url
    global errorM3u8InfoFp
    global saveRootDirPath

    
    title = os.path.basename(outfile)
    if os.path.dirname(outfile):
        saveRootDirPath = os.path.dirname(outfile)
    m3u8Url=url_path
# title中去除 \  /  :  *  ?  "  <  >  |字符，Windows系统中文件命名不能包含这些字符
    title = title.replace('\\', ' ', sys.maxsize)
    title = title.replace('/', ' ', sys.maxsize)
    title = title.replace(':', ' ', sys.maxsize)
    title = title.replace('*', ' ', sys.maxsize)
    title = title.replace('?', ' ', sys.maxsize)
    title = title.replace('"', ' ', sys.maxsize)
    title = title.replace('<', ' ', sys.maxsize)
    title = title.replace('>', ' ', sys.maxsize)
    title = title.replace('|', ' ', sys.maxsize)

    try:
        print("{0} 开始下载:".format(url_path))
        logFile.write("{0} 开始下载:\n".format(url_path))
        if m3u8VideoDownloader():
            # 成功下载完一个m3u8则清空logFile
            if not sys.platform.startswith("win"):
                logFile.seek(0)
                logFile.truncate()
            print("{0} 下载成功！".format(url_path))
        else:
            errorM3u8InfoFp.write(title + "," + url_path + '\n')
            errorM3u8InfoFp.flush()
            print("{0} 下载失败！".format(url_path))
            logFile.write("{0} 下载失败！\n".format(url_path))
    except Exception as exception:
        print(exception)
        traceback.print_exc()
def defaultMain():
    global title
    global logFile
    global m3u8Url
    global errorM3u8InfoFp
    global m3u8InputFp
    global taskThreadPool
    global processCountConf
    #os.chdir('/Users/smali/data/Project/python3/m3u8_downloader')
    # 判断m3u8文件是否存在
    if not (os.path.exists(m3u8InputFilePath)):
        print("{0}文件不存在！".format(m3u8InputFilePath))
        exit(0)
    m3u8InputFp = open(m3u8InputFilePath, "r", encoding="utf-8")
    # 设置error的m3u8 url输出
    errorM3u8InfoFp = open(errorM3u8InfoDirPath, "a+", encoding="utf-8")
    # 设置log file
    if not os.path.exists(cachePath):
        os.makedirs(cachePath)
    logFile = open(logPath, "w+", encoding="utf-8")
    # 初始化线程池
    taskThreadPool = threadpool.ThreadPool(processCountConf)
    while True:
        rowData = m3u8InputFp.readline()
        rowData = rowData.strip('\n')
        if rowData == "":
            break
        m3u8Info = rowData.split(',')
        title = m3u8Info[0]
        m3u8Url = m3u8Info[1]
        donwloadUrl(m3u8Info[1], m3u8Info[0])
        
    # 关闭文件
    logFile.close()
    m3u8InputFp.close()
    errorM3u8InfoFp.close()
    print("----------------下载结束------------------")
def defaultMain2():
     # 判断m3u8文件是否存在
    if not (os.path.exists(m3u8InputFilePath)):
        print("{0}文件不存在！".format(m3u8InputFilePath))
        exit(0)
    m3u8InputFp = open(m3u8InputFilePath, "r", encoding="utf-8")
    while True:
        rowData = m3u8InputFp.readline()
        rowData = rowData.strip('\n')
        if rowData == "":
            break
        m3u8Info = rowData.split(',')
        os.system('python3 "%s" -i "%s" -o "%s"'%(__file__,m3u8Info[1], m3u8Info[0]))

def main(argv):
    global title
    global logFile
    global m3u8Url
    global errorM3u8InfoFp
    global taskThreadPool
    global processCountConf
    
    m3u8_in_url = ''
    outputfile = ''
    try:
      opts, args = getopt.getopt(argv,"hi:o:p",['help',"ifile=","ofile=","paste"])
    except getopt.GetoptError:
      print('m3u8_download.py -i url -o filename')
      sys.exit(2)
    for opt, arg in opts:
        if opt in ('-h', 'help'):
            print('m3u8_download.py -i url -o filename')
            sys.exit()
        elif opt in ("-i", "--ifile"):
            m3u8_in_url = arg
        elif opt in ("-o", "--ofile"):
            outputfile = arg
        elif opt in ("-p", "--paste"):
            try:
                m3u8_in_url = pyperclip.paste()
            except Exception as e:
                ###兼容termux环境
                if os.system('termux-clipboard-get') == 0:
                    m3u8_in_url = subprocess.getoutput("termux-clipboard-get").strip();
                else:
                    print(e)
                    exit()
            outputfile = str(int(time.time()))
            if(m3u8_in_url[0:4] != 'http'):
                print("error pyperclip input http addr")
                sys.exit(2)
            
    # 设置error的m3u8 url输出
    errorM3u8InfoFp = open(errorM3u8InfoDirPath, "a+", encoding="utf-8")
    # 设置log file
    if not os.path.exists(cachePath):
        os.makedirs(cachePath)
    logFile = open(logPath, "w+", encoding="utf-8")
    # 初始化线程池
    taskThreadPool = threadpool.ThreadPool(processCountConf)
    print('输入的地址为：', m3u8_in_url)
    print('输出的文件为：', outputfile)
    donwloadUrl(m3u8_in_url, outputfile)
    # 关闭文件
    logFile.close()
    errorM3u8InfoFp.close()
if __name__ == '__main__':
    #////// init
    #没有输入任何参数就使用默认的 "m3u8_input.txt" 文件进行下载;
    #//////
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if(len(sys.argv) > 1):
        main(sys.argv[1:])
    else:
        defaultMain2()

