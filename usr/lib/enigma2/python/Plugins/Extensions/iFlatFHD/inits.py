# -*- coding: utf-8 -*-
iFlatFHDInfo='@j00zek Mod By RAED'

#stale
PluginName = 'iFlatFHD'
PluginGroup = 'Extensions'

#Plugin Paths
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN, SCOPE_PLUGINS
PluginFolder = PluginName
PluginPath = resolveFilename(SCOPE_PLUGINS, '%s/%s/' %(PluginGroup,PluginFolder))

#Current skin
from Components.config import *
SkinPath = resolveFilename(SCOPE_CURRENT_SKIN, '')
if not SkinPath.endswith('/'):
    SkinPath = SkinPath + '/'
CurrentSkinName=config.skin.primary_skin.value.replace('skin.xml', '').replace('/', '')

#translation
PluginLanguageDomain = "plugin-" + PluginName
PluginLanguagePath = resolveFilename(SCOPE_PLUGINS, '%s/%s/locale' % (PluginGroup,PluginFolder))

#DEBUG
myDEBUG=True
myDEBUGfile = '/tmp/%s.log' % PluginName
