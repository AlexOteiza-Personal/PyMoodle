import urllib
import requests
import lxml.html
from lxml.html import fromstring
import urlparse
import os
import sys
import time
import threading

RESOURCE_FOLDER = "folder.gif"

RESOURCE_WEB = "web.gif"
RESOURCE_HTML = "html.gif"
RESOURCE_DOC = "word.gif"
RESOURCE_DOCX = "docx.gif"
RESOURCE_PPT = "powerpoint.gif"
RESOURCE_PPTX = "ppt.gif"
RESOURCE_XLS = "excel.gif"
RESOURCE_XLSX = "xlsx.gif"
RESOURCE_PDF = "pdf.gif"
RESOURCE_VIDEO = "video.gif"
RESOURCE_ZIP = "zip.gif"

DOWNLOAD_RESOURCES = [
    RESOURCE_FOLDER ,
    RESOURCE_DOC,
    RESOURCE_DOCX ,
    RESOURCE_PPT ,
    RESOURCE_PPTX ,
    RESOURCE_XLS ,
    RESOURCE_XLSX ,
    RESOURCE_PDF ,
    RESOURCE_VIDEO ,
    RESOURCE_ZIP 
]


VERSION = '0.90a'

DEF_DIR =  os.path.join(os.path.expanduser("~"),"Apuntes")


class ResourceScrapError(Exception):
    def error(self,filename=None):
        if filename:
            return "Error: El apunte '%s' todavia no es soportado por este programa" % filename
        else:
            return "Error: El apunte todavia no es soportado por este programa"


class FileNotFoundError(Exception):
    def error(self,filename=None):
        if filename:
            return "Error: El archivo '%s' no se encuentra en el servidor" % filename
        else:
            return "Error: No se ha econtrado el archivo en el servidor"

class MoodleDownloader():

    def __init__(self,username,password):
        self.session = requests.Session()
        self.username = username
        self.password = password
        self.logged = False
        

    def login(self):
        r = self.session.post("http://moodle4.ehu.es/login/index.php",
                               data={'username' : username,
                                     'password' : password})
        if not '<div class="loginerrors">' in r.content:
            self.logged = True
        return self.logged

    def __save_file(self,url,path,payload={}):
        request = self.session.get(url,params=payload,stream=True)
        if request.headers['Content-Disposition']:
            filename = request.headers['Content-Disposition'].split("filename=")[1][1:-1]
        else:
            filename = urllib.unquote(urlparse.urlsplit(request.url).path.split("/")[-1])
        size = request.headers['Content-Length']
        if size:
            size = int(size)
            displaysize = size/1024
            if displaysize > 1023:
                displaysize = float(displaysize)/1024
                print "Descargando %s... (%.2f MB)" % (filename,displaysize)
            else:
                print "Descargando %s... (%i KB)" % (filename,displaysize)
            buf = 1
            read = 0
            perc = 0
            with open(os.path.join(path,filename),"wb") as f:
                while buf:
                    buf = request.raw.read(8192)
                    read += len(buf)
                    perc = read*100/size
                    sys.stdout.write('Descargado %i%%\r' % perc)
                    f.write(buf)
            sys.stdout.write('Descargado 100%\n')    

        else:
            print "Descargando %s... (? MB)" % filename
            with open(os.path.join(path,filename),"wb") as f:
                f.write(request.content)

    def __get_html(self,url,payload={}):
        req = self.session.get(url,params=payload,stream=True)
        if 'html' in req.headers['content-type']:
            return fromstring(req.content)
        else:
            return None

    def __clean(self,string):
        for i in "()01234567890\\/?<>|":
            if i in string:
                string = string.replace(i,"")
        return string.rstrip(" ")



    def download(self,directory=DEF_DIR):
        root = self.__get_html("http://moodle4.ehu.es")
        coursename = ""
        for course in root.cssselect("div.coursebox"):
            try:
                link = course.cssselect("div.info")[0].cssselect("div.name")[0].cssselect("a")[0]
                coursename = self.__clean(link.text)
                print "\n%s\n" % coursename
                coursepath = os.path.join(directory,coursename)
                if not os.path.exists(coursepath):
                    os.makedirs(coursepath)
                rootcourse = self.__get_html(link.get("href"))
                resources = rootcourse.cssselect("li.activity.resource")
                for resource in resources:
                    try:
                        self.__process_resource(resource,coursepath)
                    except ResourceScrapError as ex:
                        print ex.error(resource.cssselect("a")[0].cssselect("span")[0].text)
                        continue
                    except FileNotFoundError as ex:
                        print ex.error(resource.cssselect("a")[0].cssselect("span")[0].text)
                        continue
                        
            except KeyboardInterrupt:
                print "Cancelada descarga de %s" % coursename

    def __process_resource(self,resource,path):
        resourcelink = resource.cssselect("a")[0]
        resourcetype = resource.cssselect("img.activityicon")[0].get("src").split("/")[-1]
        if not resourcetype in DOWNLOAD_RESOURCES:
            return
        if resourcetype == RESOURCE_FOLDER:
            self.__process_folder(resource,path)
        else:
            popuphtml = self.__get_html(resourcelink.get("href"))
            if popuphtml is not None:
                self.__process_popup(popuphtml,path)
            else:
                self.__save_file(resourcelink.get("href"),path)

    def __process_folder(self,resource,path):
        resourcelink = resource.cssselect("a")[0]
        foldername = resourcelink.cssselect("span")[0]
        folderpath = os.path.join(path,foldername.text)
        if not os.path.exists(folderpath):
            os.makedirs(folderpath)
        files = self.__get_html(resourcelink.get("href")).cssselect("tr.file")
        for f in files:
            poplink = f.cssselect("td.name")[0].cssselect("a")[0]
            self.__save_file(poplink.get("href"),folderpath)


    def __process_popup(self,popuphtml,path):
        poplink = popuphtml.cssselect("div.popupnotice")
        if len(poplink) > 0:
            poplink = poplink[0].cssselect("a")[0]
        else:
            poplink = popuphtml.cssselect("div.resourcepdf")
            if len(poplink) == 0:
                raise ResourceScrapError()
            poplink = poplink[0].cssselect("a")[0]
        
        popdirect = self.__get_html(poplink.get("href"))
        if popdirect is None:
            self.__save_file(poplink.get("href"),path)
        else:
            if len(popdirect.cssselect('div.box.errorbox'))>0:
                 raise FileNotFoundError
            else:
                directlink = popdirect.cssselect("div.popupnotice")[0].cssselect("a")[0]
                self.__save_file(directlink.get("href"),path)
                

class ProgressBarThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.work = True
    def run(self):
        chars = "\\|/-"
        i=0;
        while self.work:
            sys.stdout.write('Conectando %s\r' % chars[i%4])
            time.sleep(0.1)
            i += 1

print "|----------------------------------------------|"
print "|                                              |"
print "| Moodle Downloader %s by Alejandro Garcia  |" % VERSION
print "|                                              |"
print "|----------------------------------------------|\n"

logged = False
while not logged:
    username = raw_input("Introduce usuario: ")
    password = raw_input("Introduce password: ")
    moodle = MoodleDownloader(username,password)
    prog = ProgressBarThread()
    prog.start()
    logged = moodle.login()
    prog.work = False
    if logged:
        print "Conectado a Moodle como %s" % username
    else:
        print "Error: usuario y password no v\xa0lidos"

path = raw_input("Indica la ruta (Pulsa INTRO para guardar en: %s): " % DEF_DIR)
if path == "":
    print "Guardando en %s" % os.path.abspath(DEF_DIR)
    moodle.download()
    print "\nCompletado :)"
    time.sleep(0.5)
else:
    print "Guardando en %s" % os.path.abspath(path)
    moodle.download(directory=path)
    print "\nCompletado :)"
    time.sleep(0.5)
        
