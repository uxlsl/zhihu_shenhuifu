#!encoding=utf-8

from __future__ import print_function

import gevent.monkey
gevent.monkey.patch_socket()

import gzip
import cStringIO
from bs4 import BeautifulSoup
import urllib
import urllib2
import gevent
from gevent.queue import Queue, Empty
from gevent.event import Event
from jinja2 import Template
import operator


questions_queue = Queue(maxsize=100)
is_end = Event()
TEMPLATE = u"""
# 知乎神回复
爬取了知乎2万个问题，选择最有可能是神回复的前1000个
计算公式：score =vote/(5+answer_len^2/10)
{% for item in questions %}
## [{{ item[1] }}]({{ item[5] }}) 得分:{{ item[6] }}
{{ item[2] }}
{% endfor %}

"""


class NotAnswer(Exception):
    pass


def formatStr(s):
    s = s.replace('\n', ' ').replace('\t', ' ')
    return s.strip()


def eval_score(i):
    return 1.0 * i[4] / (5 + (i[3] ** 2) / 10)


def getArticle(qid):
    url = 'http://www.zhihu.com/question/' + qid
    page = urllib2.urlopen(url, timeout=120).read()
    pageSoup = BeautifulSoup(page, 'lxml')
    title = str(pageSoup.title).replace(
        '<title>', '').replace('</title>', '').strip()
    item = pageSoup.find('div', {'class': 'zm-item-answer'})
    if item is None:
        raise NotAnswer("not answer {}".format(url))
    anwser = item.find(
        'div', {'class': 'zm-editable-content clearfix'}).prettify()
    vote = int(item.find(
        'div', {'class': 'zm-item-vote-info'}).get('data-votecount').strip())
    anwser = formatStr(anwser)
    ans_len = len(anwser)
    title = formatStr(title)
    out = [qid, title.decode('utf-8'), anwser,
           ans_len, vote, url]
    score = eval_score(out)
    out.append(score)
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
    return questions, lastId


def get_questions_worker(lastId, max_question=10000):
    """
    获取问题的IDS,并放时队列让问题祥情worker处理
    """
    total = 0
    while True:
        ques, lastId = getQuestions(lastId)
        if not ques:
            break
        for i in ques:
            print('put work {}'.format(i))
            questions_queue.put(i)
            total += 1
            if total > max_question:
                is_end.set()
                return


def question_desc_worker(out):
    """问题祥情获取并进行处理,这里是可以多个
    """
    while not (is_end.is_set() and questions_queue.empty()):
        try:
            qid = questions_queue.get(timeout=120)
            print('get work {}'.format(qid))
            article = getArticle(qid)
            if article[4] != 0:
                out.append(article)
        except NotAnswer as e:
            print(e)
        except Empty:
            gevent.sleep(5)
        except urllib2.URLError:
            gevent.sleep(5)


def craw():
    lastId = '389059437'
    output = 'zhihu.md'
    max_question = 1000000
    out = []
    gevent.joinall(
        [
            gevent.spawn(get_questions_worker, lastId, max_question),
            gevent.spawn(question_desc_worker, out),
            gevent.spawn(question_desc_worker, out),
            gevent.spawn(question_desc_worker, out),
        ]
    )
    print(len(out))
    out = sorted(out, key=operator.itemgetter(6), reverse=True)
    template = Template(TEMPLATE)
    content = template.render(questions=out[:100])
    open(output, 'w').write(content.encode('utf-8'))

if __name__ == '__main__':
    craw()
