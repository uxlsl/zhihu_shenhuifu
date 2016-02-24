#!encoding=utf-8
from __future__ import print_function
import json
import gzip
import cStringIO
from bs4 import BeautifulSoup
import urllib
import urllib2
import requests


class NotAnswer(Exception):
    pass


def formatStr(s):
    s = s.replace('\n', ' ').replace('\t', ' ')
    return s.strip()


def getArticle(url):
    print("getArticle {}".format(url))
    page = requests.get(url, timeout=120).content
    pageSoup = BeautifulSoup(page, 'lxml')
    title = str(pageSoup.title).replace(
        '<title>', '').replace('</title>', '').strip()
    item = pageSoup.find('div', {'class': 'zm-item-answer'})
    if item is None:
        raise NotAnswer("not answer {}".format(url))
    anwser = item.find(
        'div', {'class': 'zm-editable-content clearfix'}).get_text().strip()
    vote = item.find(
        'div', {'class': 'zm-item-vote-info'}).get('data-votecount').strip()
    anwser = formatStr(anwser)
    ans_len = len(anwser)
    if ans_len > 100:
        anwser = anwser[0:100]
    title = formatStr(title)
    out = [title, anwser.encode('utf-8'),
           str(ans_len), vote, url]
    return out


def getQuestions(start, offset='20'):
    headers = {"Accept": "*/*",
               "Accept-Encoding": "gbk,utf-8,gzip,deflate,sdch",
               "Accept-Language": "zh-CN,zh;q=0.8,en;q=0.6",
               "Connection": "keep-alive",
               "Content-Length": "64",
               "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
               'Cookie': 'q_c1=11ae11e29d0549e99c5b02ee7388c83e|1453711645000|1446823503000; cap_id="MjQ1MWI4YjcwMmFhNDhjMTgzNGU0NzgyYTk4MjZhOWY=|1453773322|1c44b89a03af2ed4a3b4c4080a50c57af165c212"; _za=2e51ba39-3ff3-4b44-bd2d-805b2b6fefa6; z_c0="QUFBQVdySXhBQUFYQUFBQVlRSlZUUjlmemxZLUdyRmwtaHRKWks5a0lFSkh2RDZZUkRWd2xnPT0=|1453773343|166a2a76c536590e2289a10a7ebca3773689dfa8"; _xsrf=abd9920df9f46cbb3f864781fbce5ed7; aliyungf_tc=AQAAAJGmD2+H0QsA+fDM3fo68NCu0P+L',
               "Host": "www.zhihu.com",
               "Origin": "http://www.zhihu.com",
               "Referer": "http://www.zhihu.com/log/questions",
               "User-Agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.137 Safari/537.36",
               "X-Requested-With": "XMLHttpRequest"
               }

    parms = {'start': start,
             'offset': offset,
             '_xsrf': 'abd9920df9f46cbb3f864781fbce5ed7'}
    url = 'http://www.zhihu.com/log/questions'
    req = urllib2.Request(url, headers=headers, data=urllib.urlencode(parms))
    content = urllib2.urlopen(req).read()
    html = gzip.GzipFile(fileobj=cStringIO.StringIO(content)).read()
    html = eval(html)['msg'][1]
    pageSoup = BeautifulSoup(html, 'lxml')
    questions = []
    items = pageSoup.find_all('div', {'class': 'zm-item'})
    for item in items:
        url = item.find_all('a', {'target': '_blank'})[
            0].get('href').rsplit('/', 1)[1]
        questions.append(url)
    lastId = items[-1].get('id').split('-')[1]
    print(questions, lastId)
    return questions, lastId


def craw():
    wf = open('zhihu.txt', 'a+')
    domain = 'http://www.zhihu.com/question/'
    lastId = '389059437'
    for i in xrange(10000):
        print (i, lastId)
        ques, lastId = getQuestions(lastId)
        for q in ques:
            try:
                out = getArticle(domain + q)
                wf.write(json.dumps(out) + '\n')
            except NotAnswer as e:
                print(e)
            except requests.Timeout as e:
                pass

    wf.close()
if __name__ == '__main__':
    craw()
