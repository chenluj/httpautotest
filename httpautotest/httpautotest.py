#!/usr/bin/env python
# coding:utf8
# author andre.yang

import requests
import xlrd
import sys
import pymysql
import robot
from urllib import urlencode
from robot.libraries.BuiltIn import BuiltIn
import logging
import json

default_encoding = 'utf-8'
if sys.getdefaultencoding() != default_encoding:
    reload(sys)
    sys.setdefaultencoding(default_encoding)

class httpautotest():
    ROBOT_LIBRARY_SCOPE = 'Global'

    def __init__(self):
        self._cache = robot.utils.ConnectionCache('No sessions created')
        self.builtin = BuiltIn()

    def _utf8_urlencode(self, data):
        if type(data) is unicode:
            return data.encode('utf-8')

        if not type(data) is dict:
            return data

        utf8_data = {}
        for k, v in data.iteritems():
            utf8_data[k] = unicode(v).encode('utf-8')
        return urlencode(utf8_data)

    """
    打开excel
    """
    def _openexcel(self, excelurl,sheetname):
        bk = xlrd.open_workbook(excelurl)
        try:
            sh = bk.sheet_by_name(sheetname)
            return sh
        except:
            logging.info("no sheet in %s named %s" % (excelurl, sheetname))
            exit()

    """
    读取excel参数
    """
    def _getexcelparas(self,sheetname,exceldir,num):
        sh = self._openexcel(exceldir, sheetname)
        try:
            row_data=sh.row_values(int(num))
        except Exception, e:
            print u'所选列没有数据'
        return row_data


    #数据校验方法
    def _checkdb(self,host,dbname,username,password,port,excelurl,sheetname,rownum):
        """
        'host': dbhost

        'dbname': database's name

        'username': dbusername

        'password': dbpassword
        
        'port': dbport
        
        'excelurl': exp D://downloads/case.xls
        
        sheetname: sheet's name exp sheet1
        
        rownum :row num
        """
        conn = pymysql.connect(
            host=host,
            port=int(port),
            user=username,
            passwd=password,
            db=dbname,
            charset='utf8'
        )
        cur = conn.cursor()
        ischeckdb = self._getexcelparas(sheetname, excelurl, rownum)[5]
        sqlscript = self._getexcelparas(sheetname, excelurl, rownum)[6]
        expectedvalue=self._getexcelparas(sheetname, excelurl, rownum)[7]
        if ischeckdb == 1:
            size = cur.execute(sqlscript)
            if size> 0:
                logging.info(u"查询出数据条数为 "+str(size)+u" 条")
                info = cur.fetchmany(1)
                jd=str(info[0])[1:-1]
                if type(expectedvalue)==float:
                    jd =jd.replace(' ', '').replace(',', '')
                    expectedvalue=str(int(expectedvalue))
                else:
                    jd=jd.replace(' ', '')
                if jd==expectedvalue:
                    logging.info(u"数据库校验通过")
                else:
                    logging.info(u"数据库校验未通过,预期值: "+str(expectedvalue).replace('.0',''))
                    logging.info(u" 实际值: "+str(info[0][0]))
                    raise AssertionError()
            else :
                logging.info(u"数据库中没有查询到数据")
                raise AssertionError

        elif ischeckdb == 'FLASE' or ischeckdb == '':
            logging.info(u"不进入SQL判断")
        else :
            logging.info(u'第'+str(rownum)+u'行'+u'是否检查数据库输入不合法')
            raise RuntimeError
        cur.close()
        conn.commit()
        conn.close()

    #数据校验
    def _checkdata(self,domain,descontent,remethod,payload,do):
        """
        'domain': server host

        'descontent': wish content

        'remethod': request method

        'payload': params

        'do': request do
        """
        descontent = descontent.replace("\n","")
        descontent = descontent.replace(" ", "")
        descontent = descontent.encode("utf-8")
        payload=payload.encode("utf-8")
        logging.info (u'请求参数为:' + str(payload))
        if remethod.upper() == 'GET':
            res = requests.get(domain + do, params=payload, timeout=3)
            if res.status_code != 200:
                logging.info(u"请求失败,statuscode非200")
                raise AssertionError
            resreplace=res.content.replace(" ", "")
            if descontent == resreplace:
                logging.info(u"接口断言通过")
            else:
                logging.info(u"实际响应数据为:" + res.content.replace(" ", ""))
                logging.info(u"接口断言与期望不符")
                logging.info(u"预期结果为" + descontent)
                raise AssertionError
        elif remethod.upper() == 'POST':
            res = requests.post(domain + do, params=payload, timeout=3)
            if res.status_code != 200:
                logging.info(u"请求失败,statuscode非200")
                raise AssertionError
            resreplace=res.content.replace(" ", "")
            if descontent == resreplace:
                logging.info(u"接口断言通过")
            else:
                logging.info(u"实际响应数据为:" + res.content.replace(" ", ""))
                logging.info(u"与期望不符")
                logging.info(u"预期结果为"+descontent)
                raise AssertionError
        else:
            logging.info(u'请求方式错误')
            logging.info(u'请求方式只能为get/post,现为' + remethod)
            raise AssertionError
        return res.content.decode("utf-8")


    def todict(self, db):
        return eval('dict(%s)' % db)

    #case执行方法
    def testcase(self,domain,sheetname,excelurl,rownum,db):

        """
        'domain': host
        
        'sheetname': sheet's name exp sheet1
        
        'excelurl': exp D://downloads/case.xls
        
        'rownum': row number
        
        'db': database config
        
        Examples:
        | `Testcase` | http://192.168.20.154 | zkk | ${CURDIR}${/}case1${/}case1.xlsx | 1 | ${db} |
        """
        logging.info(u'用例名称: '+self._getexcelparas(sheetname, excelurl, rownum)[0])
        do=self._getexcelparas(sheetname, excelurl, rownum)[1]#方法名
        remethod=self._getexcelparas(sheetname, excelurl, rownum)[2]#请求方式
        payload=self._getexcelparas(sheetname, excelurl, rownum)[3]#请求参数
        descontent=self._getexcelparas(sheetname, excelurl, rownum)[4]#预期结果
        res=self._checkdata(domain,descontent, remethod, payload, do)
        db=self.todict(db)
        self._checkdb(db['host'], db['db'], db['user'],db['passwd'],db['port'],excelurl, sheetname, rownum)
        return res

    def testcase_one(self,domain,sheetname,excelurl,rownum,*args):
        do = self._getexcelparas(sheetname, excelurl, rownum)[1]
        remethod = self._getexcelparas(sheetname, excelurl, rownum)[2]
        payload = self._getexcelparas(sheetname, excelurl, rownum)[3]
        res=self._getres(domain,remethod,payload,do,*args)
        return res

    def to_json(self, content, pretty_print=False):
        """ Convert a string to a JSON object
        `content` String content to convert into JSON
        'pretty_print' If defined, will output JSON is pretty print format
        """
        content = self._utf8_urlencode(content)
        if pretty_print:
            json_ = self._json_pretty_print(content)
        else:
            json_ = json.loads(content)
        return json_

    def _getres(self,domain, remethod, payload, do,*args):
        payload = payload.encode("utf-8")
        if len(args)==0:
            payload_b=''
        else:
            payload_b=args[0]
        if remethod.upper() == 'GET':
            res = requests.get(domain + do, params=payload+'&'+payload_b, timeout=3)
            resd = res.content.decode("utf-8")
            return resd
        elif remethod.upper() == 'POST':
            res = requests.post(domain + do, params=payload +'&'+payload_b, timeout=3)
            resd=res.content.decode("utf-8")
            return resd
        else:
            logging.info(u'请求方式错误')
            logging.info(u'请求方式只能为get/post,现为' + remethod)
            raise AssertionError

if __name__ == '__main__':
    a=httpautotest()
    a.testcase('http://192.168.20.154','测试1','../case1.xlsx',2,"host='192.168.20.155',db='zlax_test',user='test',passwd='test123',port=3306")
