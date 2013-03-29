# -*- coding: utf-8 -*- 

import os
import re
import sys
import xbmc
import xbmcvfs
import xbmcgui
import shutil
import struct
import unicodedata

try: import simplejson as json
except: import json

try: from hashlib import md5
except: from md5 import new as md5

_              = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__cwd__        = sys.modules[ "__main__" ].__cwd__

STATUS_LABEL   = 100
LOADING_IMAGE  = 110
SUBTITLES_LIST = 120
SERVICES_LIST  = 150
CANCEL_DIALOG  = ( 9, 10, 13, 92, 216, 247, 257, 275, 61467, 61448, )

SERVICE_DIR    = os.path.join(__cwd__, "resources", "lib", "services")

LANGUAGES      = (
    
    # Full Language name[0]     podnapisi[1]  ISO 639-1[2]   ISO 639-1 Code[3]   Script Setting Language[4]   localized name id number[5]
    
    ("English"                    , "2",        "en",            "eng",                 "0",                     30212  ),
    ("Hebrew"                     , "22",       "he",            "heb",                 "1",                     30218  ),
    ("French"                     , "8",        "fr",            "fre",                 "2",                     30215  ),
    ("Russian"                    , "27",       "ru",            "rus",                 "3",                     30236  ),)


REGEX_EXPRESSIONS = [ '[Ss]([0-9]+)[][._-]*[Ee]([0-9]+)([^\\\\/]*)$',
                      '[\._ \-]([0-9]+)x([0-9]+)([^\\/]*)',                     # foo.1x09 
                      '[\._ \-]([0-9]+)([0-9][0-9])([\._ \-][^\\/]*)',          # foo.109
                      '([0-9]+)([0-9][0-9])([\._ \-][^\\/]*)',
                      '[\\\\/\\._ -]([0-9]+)([0-9][0-9])[^\\/]*',
                      'Season ([0-9]+) - Episode ([0-9]+)[^\\/]*',
                      '[\\\\/\\._ -][0]*([0-9]+)x[0]*([0-9]+)[^\\/]*',
                      '[[Ss]([0-9]+)\]_\[[Ee]([0-9]+)([^\\/]*)',                 #foo_[s01]_[e01]
                      '[\._ \-][Ss]([0-9]+)[\.\-]?[Ee]([0-9]+)([^\\/]*)',        #foo, s01e01, foo.s01.e01, foo.s01-e01
                      's([0-9]+)ep([0-9]+)[^\\/]*',                              #foo - s01ep03, foo - s1ep03
                      '[Ss]([0-9]+)[][ ._-]*[Ee]([0-9]+)([^\\\\/]*)$',
                      '[\\\\/\\._ \\[\\(-]([0-9]+)x([0-9]+)([^\\\\/]*)$'
                     ]

class Pause:
  def __init__(self):
    self.player_state = xbmc.getCondVisibility('Player.Paused')

  def restore(self):
    if self.player_state != xbmc.getCondVisibility('Player.Paused'):
      xbmc.Player().pause()
      
  def pause(self):
    if not xbmc.getCondVisibility('Player.Paused'):
      xbmc.Player().pause()
   
def log(module,msg):
  xbmc.log((u"### [%s-%s] - %s" % (__scriptname__,module,msg,)).encode('utf-8'),level=xbmc.LOGDEBUG ) 

def regex_tvshow(compare, file, sub = ""):
  sub_info = ""
  tvshow = 0
  
  for regex in REGEX_EXPRESSIONS:
    response_file = re.findall(regex, file)                  
    if len(response_file) > 0 : 
      log( __name__ , "Regex File Se: %s, Ep: %s," % (str(response_file[0][0]),str(response_file[0][1]),) )
      tvshow = 1
      if not compare :
        title = re.split(regex, file)[0]
        for char in ['[', ']', '_', '(', ')','.','-']: 
           title = title.replace(char, ' ')
        if title.endswith(" "): title = title[:-1]
        return title,response_file[0][0], response_file[0][1]
      else:
        break
  
  if (tvshow == 1):
    for regex in regex_expressions:       
      response_sub = re.findall(regex, sub)
      if len(response_sub) > 0 :
        try :
          sub_info = "Regex Subtitle Ep: %s," % (str(response_sub[0][1]),)
          if (int(response_sub[0][1]) == int(response_file[0][1])):
            return True
        except: pass      
    return False
  if compare :
    return True
  else:
    return "","",""    

def languageTranslate(lang, lang_from, lang_to):
  for x in LANGUAGES:
    if lang == x[lang_from] :
      return x[lang_to]

def pause():
  if not xbmc.getCondVisibility('Player.Paused'):
    xbmc.Player().pause()
    return True
  else:
    return False  
    
def unpause():
  if xbmc.getCondVisibility('Player.Paused'):
    xbmc.Player().pause()  

def rem_files(directory):
  try:
    if xbmcvfs.exists(directory):
      shutil.rmtree(directory)
  except:
    pass
    
  if not xbmcvfs.exists(directory):
    os.makedirs(directory)
      
def copy_files( subtitle_file, file_path ):
  subtitle_set = False
  try:
    log( __name__ ,"vfs module copy %s -> %s" % (subtitle_file, file_path))
    xbmcvfs.copy(subtitle_file, file_path)
    subtitle_set = True
  except :
    dialog = xbmcgui.Dialog()
    selected = dialog.yesno( __scriptname__ , _( 748 ), _( 750 ),"" )
    if selected == 1:
      file_path = subtitle_file
      subtitle_set = True

  return subtitle_set, file_path

def normalizeString(str):
  return unicodedata.normalize(
         'NFKD', unicode(unicode(str, 'utf-8'))
         ).encode('ascii','ignore')

def hashFile(file_path, rar):
    if rar:
      return OpensubtitlesHashRar(file_path)
      
    log( __name__,"Hash Standard file")  
    longlongformat = 'q'  # long long
    bytesize = struct.calcsize(longlongformat)
    f = xbmcvfs.File(file_path)
    
    filesize = f.size()
    hash = filesize
    
    if filesize < 65536 * 2:
        return "SizeError"
    
    buffer = f.read(65536)
    f.seek(max(0,filesize-65536),0)
    buffer += f.read(65536)
    f.close()
    for x in range((65536/bytesize)*2):
        size = x*bytesize
        (l_value,)= struct.unpack(longlongformat, buffer[size:size+bytesize])
        hash += l_value
        hash = hash & 0xFFFFFFFFFFFFFFFF
    
    returnHash = "%016x" % hash
    return filesize,returnHash


def OpensubtitlesHashRar(firsrarfile):
    log( __name__,"Hash Rar file")
    f = xbmcvfs.File(firsrarfile)
    a=f.read(4)
    if a!='Rar!':
        raise Exception('ERROR: This is not rar file.')
    seek=0
    for i in range(4):
        f.seek(max(0,seek),0)
        a=f.read(100)        
        type,flag,size=struct.unpack( '<BHH', a[2:2+5]) 
        if 0x74==type:
            if 0x30!=struct.unpack( '<B', a[25:25+1])[0]:
                raise Exception('Bad compression method! Work only for "store".')            
            s_partiizebodystart=seek+size
            s_partiizebody,s_unpacksize=struct.unpack( '<II', a[7:7+2*4])
            if (flag & 0x0100):
                s_unpacksize=(unpack( '<I', a[36:36+4])[0] <<32 )+s_unpacksize
                log( __name__ , 'Hash untested for files biger that 2gb. May work or may generate bad hash.')
            lastrarfile=getlastsplit(firsrarfile,(s_unpacksize-1)/s_partiizebody)
            hash=addfilehash(firsrarfile,s_unpacksize,s_partiizebodystart)
            hash=addfilehash(lastrarfile,hash,(s_unpacksize%s_partiizebody)+s_partiizebodystart-65536)
            f.close()
            return (s_unpacksize,"%016x" % hash )
        seek+=size
    raise Exception('ERROR: Not Body part in rar file.')

def getlastsplit(firsrarfile,x):
    if firsrarfile[-3:]=='001':
        return firsrarfile[:-3]+('%03d' %(x+1))
    if firsrarfile[-11:-6]=='.part':
        return firsrarfile[0:-6]+('%02d' % (x+1))+firsrarfile[-4:]
    if firsrarfile[-10:-5]=='.part':
        return firsrarfile[0:-5]+('%1d' % (x+1))+firsrarfile[-4:]
    return firsrarfile[0:-2]+('%02d' %(x-1) )

def addfilehash(name,hash,seek):
    f = xbmcvfs.File(name)
    f.seek(max(0,seek),0)
    for i in range(8192):
        hash+=struct.unpack('<q', f.read(8))[0]
        hash =hash & 0xffffffffffffffff
    f.close()    
    return hash

def hashFileMD5(file_path, buff_size=1048576):
    # calculate MD5 key from file
    f = xbmcvfs.File(file_path)
    if f.size() < buff_size:
        return None
    f.seek(0,0)
    buff = f.read(buff_size)    # size=1M
    f.close()
    # calculate MD5 key from file
    m = md5();
    m.update(buff);
    return m.hexdigest()

def getShowId():
    try:
      playerid_query = '{"jsonrpc": "2.0", "method": "Player.GetActivePlayers", "id": 1}'
      playerid = json.loads(xbmc.executeJSONRPC(playerid_query))['result'][0]['playerid']
      tvshowid_query = '{"jsonrpc": "2.0", "method": "Player.GetItem", "params": {"playerid": ' + str(playerid) + ', "properties": ["tvshowid"]}, "id": 1}'
      tvshowid = json.loads(xbmc.executeJSONRPC (tvshowid_query))['result']['item']['tvshowid']
      tvdbid_query = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShowDetails", "params": {"tvshowid": ' + str(tvshowid) + ', "properties": ["imdbnumber"]}, "id": 1}'
      return json.loads(xbmc.executeJSONRPC (tvdbid_query))['result']['tvshowdetails']['imdbnumber']
    except:
      log( __name__ ," Failed to find TVDBid in database")  
    


