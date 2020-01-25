# -*- coding: utf-8 -*-
# Based on AtileHD concept by schomi & plnick
# Modified by RAED for Open Vision

from inits import *
from Components.ActionMap import ActionMap
from Components.config import *
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from enigma import eTimer
from Components.MenuList import MenuList
from Screens.InputBox import InputBox
from Plugins.Plugin import PluginDescriptor
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Standby import TryQuitMainloop
from Tools.Directories import *
from Tools.LoadPixmap import LoadPixmap
from inits import PluginLanguagePath, iFlatFHDInfo, SkinPath
from debug import printDEBUG
from Components.Console import Console as iConsole
try:
    from Screens.SkinSelector import SkinSelector
except:
    from Plugins.SystemPlugins.SkinSelector.plugin import SkinSelector

#system imports
from os import listdir, remove, rename, system, path, symlink, chdir, rmdir, mkdir
import shutil
import re

#Translations part
from Components.Language import language
currLang = language.getLanguage()[:2] #used for descriptions keep GUI language in 'pl|en' format

try:
    from os import path
    if path.exists(PluginLanguagePath):
        raise ValueError('a hack :)')
    from Components.LanguageGOS import gosgettext as _
except:
    from inits import PluginLanguageDomain
    from Components.Language import language
    import gettext
    from os import environ

    def localeInit():
        lang = language.getLanguage()[:2]
        environ["LANGUAGE"] = lang
        gettext.bindtextdomain(PluginLanguageDomain, PluginLanguagePath)

    def _(txt):
        t = gettext.dgettext(PluginLanguageDomain, txt)
        if t == txt:
                t = gettext.gettext(txt)
        return t

    localeInit()
    language.addCallback(localeInit)

def trace_error():
    import sys
    import traceback
    try:
        traceback.print_exc(file=sys.stdout)
        traceback.print_exc(file=open('/tmp/iFlatFHD.log', 'a'))
    except:
        pass

def logdata(label_name = '', data = None):
    try:
        data=str(data)
        fp = open('/tmp/iFlatFHD.log', 'a')
        fp.write( str(label_name) + ': ' + data+"\n")
        fp.close()
    except:
        trace_error()    
        pass

#iFlatFHD permanent configs, we use iFlatFHD for compatibility reasons
config.plugins.iFlatFHD = ConfigSubsection()
config.plugins.iFlatFHD.refreshInterval = ConfigNumber(default=30) #in minutes
try:
        config.plugins.iFlatFHD.city = ConfigText(default="manama", visible_width = 250, fixed_size = False)       
        config.plugins.iFlatFHD.windtype = ConfigSelection(default="ms", choices = [
                ("ms", _("m/s")),
                ("fts", _("ft/s")),
                ("kmh", _("km/h")),
                ("mph", _("mp/h")),
                ("knots", _("knots"))])
        config.plugins.iFlatFHD.degreetype = ConfigSelection(default="C", choices = [
                ("C", _("Celsius")),
                ("F", _("Fahrenheit"))])
        config.plugins.iFlatFHD.weather_location= ConfigText(default="bh-BH", visible_width = 250, fixed_size = False)       
except:
        trace_error()
        pass

def readurl(url):
    import urllib2
    try:
        req = urllib2.Request(url)
        response = urllib2.urlopen(req)
        data = response.read()
        response.close()
        return data
    except urllib2.URLError as e:
        if hasattr(e, 'code'):
            print 'We failed with error code - %s.' % e.code
          
        elif hasattr(e, 'reason'):
            print 'We failed to reach a server.'
            print 'Reason: %s' % e.reason

def getcities(weather_location):
        url='http://www.geonames.org/advanced-search.html?q=&country=%s&featureClass=P&continentCode=' % weather_location.upper()
        #url='http://www.geonames.org/search.html?q=&country=%s' % weather_location
        data=readurl(url)
        if data is None:
                return []
        try:
                regx='''<a href=".*?"><img src=".*?" border="0" alt=".*?"></a></td><td><a href=".*?">(.*?)</a>'''
                match=re.findall(regx,data, re.M|re.I)
                cities=[]
                for item in match:
                    cityName=item.replace(',',"").strip()
                    try:
                            cityName=cityName.encode("utf-8","ignore")
                    except:
                            pass
                    if cityName in cities:
                        continue
                    cities.append(cityName)
                cities.sort()
                return cities                   
        except:
                return []
        
def Plugins(**kwargs):
    return [PluginDescriptor(name=_("iFlatFHD Setup"), description=_("Personalize your Skin"), where = PluginDescriptor.WHERE_MENU, fnc=menu)]

def menu(menuid, **kwargs):
    for line in open("/etc/enigma2/settings"):
         if "config.skin.primary_skin=iFlatFHD/skin.xml" in line:
              if menuid == "mainmenu":
                return [(_("Setup -") + " " + CurrentSkinName, main, "iFlatFHD_Menu", 40)]
    return []

def main(session, **kwargs):
    printDEBUG("Opening Menu ...")
    session.open(iFlatFHD_Config)

def isInteger(s):
	try: 
		int(s)
		return True
	except ValueError:
		return False

class WeatherLocationChoiceList(Screen):
	skin = """
		<screen name="WeatherLocationChoiceList" position="center,center" size="1280,720" title="Location list" >
			<widget source="Title" render="Label" position="70,47" size="950,43" font="Regular;35" transparent="1" />
			<widget name="choicelist" position="70,115" size="700,480" scrollbarMode="showOnDemand" scrollbarWidth="6" transparent="1" />
			<eLabel position=" 55,675" size="290, 5" zPosition="-10" backgroundColor="red" />
			<eLabel position="350,675" size="290, 5" zPosition="-10" backgroundColor="green" />
			<eLabel position="645,675" size="290, 5" zPosition="-10" backgroundColor="yellow" />
			<eLabel position="940,675" size="290, 5" zPosition="-10" backgroundColor="blue" />
			<widget name="key_red" position="70,635" size="260,25" zPosition="1" font="Regular;20" halign="left" foregroundColor="foreground" transparent="1" />
			<widget name="key_green" position="365,635" size="260,25" zPosition="1" font="Regular;20" halign="left" foregroundColor="foreground" transparent="1" />
		</screen>
		"""

	def __init__(self, session, country):
		self.session = session
		self.country = country
		list = []
		Screen.__init__(self, session)
		self.title = _(country)
		self["choicelist"] = MenuList(list)
		self["key_red"] = Label(_("Cancel"))
		self["key_green"] = Label(_("Add city"))
		self["myActionMap"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"ok": self.keyOk,
			"green": self.add_city,
			"cancel": self.keyCancel,
			"red": self.keyCancel,
		}, -1)
                self.iConsole = iConsole()		
                self.timer = eTimer()
                self.timer.callback.append(self.createChoiceList)
                self.timer.start(5, False)

	def createChoiceList(self):
                self.timer.stop()
		list = []
		list=getcities(self.country)
		self["choicelist"].l.setList(list)

	def control_xml(self, result, retval, extra_args):
		if retval is not 0:
			self.write_none()

	def write_none(self):
		with open('/tmp/weathermsn.xml', 'w') as noneweather:
			noneweather.write('None')
		noneweather.close()

	def get_xmlfile(self,weather_city,weather_location):
                degreetype = config.plugins.iFlatFHD.degreetype.value
                weather_city=weather_city.replace(" ","+")
                url='http://weather.service.msn.com/data.aspx?weadegreetype=%s&culture=%s&weasearchstr=%s&src=outlook' % (degreetype, weather_location, weather_city)
                file_name='/tmp/weathermsn.xml'
                import urllib
                # Download the file from `url` and save it locally under `file_name`:
                try:
                       urllib.urlretrieve(url, file_name)
                       return True
                except:
                       return False
		#self.iConsole.ePopen("wget -P /tmp -T2 'http://weather.service.msn.com/data.aspx?weadegreetype=%s&culture=%s&weasearchstr=%s&src=outlook' -O /tmp/weathermsn.xml" % (degreetype, weather_location, weather_city), self.control_xml)

        def add_city(self):
                 self.session.openWithCallback(self.cityCallback, InputBox, title=_("Please enter a name of the city"), text="cityname", maxSize=False, visible_width =250)

        def cityCallback(self,city=None):
                if city:
                        if os.path.exists('/tmp/weathermsn.xml'):
                          os.remove('/tmp/weathermsn.xml')
                        returnValue = city
                        countryCode=self.country.lower()+"-"+self.country.upper()
                        if self.get_xmlfile(returnValue,countryCode)==False:
                          self.session.open(MessageBox, _("Sorry, your city is not available."),MessageBox.TYPE_ERROR)
                          return 
                        if not fileExists('/tmp/weathermsn.xml'):
                                self.write_none()
                                self.session.open(MessageBox, _("Sorry, your city is not available."),MessageBox.TYPE_ERROR)
                                return None
                        if returnValue is not None:
                                self.close(returnValue)
                        else:
                                self.keyCancel()

	def keyOk(self):
                if os.path.exists('/tmp/weathermsn.xml'):
                  os.remove('/tmp/weathermsn.xml')
		returnValue = self["choicelist"].l.getCurrentSelection()
		countryCode=self.country.lower()+"-"+self.country.upper()
		if self.get_xmlfile(returnValue,countryCode)==False:
                  self.session.open(MessageBox, _("Sorry, your city is not available."),MessageBox.TYPE_ERROR)
                  return 
		if not fileExists('/tmp/weathermsn.xml'):
			self.write_none()
			self.session.open(MessageBox, _("Sorry, your city is not available."),MessageBox.TYPE_ERROR)
			return None
		if returnValue is not None:
			self.close(returnValue)
		else:
			self.keyCancel()

	def keyCancel(self):
		self.close(None)

class iFlatFHD_Config(Screen, ConfigListScreen):
    skin = """
  <screen name="iFlatFHD_Config" position="82,124" size="1101,376" title="iFlatFHD Setup" backgroundColor="transparent" flags="wfNoBorder">
    <eLabel position="7,2" size="1091,372" zPosition="-15" backgroundColor="#20000000" />
    <eLabel position="4,51" size="664,238" zPosition="-10" backgroundColor="#20606060" />
    <eLabel position="672,51" size="410,237" zPosition="-10" backgroundColor="#20606060" />
    <eLabel position="6,302" size="240,55" zPosition="-10" backgroundColor="#20b81c46" />
    <eLabel position="284,302" size="240,55" zPosition="-10" backgroundColor="#20009f3c" />
    <eLabel position="564,302" size="240,56" zPosition="-10" backgroundColor="#209ca81b" />
    <eLabel position="843,302" size="240,55" zPosition="-10" backgroundColor="#202673ec" />
    <widget source="Title" render="Label" position="2,4" size="889,43" font="Regular;35" foregroundColor="#00ffffff" backgroundColor="#004e4e4e" transparent="1" />
    <widget name="config" position="6,55" size="657,226" scrollbarMode="showOnDemand" transparent="1" />
    <widget name="Picture" position="676,56" size="400,225" alphatest="blend" />
    <widget name="key_red" position="18,316" size="210,25" zPosition="1" font="Regular;20" halign="left" foregroundColor="#00ffffff" backgroundColor="#20b81c46" transparent="1" />
    <widget name="key_green" position="299,317" size="210,25" zPosition="1" font="Regular;20" halign="left" foregroundColor="#00ffffff" backgroundColor="#20009f3c" transparent="1" />
    <widget name="key_yellow" position="578,317" size="210,25" zPosition="1" font="Regular;20" halign="left" foregroundColor="#00ffffff" backgroundColor="#209ca81b" transparent="1" />
    <widget name="key_blue" position="854,318" size="210,25" zPosition="0" font="Regular;20" halign="left" foregroundColor="#00ffffff" backgroundColor="#202673ec" transparent="1" />
  </screen>
"""
    skin_lines = []
    changed_screens = False

    def __init__(self, session, args = 0):
        self.session = session
        Screen.__init__(self, session)
        
        myTitle=_("iFlatFHD Setup %s") % iFlatFHDInfo
        self.setTitle(myTitle)
        try:
            self["title"]=StaticText(myTitle)
        except:
            pass
            
        self.skin_base_dir = SkinPath
        self.currentSkin = CurrentSkinName
        printDEBUG("self.skin_base_dir=%s, skin=%s, currentSkin=%s" % (self.skin_base_dir, config.skin.primary_skin.value, self.currentSkin))
        if self.currentSkin != '':
                self.currentSkin = '_' + self.currentSkin # default_skin = '', others '_skinname', used later

        if path.exists(resolveFilename(SCOPE_PLUGINS, 'SystemPlugins/VTIPanel/')):
            self.isVTI = True
        else:
            self.isVTI = False
            
        self.defaultOption = "default"
        self.defaults = (self.defaultOption, _("Default"))
        self.color_file = "skin_user_colors.xml"
        self.user_font_file = "skin_user_header.xml"
        
        if path.exists(self.skin_base_dir):
            #FONTS
            if path.exists(self.skin_base_dir + self.user_font_file):
                self.default_font_file = path.basename(path.realpath(self.skin_base_dir + self.user_font_file))
                printDEBUG("self.default_font_file = " + self.default_font_file )
            else:
                self.default_font_file = self.defaultOption
            if not path.exists(self.skin_base_dir + "allFonts/"):
                mkdir(self.skin_base_dir + "allFonts/")
            #COLORS
            if path.exists(self.skin_base_dir + self.color_file):
                self.default_color_file = path.basename(path.realpath(self.skin_base_dir + self.color_file))
                printDEBUG("self.default_color_file = " + self.default_color_file )
            else:
                self.default_color_file = self.defaultOption
                
            if not path.exists(self.skin_base_dir + "allColors/"):
                mkdir(self.skin_base_dir + "allColors/")
            #PREVIEW
            if not path.exists(self.skin_base_dir + "allPreviews"):
                mkdir(self.skin_base_dir + "allPreviews/")
            if path.exists(self.skin_base_dir + "preview"):
                if self.isVTI == False and path.isdir(self.skin_base_dir + "preview"):
                    try: rmdir(self.skin_base_dir + "preview")
                    except: pass
            else:
                if self.isVTI == True:
                    symlink(self.skin_base_dir + "allPreviews", self.skin_base_dir + "preview")
            #SELECTED Skins folder - We use different folder name (more meaningfull) for selections
            if path.exists(self.skin_base_dir + "mySkin_off"):
                if not path.exists(self.skin_base_dir + "iFlatFHD_Selections"):
                    chdir(self.skin_base_dir)
                    try:
                        rename("mySkin_off", "iFlatFHD_Selections")
                    except:
                        pass

        current_color = self.getCurrentColor()[0]
        current_font = self.getCurrentFont()[0]
        myiFlatFHD_active = self.getmySkinState()
        self.myiFlatFHD_active = NoSave(ConfigYesNo(default=myiFlatFHD_active))
        self.myiFlatFHD_font = NoSave(ConfigSelection(default=current_font, choices = self.getPossibleFont()))
        self.myiFlatFHD_style = NoSave(ConfigSelection(default=current_color, choices = self.getPossibleColor()))
        self.myiFlatFHD_fake_entry = NoSave(ConfigNothing())
        self.LackOfFile = ''
        self.list = []
        ConfigListScreen.__init__(self, self.list, on_change = self.changedEntry)
        #ConfigListScreen.__init__(self, self.list, session = self.session, on_change = self.changedEntry) ## remove keyboard from city search line

        self["key_red"] = Label(_("Cancel"))
        self["key_green"] = Label(_("OK"))
        self["key_yellow"] = Label()
        self["key_blue"] = Label(_("About"))
        self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
            {
                "green": self.keyGreen,
                "red": self.cancel,
                "yellow": self.keyYellow,
                "blue": self.about,
                "cancel": self.cancel,
                "ok": self.keyOk,
            }, -2)
            
        self["Picture"] = Pixmap()
        
        if not self.selectionChanged in self["config"].onSelectionChanged:
            self["config"].onSelectionChanged.append(self.selectionChanged)
        
        self.createConfigList()
        self.updateEntries = False
        
    def createConfigList(self):
        self.set_color = getConfigListEntry(_("Colors:"), self.myiFlatFHD_style)
        self.set_font = getConfigListEntry(_("Font:"), self.myiFlatFHD_font)
        self.set_myatile = getConfigListEntry(_("Enable skin personalization:"), self.myiFlatFHD_active)
        self.set_new_skin = getConfigListEntry(_("Change skin"), ConfigNothing())
        self.list = []
        self.list.append(self.set_myatile)
        self.list.append(self.set_color)
        self.list.append(self.set_font)
	self.list.append(self.set_new_skin)
	self.list.append(getConfigListEntry(_("---MSN Weather---"), self.myiFlatFHD_fake_entry))
	self.list.append(getConfigListEntry(_("Refresh interval in minutes:"), config.plugins.iFlatFHD.refreshInterval))
        self.list.append(getConfigListEntry(_("Temperature unit:"), config.plugins.iFlatFHD.degreetype))
        self.find_city = getConfigListEntry(_("Location #press OK to change:"), config.plugins.iFlatFHD.city)
	self.list.append(self.find_city)

        self["config"].list = self.list
        self["config"].l.setList(self.list)
        if self.myiFlatFHD_active.value:
            self["key_yellow"].setText(_("User skins"))
        else:
            self["key_yellow"].setText("")

    def changedEntry(self):
        self.updateEntries = True
        printDEBUG("[iFlatFHD:changedEntry]")
        if self["config"].getCurrent() == self.set_color:
            self.setPicture(self.myiFlatFHD_style.value)
        elif self["config"].getCurrent() == self.set_font:
            self.setPicture(self.myiFlatFHD_font.value)
        elif self["config"].getCurrent() == self.set_myatile:
            if self.myiFlatFHD_active.value:
                self["key_yellow"].setText(_("User skins"))
            else:
                self["key_yellow"].setText("")

    def selectionChanged(self):
        if self["config"].getCurrent() == self.set_color:
            self.setPicture(self.myiFlatFHD_style.value)
        elif self["config"].getCurrent() == self.set_font:
            self.setPicture(self.myiFlatFHD_font.value)
        else:
            self["Picture"].hide()

    def cancel(self):
        if self["config"].isChanged():
            self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Save settings?"), MessageBox.TYPE_YESNO, default = False)
        else:
            for x in self["config"].list:
                x[1].cancel()
            if self.changed_screens:
                self.restartGUI()
            else:
                self.close()

    def cancelConfirm(self, result):
        if result is None or result is False:
            printDEBUG("Cancel confirmed.")
        else:
            printDEBUG("Cancel confirmed. Config changes will be lost.")
            for x in self["config"].list:
                x[1].cancel()
            self.close()
                
    def getPossibleColor(self):
        color_list = []
        color_list.append(self.defaults)
        
        if not path.exists(self.skin_base_dir + "allColors/"):
            return color_list
        
        for f in sorted(listdir(self.skin_base_dir + "allColors/"), key=str.lower):
            if f.endswith('.xml') and f.startswith('colors_'):
                friendly_name = f.replace("colors_atile_", "").replace("colors_", "")
                friendly_name = friendly_name.replace(".xml", "")
                friendly_name = friendly_name.replace("_", " ")
                color_list.append((f, friendly_name))
        
        for f in sorted(listdir(self.skin_base_dir), key=str.lower):
            if f.endswith('.xml') and f.startswith('colors_'):
                friendly_name = f.replace("colors_atile_", "").replace("colors_", "")
                friendly_name = friendly_name.replace(".xml", "")
                friendly_name = friendly_name.replace("_", " ")
                color_list.append((f, friendly_name))

        return color_list

    def getPossibleFont(self):
        font_list = []
        font_list.append(self.defaults)
        
        if not path.exists(self.skin_base_dir + "allFonts/"):
            return font_list
        
        for f in sorted(listdir(self.skin_base_dir + "allFonts/"), key=str.lower):
            if f.endswith('.xml') and f.startswith('font_'):
                friendly_name = f.replace("font_atile_", "").replace("font_", "")
                friendly_name = friendly_name.replace(".xml", "")
                friendly_name = friendly_name.replace("_", " ")
                font_list.append((f, friendly_name))

        for f in sorted(listdir(self.skin_base_dir), key=str.lower):
            if f.endswith('.xml') and f.startswith('font_'):
                friendly_name = f.replace("font_atile_", "").replace("font_", "")
                friendly_name = friendly_name.replace(".xml", "")
                friendly_name = friendly_name.replace("_", " ")
                font_list.append((f, friendly_name))

        return font_list

    def getmySkinState(self):
        chdir(self.skin_base_dir)
        if path.exists("mySkin"):
            return True
        else:
            return False

    def getCurrentColor(self):
        myfile = self.skin_base_dir + self.color_file
        if not path.exists(myfile):
            if path.exists(self.skin_base_dir + "allColors/" + self.default_color_file):
                if path.islink(myfile):
                    remove(myfile)
                chdir(self.skin_base_dir)
                symlink("allColors/" + self.default_color_file, self.color_file)
            else:
                return (self.default_color_file, self.default_color_file)
        filename = path.realpath(myfile)
        filename = path.basename(filename)
        friendly_name = filename.replace("colors_atile_", "").replace("colors_", "")
        friendly_name = friendly_name.replace(".xml", "")
        friendly_name = friendly_name.replace("_", " ")
        return (filename, friendly_name)
		
    def getCurrentFont(self):
        myfile = self.skin_base_dir + self.user_font_file
        if not path.exists(myfile):
            if path.exists(self.skin_base_dir + "allFonts/" + self.default_font_file):
                if path.islink(myfile):
                    remove(myfile)
                chdir(self.skin_base_dir)
                symlink("allFonts/" + self.default_font_file, self.user_font_file)
            else:
                return (self.default_font_file, self.default_font_file)
        filename = path.realpath(myfile)
        filename = path.basename(filename)
        friendly_name = filename.replace("font_atile_", "").replace("font_", "")
        friendly_name = friendly_name.replace(".xml", "")
        friendly_name = friendly_name.replace("_", " ")
        return (filename, friendly_name)

    def setPicture(self, f):
        preview = self.skin_base_dir + "allPreviews/"
        if not path.exists(preview):
            mkdir(preview)
        pic = f[:-4]
        if f.startswith("bar_"):
            pic = f + ".png"
        printDEBUG("[iFlatFHD:setPicture] pic =" + pic + '[jpg|png]')
        previewJPG = preview + "preview_" + picJPG
        if path.exists(preview + "preview_" + pic + '.jpg'):
            self.UpdatePreviewPicture(preview + "preview_" + pic + '.jpg')
        if path.exists(preview + "preview_" + pic + '.png'):
            self.UpdatePreviewPicture(preview + "preview_" + pic + '.png')
        else:
            self["Picture"].hide()

    def setPicture(self, f):
        pic = f[:-4]
        if path.exists(self.skin_base_dir + "allPreviews/preview_" + pic + '.png'):
            self.UpdatePreviewPicture(self.skin_base_dir + "allPreviews/preview_" + pic + '.png')
        elif path.exists(self.skin_base_dir + "allPreviews/preview_" + pic + '.jpg'):
            self.UpdatePreviewPicture(self.skin_base_dir + "allPreviews/preview_" + pic + '.jpg')
        elif path.exists(self.skin_base_dir + "allPreviews/" + pic + '.png'):
            self.UpdatePreviewPicture(self.skin_base_dir + "allPreviews/" + pic + '.png')
        elif path.exists(self.skin_base_dir + "allPreviews/" + pic + '.jpg'):
            self.UpdatePreviewPicture(self.skin_base_dir + "allPreviews/" + pic + '.jpg')
    
    def UpdatePreviewPicture(self, PreviewFileName):
            self["Picture"].instance.setScale(1)
            self["Picture"].instance.setPixmap(LoadPixmap(path=PreviewFileName))
            self["Picture"].show()
            
    def keyYellow(self):
        if self.myiFlatFHD_active.value:
            if not path.exists(self.skin_base_dir + "iFlatFHD_Selections"):
                mkdir(self.skin_base_dir + "iFlatFHD_Selections")
            if not path.exists(self.skin_base_dir + "allPreviews"):
                mkdir(self.skin_base_dir + "allPreviews")
            self.session.openWithCallback(self.iFlatFHDScreesnCB, iFlatFHDScreens)
        else:
            self["config"].setCurrentIndex(0)

    def keyOk(self):
        sel =  self["config"].getCurrent()
        if sel is not None and sel == self.set_new_skin:
            self.openSkinSelector()
        elif sel is not None and sel == self.find_city:
            countriesFile = resolveFilename(SCOPE_PLUGINS, 'Extensions/RaedQuickSignal/countries')
            countries=open(countriesFile).readlines()
            clist=[]
            for country in countries:
                countryCode,countryName=country.split(",")
                clist.append((countryName,countryCode))
            from Screens.ChoiceBox import ChoiceBox
            self.session.openWithCallback(self.choicesback, ChoiceBox, _('select your country'), clist)
        else:
            self.keyGreen()

    def choicesback(self, select):
        if select:
            self.country=select[1]
            config.plugins.iFlatFHD.weather_location.value=self.country.lower()+"-"+self.country.upper()
            config.plugins.iFlatFHD.weather_location.save()
            self.session.openWithCallback(self.citiesback, WeatherLocationChoiceList, self.country)
                    
    def citiesback(self,select):
        if select:
            weather_city = select
            weather_city.capitalize() 
            config.plugins.iFlatFHD.city.setValue(weather_city)
            self.createConfigList()

    def keyGreen(self):
        if self["config"].isChanged() or self.updateEntries == True:
            printDEBUG("[iFlatFHD:keyOk] self.myiFlatFHD_font.value=" + self.myiFlatFHD_font.value)
            printDEBUG("[iFlatFHD:keyOk] self.myiFlatFHD_style.value=" + self.myiFlatFHD_style.value)
            config.plugins.iFlatFHD.refreshInterval.value = config.plugins.iFlatFHD.refreshInterval.value
            config.plugins.iFlatFHD.city.value = config.plugins.iFlatFHD.city.value
            config.plugins.iFlatFHD.degreetype.value = config.plugins.iFlatFHD.degreetype.value
            for x in self["config"].list:
                x[1].save()
            configfile.save()
            #we change current folder to active skin folder
            chdir(self.skin_base_dir)
            #FONTS
            if path.exists(self.user_font_file):
                remove(self.user_font_file)
            elif path.islink(self.user_font_file):
                remove(self.user_font_file)
            if path.exists('allFonts/' + self.myiFlatFHD_font.value):
                symlink('allFonts/' + self.myiFlatFHD_font.value, self.user_font_file)
            #COLORS
            if path.exists(self.color_file):
                remove(self.color_file)
            elif path.islink(self.color_file):
                remove(self.color_file)
            if path.exists("allColors/" + self.myiFlatFHD_style.value):
                symlink("allColors/" + self.myiFlatFHD_style.value, self.color_file)
            #SCREENS
            if self.myiFlatFHD_active.value:
                if not path.exists("mySkin") and path.exists("iFlatFHD_Selections"):
                    try:
                        symlink("iFlatFHD_Selections","mySkin")
                    except:
                        printDEBUG("[iFlatFHD:keyOK]symlinking myskin exception")
                        with open("/proc/sys/vm/drop_caches", "w") as f: f.write("1\n") #avoid GS with system on tuners with small RAM
                        destPath = path.join(self.skin_base_dir , "mySkin")
                        sourcePath = path.join(self.skin_base_dir , "iFlatFHD_Selections")
                        system("rm -rf %s;ln -sf %s %s" % (destPath , sourcePath ,destPath) )
            else:
                if path.exists("mySkin"):
                    if path.exists("iFlatFHD_Selections"):
                        if path.islink("mySkin"):
                            remove("mySkin")
                        else:
                            shutil.rmtree("mySkin")
                    else:
                        rename("mySkin", "iFlatFHD_Selections")
  
            self.update_user_skin()
            self.restartGUI()
        else:
            if self.changed_screens:
                self.update_user_skin()
                self.restartGUI()
            else:
                self.close()

    def openSkinSelector(self):
		self.session.openWithCallback(self.skinChanged, SkinSelector)

    def openSkinSelectorDelayed(self):
		self.delaytimer = eTimer()
		self.delaytimer.callback.append(self.openSkinSelector)
		self.delaytimer.start(200, True)

    def skinChanged(self, ret = None):
		global cur_skin
		cur_skin = config.skin.primary_skin.value.replace('/skin.xml', '')
		if cur_skin == "skin.xml":
			self.restartGUI()
		else:
			self.getInitConfig()
			self.createConfigList()

    def iFlatFHDScreesnCB(self):
        self.changed_screens = True
        self["config"].setCurrentIndex(0)

    def restartGUI(self):
        myMessage = ''
        if self.LackOfFile != '':
            printDEBUG("missing components: %s" % self.LackOfFile)
            myMessage += _("Missing components found: %s\n\n") % self.LackOfFile
            myMessage += _("Skin will NOT work properly!!!\n\n")
        myMessage += _("Restart necessary, restart GUI now?")
        restartbox = self.session.openWithCallback(self.restartGUIcb,MessageBox, myMessage, MessageBox.TYPE_YESNO, default = False)
        restartbox.setTitle(_("Message"))

    def keyBlue(self):
        import xml.etree.cElementTree as ET
        from Screens.VirtualKeyBoard import VirtualKeyBoard
        
        def SaveScreen(ScreenFileName = None):
            if ScreenFileName is not None:
                if not ScreenFileName.endswith('.xml'):
                    ScreenFileName += '.xml'
                if not ScreenFileName.startswith('skin_'):
                    ScreenFileName = 'skin_' + ScreenFileName
                printDEBUG("Writing %s%s/%s" % (SkinPath, 'allScreens',ScreenFileName))
                
                for skinScreen in root.findall('screen'):
                    if 'name' in skinScreen.attrib:
                        if skinScreen.attrib['name'] == self.ScreenSelectedToExport:
                            SkinContent = ET.tostring(skinScreen)
                            break
                with open("%s%s/%s" % (SkinPath, 'allScreens', ScreenFileName), "w") as f:
                    f.write('<skin>\n')
                    f.write(SkinContent)
                    f.write('</skin>\n')

        def ScreenSelected(ret):
            if ret:
                self.ScreenSelectedToExport = ret[0]
                printDEBUG('Selected: %s' % self.ScreenSelectedToExport)
                self.session.openWithCallback(SaveScreen, VirtualKeyBoard, title=(_("Enter filename")), text = self.ScreenSelectedToExport + '_new')
        
        ScreensList= []
        root = ET.parse(SkinPath + 'skin.xml').getroot()
        for skinScreen in root.findall('screen'):
            if 'name' in skinScreen.attrib:
                printDEBUG('Found in skin.xml: %s' % skinScreen.attrib['name'])
                ScreensList.append((skinScreen.attrib['name'],skinScreen.attrib['name']))
        if len(ScreensList) > 0:
            ScreensList.sort()
            self.session.openWithCallback(ScreenSelected, ChoiceBox, title = _("Select skin to export:"), list = ScreensList)
                
    def restartGUIcb(self, answer):
        if answer is True:
            self.session.open(TryQuitMainloop, 3)
        else:
            self.close()

    def update_user_skin(self):
        #print "[iFlatFHD} update_user_skin"
        if self.isVTI == True: #jesli mamy VTI, to nie musimy robic pliku
            return

        user_skin_file=resolveFilename(SCOPE_CONFIG, 'skin_user' + self.currentSkin + '.xml')
        if path.exists(user_skin_file):
            remove(user_skin_file)
        if self.myiFlatFHD_active.value:
            printDEBUG("update_user_skin.self.myiFlatFHD_active.value")
            user_skin = ""
            if path.exists(self.skin_base_dir + 'skin_user_header.xml'):
                user_skin = user_skin + self.readXMLfile(self.skin_base_dir + 'skin_user_header.xml' , 'fonts')
            if path.exists(self.skin_base_dir + 'skin_user_colors.xml'):
                user_skin = user_skin + self.readXMLfile(self.skin_base_dir + 'skin_user_colors.xml' , 'ALLSECTIONS')
            if path.exists(self.skin_base_dir + 'skin_user_window.xml'):
                user_skin = user_skin + self.readXMLfile(self.skin_base_dir + 'skin_user_window.xml' , 'ALLSECTIONS')
            if path.exists(self.skin_base_dir + 'mySkin'):
                for f in listdir(self.skin_base_dir + "mySkin/"):
                    user_skin = user_skin + self.readXMLfile(self.skin_base_dir + "mySkin/" + f, 'screen')
            if user_skin != '':
                user_skin = "<skin>\n" + user_skin
                user_skin = user_skin + "</skin>\n"
                with open (user_skin_file, "w") as myFile:
                    printDEBUG("update_user_skin.self.myiFlatFHD_active.value write myFile")
                    myFile.write(user_skin)
                    myFile.flush()
                    myFile.close()
            #checking if all renderers are in system
            self.checkComponent(user_skin, 'render' , resolveFilename(SCOPE_PLUGINS, '../Components/Renderer/') )
            self.checkComponent(user_skin, 'pixmap' , resolveFilename(SCOPE_SKIN, '') )
               
    def checkComponent(self, myContent, look4Component , myPath): #look4Component=render|
        def updateLackOfFile(name, mySeparator =', '):
            printDEBUG("Missing component found:%s\n" % name)
            if self.LackOfFile == '':
                self.LackOfFile = name
            else:
                self.LackOfFile += mySeparator + name
            
        r=re.findall( r' %s="([a-zA-Z0-9_/\.]+)" ' % look4Component , myContent )
        r=list(set(r)) #remove duplicates, no need to check for the same component several times

        printDEBUG("Found %s:\n" % (look4Component))
        print r
        if r:
            for myComponent in set(r):
                #print" [iFlatFHD] checks if %s exists" % myComponent
                if look4Component == 'pixmap':
                    #printDEBUG("%s\n%s\n" % (myComponent,myPath + myComponent))
                    if myComponent.startswith('/'):
                        if not path.exists(myComponent):
                            updateLackOfFile(myComponent, '\n')
                    else:
                        if not path.exists(myPath + myComponent):
                            updateLackOfFile(myComponent)
                else:
                    if not path.exists(myPath + myComponent + ".pyo") and not path.exists(myPath + myComponent + ".py"):
                        updateLackOfFile(myComponent)
        return
    
    def readXMLfile(self, XMLfilename, XMLsection): #sections:ALLSECTIONS|fonts|
        myPath=path.realpath(XMLfilename)
        if not path.exists(myPath):
            remove(XMLfilename)
            return ''
        filecontent = ''
        if XMLsection == 'ALLSECTIONS':
            sectionmarker = True
        else:
            sectionmarker = False
        with open (XMLfilename, "r") as myFile:
            for line in myFile:
                if line.find('<skin>') >= 0 or line.find('</skin>') >= 0:
                    continue
                if line.find('<%s' %XMLsection) >= 0 and sectionmarker == False:
                    sectionmarker = True
                elif line.find('</%s>' %XMLsection) >= 0 and sectionmarker == True:
                    sectionmarker = False
                    filecontent = filecontent + line
                if sectionmarker == True:
                    filecontent = filecontent + line
            myFile.close()
        return filecontent

    def about(self):
        self.session.open(iFlatFHD_About)

class iFlatFHD_About(Screen):

	def __init__(self, session, args = 0):
		self.session = session
		Screen.__init__(self, session)
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
			{
				"cancel": self.cancel,
				"ok": self.keyOk,
			}, -2)

	def keyOk(self):
		self.close()

	def cancel(self):
		self.close()

class iFlatFHDScreens(Screen):
    skin = """
  <screen name="iFlatFHDScreens" position="center,center" size="1280,720" title="iFlatFHD Setup">
			<widget source="Title" render="Label" position="70,47" size="950,43" font="Regular;35" transparent="1" />
			<widget source="menu" render="Listbox" position="70,115" size="700,480" scrollbarMode="showOnDemand" scrollbarWidth="6" scrollbarSliderBorderWidth="1" enableWrapAround="1" transparent="1">
			<convert type="TemplatedMultiContent">
                                {"template":
                                        [
                                                MultiContentEntryPixmapAlphaTest(pos = (2, 2), size = (54, 54), png = 3),
                                                MultiContentEntryText(pos = (60, 2), size = (500, 22), font=0, flags = RT_HALIGN_LEFT|RT_VALIGN_CENTER, text = 1), # name
                                                MultiContentEntryText(pos = (55, 24),size = (500, 32), font=1, flags = RT_HALIGN_LEFT|RT_VALIGN_CENTER, text = 2), # info
                                        ],
                                        "fonts": [gFont("Regular", 22),gFont("Regular", 16)],
                                        "itemHeight": 60
                                }
                        </convert>
			</widget>
			<widget name="Picture" position="808,342" size="400,225" alphatest="on" />
			<eLabel position=" 55,675" size="290, 5" zPosition="-10" backgroundColor="red" />
			<eLabel position="350,675" size="290, 5" zPosition="-10" backgroundColor="green" />
			<widget source="key_red" render="Label" position="70,635" size="260,25" zPosition="1" font="Regular;20" halign="left" transparent="1" />
			<widget source="key_green" render="Label" position="365,635" size="260,25" zPosition="1" font="Regular;20" halign="left" transparent="1" />
		</screen>
"""
    
    allScreensGroups = [(_("All skins"), "_"),
    (_("ChannelList skins"), "channelselection"),
    (_("Infobar skins"), "infobar"),
    ]

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        
        myTitle=_("iFlatFHD %s - additional screens") %  iFlatFHDInfo
        self.setTitle(myTitle)
        try:
            self["title"]=StaticText(myTitle)
        except:
            pass
        
        self["key_red"] = StaticText(_("Exit"))
        self["key_green"] = StaticText("on")
        
        self["Picture"] = Pixmap()
        
        menu_list = []
        self["menu"] = List(menu_list)
        
        self.allScreensGroup = self.allScreensGroups[0][1]
        
        self["shortcuts"] = ActionMap(["SetupActions", "ColorActions", "DirectionActions"],
        {
            "ok": self.runMenuEntry,
            "cancel": self.keyCancel,
            "red": self.keyCancel,
            "green": self.runMenuEntry,
        }, -2)
        
        self.currentSkin = CurrentSkinName
        self.skin_base_dir = SkinPath
        #self.screen_dir = "allScreens"
        self.allScreens_dir = "allScreens"
        self.file_dir = "iFlatFHD_Selections"
        if path.exists("%siFlatFHDpics/install.png" % SkinPath):
            printDEBUG("SkinConfig is loading %siFlatFHDpics/install.png" % SkinPath)
            self.enabled_pic = LoadPixmap(cached=True, path="%siFlatFHDpics/install.png" % SkinPath)
        else:
            self.enabled_pic = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "Extensions/iFlatFHD/pic/install.png"))
        #check if we have preview files
        isPreview=0
        for xpreview in listdir(self.skin_base_dir + "allPreviews/"):
            if len(xpreview) > 4 and  xpreview[-4:] == ".png":
                isPreview += 1
            if isPreview >= 2:
                break
        if self.currentSkin == "infinityHD-nbox-tux-full" and isPreview < 2:
            printDEBUG("no preview files :(")
            if path.exists("%siFlatFHDpics/install.png" % SkinPath):
                printDEBUG("SkinConfig is loading %siFlatFHDpics/opkg.png" % SkinPath)
                self.disabled_pic = LoadPixmap(cached=True, path="%siFlatFHDpics/opkg.png" % SkinPath)
            else:
                self.disabled_pic = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "Extensions/iFlatFHD/pic/opkg.png"))
            self['key_blue'].setText(_('Install from OPKG'))
        else:
            if path.exists("%siFlatFHDpics/install.png" % SkinPath):
                printDEBUG("SkinConfig is loading %siFlatFHDpics/remove.png" % SkinPath)
                self.disabled_pic = LoadPixmap(cached=True, path="%siFlatFHDpics/remove.png" % SkinPath)
            else:
                self.disabled_pic = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "Extensions/iFlatFHD/pic/remove.png"))
        
        if not self.selectionChanged in self["menu"].onSelectionChanged:
            self["menu"].onSelectionChanged.append(self.selectionChanged)
        
        self.onLayoutFinish.append(self.createMenuList)
     
    def selectionChanged(self):
        sel = self["menu"].getCurrent()
        if sel is not None:
            self.setPicture(sel[0])
            if sel[3] == self.enabled_pic:
                    self["key_green"].setText(_("off"))
            elif sel[3] == self.disabled_pic:
                    self["key_green"].setText(_("on"))

    def createMenuList(self):
        chdir(self.skin_base_dir)
        f_list = []
        if path.exists(self.skin_base_dir + self.allScreens_dir):
            list_dir = sorted(listdir(self.skin_base_dir + self.allScreens_dir), key=str.lower)
            for f in list_dir:
                if f.endswith('.xml') and f.startswith('skin_') and f.lower().find(self.allScreensGroup) > 0:
                    friendly_name = f.replace("skin_", "")
                    friendly_name = friendly_name.replace(".xml", "")
                    friendly_name = friendly_name.replace("_", " ")
                    linked_file = self.skin_base_dir + self.file_dir + "/" + f
                    if path.exists(linked_file):
                        if path.islink(linked_file):
                            pic = self.enabled_pic
                        else:
                            remove(linked_file)
                            symlink(self.skin_base_dir + self.allScreens_dir + "/" + f, self.skin_base_dir + self.file_dir + "/" + f)
                            pic = self.enabled_pic
                    else:
                        pic = self.disabled_pic
                    f_list.append((f, friendly_name, self.getInfo(f) , pic))
        menu_list = []
        if len(f_list) == 0:
            f_list.append(("dummy", _("No User skins found"), '', self.disabled_pic))
        for entry in f_list:
            menu_list.append((entry[0], entry[1], entry[2], entry[3]))
        #print menu_list
        try:
          self["menu"].UpdateList(menu_list)
        except:
          print "Update asser error :(" #workarround to have it working on openpliPC
          myIndex=self["menu"].getIndex() #as an effect, index is cleared so we need to store it first
          self["menu"].setList(menu_list)
          self["menu"].setIndex(myIndex) #and restore
        self.selectionChanged()
        
    def getInfo(self, f):#currLang
        info = f.replace(".xml", ".txt")
        if path.exists(self.skin_base_dir + "allInfos/info_" + currLang + "_" + info):
            myInfoFile=self.skin_base_dir + "allInfos/info_" + currLang + "_" + info
        elif path.exists(self.skin_base_dir + "allInfos/info_en_" + info):
            myInfoFile=self.skin_base_dir + "allInfos/info_en_" + info
        else:
            #return 'No Info'
            return ''
        
        #with open("/proc/sys/vm/drop_caches", "w") as f: f.write("1\n")
        info = open(myInfoFile, 'r').read().strip()
        return info
            
    def setPicture(self, f):
        pic = f[:-4]
        if path.exists(self.skin_base_dir + "allPreviews/preview_" + pic + '.png'):
            self.UpdatePreviewPicture(self.skin_base_dir + "allPreviews/preview_" + pic + '.png')
        elif path.exists(self.skin_base_dir + "allPreviews/preview_" + pic + '.jpg'):
            self.UpdatePreviewPicture(self.skin_base_dir + "allPreviews/preview_" + pic + '.jpg')
        elif path.exists(self.skin_base_dir + "allPreviews/" + pic + '.png'):
            self.UpdatePreviewPicture(self.skin_base_dir + "allPreviews/" + pic + '.png')
        elif path.exists(self.skin_base_dir + "allPreviews/" + pic + '.jpg'):
            self.UpdatePreviewPicture(self.skin_base_dir + "allPreviews/" + pic + '.jpg')
        else:
            self["Picture"].hide()
    
    def UpdatePreviewPicture(self, PreviewFileName):
            self["Picture"].instance.setScale(1)
            self["Picture"].instance.setPixmap(LoadPixmap(path=PreviewFileName))
            self["Picture"].show()

    def keyCancel(self):
        self.close()

    def runMenuEntry(self):
        sel = self["menu"].getCurrent()
        if sel[3] == self.enabled_pic:
            remove(self.skin_base_dir + self.file_dir + "/" + sel[0])
        elif sel[3] == self.disabled_pic:
            symlink(self.skin_base_dir + self.allScreens_dir + "/" + sel[0], self.skin_base_dir + self.file_dir + "/" + sel[0])
        self.createMenuList()

class iFlatFHD_About(Screen):
    skin = """
  <screen name="iFlatFHD_About" position="center,center" size="700,250" title="iFlatFHD info">
    <eLabel text="by j00zek" position="0,15" size="698,50" font="Regular;28" halign="center"/>
    <eLabel text="Modified by RAED for Open Vision" position="5,69" size="686,57" font="Regular;18" halign="center"/>
    <eLabel text="https://openvision.tech" position="5,129" size="672,50" font="Regular;24" halign="center"/>
    <widget name="skininfo" position="5,182" size="667,50" font="Regular;20" halign="center"/>
  </screen>
"""

    def __init__(self, session, args = 0):
        self.session = session
        Screen.__init__(self, session)
        self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
            {
                "cancel": self.cancel,
                "ok": self.keyOk,
            }, -2)
        self.setTitle(_("iFlatFHD %s") % iFlatFHDInfo)
        self['skininfo'] = Label("")
        if path.exists(SkinPath + 'skin.config'):
            with open(SkinPath + 'skin.config', "r") as f:
                for line in f:
                    if line.startswith('description='):
                        self['skininfo'].text = line.split('=')[1].replace('"','').replace("'","").strip()
                        break
                f.close()

    def keyOk(self):
        self.close()

    def cancel(self):
        self.close()
