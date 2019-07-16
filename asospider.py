from scrapy_tool.scrapy_tool import *
import requests, os, csv, time, sys,sqlite3,re
from bs4 import BeautifulSoup


class asospider():
    def __init__(self):
        #加载下载器
        self.base_url = 'http://aso.niaogebiji.com'
        self.st = scrapy_tool(test_url= self.base_url)
        # 查重器与缓存器
        self.used_url = []
        self.buffer_url = []
        self.used_file_path = 'usedid'
        if os.path.exists(self.used_file_path):
            for i in os.listdir(self.used_file_path):
                with open(os.path.join(self.used_file_path,i),'r') as f:
                    temp = f.read()
                temp = re.sub(r'\s+','',temp)
                templist = temp.split(',')
                self.used_url += templist
        else:
            os.mkdir(self.used_file_path)

        # 新建数据库
        self.conn = sqlite3.connect('data.db')
        self.c = self.conn.cursor()
        try:
            self.c.execute('''create table baseinfo
            (appleid integer primary key,
            appName varchar(50),
            appType varchar(10),
            price varchar(10),
            latestVersion varchar(20),
            developerFirm varchar(50),
            developer varchar(50),
            tags varchar(50),
            releaseDate varchar(20),
            lastestDate varchar(20),
            bundleId varchar(50),
            lastestVer varchar(20),
            size varchar(10),
            payInApp varchar(10),
            support varchar(20),
            compatibility varchar(50),
            lang varchar(20),
            contentRank varchar(10),
            introcontent text,
            artistname varchar(50),
            samepubappnum integer,
            samepubapplist text,
            samepubapplistid text,
            competeappidlist text)''')
            self.conn.commit()
        except:
            pass
        try:
            self.c.execute('''create table version
            (appleid integer,
            verDate varchar(20),
            timestamp integer,
            versionTitle varchar(20),
            versionTitle2 varchar(20),
            filename varchar(30) primary key,
            vercontent text)''')
            self.conn.commit()
        except:
            pass
        try:
            self.c.execute('''create table errorid
            (erroid integer primary key)''')
            self.conn.commit()
        except:
            pass
    def scrape_by_input(self, filepath = 'input'):
        templist = []
        for i in os.listdir(filepath):
            with open(os.path.join(filepath,i), 'r') as f:
                temp = f.read()
            temp = re.sub(r'\s+','',temp)
            templist+=temp.split(',')
        self.buffer_url += list(set(templist))
        for appleid in self.buffer_url:
            if appleid in self.used_url:
                continue
            self.scrape_by_id(appleid)

    def scrape_by_id(self,appleid):
        try:
            # 1. 构造url
            url_dict = self.gen_urls(appleid)
            # 2. 下载网页
            responses = {}
            for k,url in url_dict.items():
                responses[k] = self.download_page(url)
            # 3.解析网页
            bs_result = self.parse_bs(responses['bs'])
            ver_result = self.parse_ver(responses['ver'],appleid)
            pub_result = self.parse_pub(responses['pub'])
            compete_result = self.parse_compete(responses['competitor'])
            # 3.2 对解析获得的数据进行处理
            results = bs_result+pub_result+compete_result

            # #测试用代码
            # print(results)
            # for i in ver_result:
            #     print(i)
            #  4 存储数据
            self.save_to_db(results, 'baseinfo')
            for i in ver_result:
                self.save_to_db(i,'version')
            with open(os.path.join(self.used_file_path,'success.txt'),'a+') as f:
                f.write(',{}'.format(appleid))
            self.used_url.append(appleid)
            print('success: {}'.format(appleid))
            time.sleep(1)
        except:
            self.save_to_db((appleid,),'errorid')
            with open(os.path.join(self.used_file_path,'errorid.txt'),'a+') as f:
                f.write(',{}'.format(appleid))
            self.used_url.append(appleid)
            print('error: {}',format(appleid))


    def gen_urls(self,appleid):
        bsurl = 'http://aso.niaogebiji.com/app/baseinfo?id={}'.format(appleid)
        vurl = 'http://aso.niaogebiji.com/app/version?id={}'.format(appleid)
        purl = 'http://aso.niaogebiji.com/app/samepubapp?id={}'.format(appleid)
        curl = 'http://aso.niaogebiji.com/app/competitor?id={}'.format(appleid)
        url_dict = {'bs': bsurl, 'ver': vurl, 'pub': purl, 'competitor': curl}
        return url_dict
    def download_page(self,url):
        response = self.st.requests_st(url)
        return response
    def parse_bs(self,res):
        soup = BeautifulSoup(res.text, 'html.parser')
        basecontentdiv1 = soup.find('div', class_='appinfoTxt flex1 mobile-hide')
        appName = basecontentdiv1.find('p', class_='appname ellipsis').get_text()
        vdict = {'appleid':'appId','appType': 'category', 'price': 'price', 'latestVersion': 'version'}
        for key in vdict:
            targetdiv = basecontentdiv1.find('div', class_=vdict[key])
            if targetdiv != None:
                try:
                    if key == 'appType' or key == 'appleid':
                        vdict[key] = targetdiv.find('a',{'class': 'rankBlue'}).get_text()
                    else:
                        vdict[key] = targetdiv.find('div', class_='info').get_text()
                except:
                    vdict[key] = ''
            else:
                vdict[key] = ''
        appleid = vdict['appleid']
        appType = vdict['appType']
        price = vdict['price']
        latestVersion = vdict['latestVersion']

        baseinfotable = soup.find('table', class_='base-info base-area mobile-hide')
        variabledict = {"developerFirm": "开发商", "developer": "开发者", "tags": "分类", "releaseDate": "发布日期",
                        "lastestDate": "更新日期", "bundleId": "Bundle ID", "lastestVer": "版本", "size": "大小",
                        "payInApp": "是否有内购", "support": "支持网站", "compatibility": "兼容性", "lang": "语言",
                        "contentRank": "内容评级"}
        for key in variabledict:
            targettd = baseinfotable.find('td', text=variabledict[key])
            if targettd != None:
                try:
                    if key == 'support':
                        variabledict[key] = targettd.next_sibling.a.get_text()
                    else:
                        testtd = targettd.next_sibling.next_sibling
                        variabledict[key] = testtd.get_text()
                except:
                    variabledict[key] = ''
            else:
                variabledict[key] = ''
        developerFirm = variabledict['developerFirm']
        developer = variabledict['developer']
        tags = variabledict['tags']
        releaseDate = variabledict['releaseDate']
        lastestDate = variabledict['lastestDate']
        bundleId = variabledict['bundleId']
        lastestVer = variabledict['lastestVer']
        size = variabledict['size']
        payInApp = variabledict['payInApp']
        support = variabledict['support']
        compatibility = variabledict['compatibility']
        lang = variabledict['lang']
        contentRank = variabledict['contentRank']



        intro = soup.find('div', class_='vertxt')
        if intro != None:
            introcontent = str(intro).replace('<br>', '').replace('<div class="vertxt" style="max-height: 156px;">',
                                                                  '').replace('<div class="vertxt">', '').replace(
                '<br/>',
                '').replace(
                '</div>', '')
            introcontent = re.sub(r'\s+','',introcontent)
        else:
            introcontent = ''
        introfilename = 'intro{}.txt'.format(appleid)

        datatuple = (appleid, appName, appType, price, latestVersion, developerFirm, developer, tags, releaseDate,lastestDate,bundleId, lastestVer, size, payInApp, support, compatibility, lang, contentRank, introcontent)
        return datatuple
    def parse_ver(self,res,appleid):
        soup = BeautifulSoup(res.text, 'html.parser')
        targetdiv = soup.find('div', class_='rankcontent')
        verdivlist = targetdiv.find_all('div', class_='versionItem')
        for verdiv in verdivlist:
            verDate = verdiv.find('div', class_='verDate').get_text()
            versionTitle = verdiv.find('p', class_='versionTitle').get_text()
            versionTitle2 = 'v' + versionTitle
            vertxt = verdiv.find('div', class_='vertxt')
            vercontent = str(vertxt).replace('<div class="vertxt">', '').replace('<br>', '').replace('</div>',
                                                                                                     '').replace(
                '<br/>', '')
            vercontent = re.sub(r'\s+','',vercontent)
            timeArray = time.strptime(verDate, "%Y年%m月%d日")
            timestamp = time.mktime(timeArray)
            filename = '%sv%s.txt' % (appleid, versionTitle)
            filename = filename.replace('.', '_').replace('_txt', '.txt')
            datatuple = (appleid, verDate, timestamp, versionTitle, versionTitle2, filename,vercontent)
            yield datatuple
    def parse_pub(self,res):
        soup = BeautifulSoup(res.text, 'html.parser')
        samepubapp = soup.find('div', {'id': 'samepubapp'})
        artistname = soup.find('div', {'class': 'artistnamezh'}).get_text()
        table = samepubapp.find('tbody')
        if table is None:
            samepubappnum = 0
            samepubapplist = " "
            samepubapplistid = " "
        else:
            tr = table.find_all('tr')
            samepubappnum = len(tr)
            samepubapplist = []
            samepubappidlist = []
            for t in tr:
                ainfo = t.find('a', {'class': 'app_name'})
                sameappid = ainfo['href'].replace('/app/weekdatareport?id=', '')
                sameappname = ainfo.get_text().replace(',', '')
                samepubapplist.append(sameappname)
                samepubappidlist.append(sameappid)
            samepubapplist = '|'.join(samepubapplist)
            samepubapplistid = '|'.join(samepubappidlist)
        datatuple = (artistname, samepubappnum, samepubapplist, samepubapplistid)
        return datatuple
    def parse_compete(self,res):
        competeappidlist = []
        soup = BeautifulSoup(res.text,'html.parser')
        table = soup.find('table',{'class': 'competitorTable'})
        trs = table.tbody.find_all('tr')
        for tr in trs:
            tds = tr.find_all('td')
            if str(tds[3]).find('游戏') >=0:
                temp = tds[1].find('a')
                temp_id = temp['href'].replace('/app/rank?id=','')
                competeappidlist.append(temp_id)
        competeid = '|'.join(competeappidlist)
        return (competeid,)
    def save_to_db(self,datatuple,tablename):
        try:
            self.c.execute('insert into {} values ({}?)'.format(tablename,"?,"*(len(datatuple)-1)),datatuple)
            self.conn.commit()
        except:
            pass
if __name__ == "__main__":
    sp = asospider()
    sp.scrape_by_input()


