import sys
import xbmc
import xbmcgui
import xbmcplugin
import urllib
import json
import os
import time
import urlparse

LOG_ENABLED = False
handle = int(sys.argv[1])
FILE_EXTENSIONS = []

# plugin modes
MODE_SCAN_SOURCE = 10
MODE_SHOW_SOURCES = 20

# parameter keys
PARAMETER_KEY_MODE = "mode"
PARAMETER_KEY_SOURCE = "source"

# dir walker counters
dirCount = 0
fileCount = 0
filesFound = 0

#############################################################################################
# Functions
#############################################################################################

def log(line):
    if LOG_ENABLED:
        print "MMS : " + line#repr(line)

        
def clean_smb_path(uri):
    log("Cleaning SMB Path : " + uri)
    bits=urlparse.urlparse(uri)
    newSmbPath="smb://" + bits.hostname + bits.path
    log("Cleaned SMB Path : " + newSmbPath)
    return newSmbPath
    
def clean_name(text):
    text = text.replace('%21', '!')
    text = text.replace('%3a', ':')
    text = text.replace('%5c', '\\')
    text = text.replace('%2f', '/')
    text = text.replace('%2c', ',')
    text = text.replace('%20', ' ')

    if text.startswith("smb:"):
        text = clean_smb_path(text)
    
    return text
    
def get_movie_sources():    
    log("get_movie_sources() called")
    
    jsonResult = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Files.GetSources", "params": {"media": "video"}, "id": 1}')
    log("VideoLibrary.GetSources results:\n" + jsonResult)
    shares = eval(jsonResult)#json.loads(jsonResult)
    shares = shares['result']['sources']
    
    results = []
    for s in shares:
        log("FOUND SHARE: " + s['label'] + " - " + s['file'])
        
        share = {}
        share['path'] = s['file']
        share['name'] = s['label']
        results.append(share)
        
    return results

def get_extensions(ext_string):
    log("Extension String : " + ext_string)
    bits = ext_string.split(",")
    extensions = []
    for bit in bits:
        extensions.append(bit.strip())
        log("Adding Extension : " + bit.strip())
    
    return extensions

def file_has_extensions(filename, extensions):
    name, extension = os.path.splitext(os.path.basename(filename))
    name = name.lower()
    extension = extension[1:].lower()
    extensions = [ f.lower() for f in extensions ]

    if extension == 'ifo' and name != 'video_ts':
        return False

    return extension in extensions

def walk_Path(path, walked_files, progress):
    log("walk_Path(" + path + ")")
    
    global dirCount
    global fileCount
    global filesFound
    
    count_text = "Scanned : " + str(dirCount) + " Directories " + str(fileCount) + "  Files"
    found_text = "Files Found : " + str(filesFound)
    hacked_path = "Path: " + path
    progress.update(40, count_text, found_text, hacked_path)
    #time.sleep(5)
    
    # double slash the \ in the path
    path = path.replace("\\", "\\\\")
    rpcCall = "{\"jsonrpc\": \"2.0\", \"method\": \"Files.GetDirectory\", \"params\": {\"directory\": \"" + path + "\"}, \"id\": 1}"
    log("rpcCall: " + rpcCall)
    jsonResult = xbmc.executeJSONRPC(rpcCall)
    log("Files.GetDirectory results: " + jsonResult)
    
    # json.loads expects utf-8 but the conversion using unicode breaks stuff
    #jsonResult = unicode(jsonResult, 'utf-8', errors='ignore')
    #set_files = json.loads(jsonResult)
    
    set_files = []

    try:
        set_files = eval(jsonResult)
    except:
        log("Error Parsing GetDirectory() results : " + str(sys.exc_info()[0]))
        set_files = []
        
    if(len(set_files) == 0):
        return
    
    if(set_files.get('error') != None):
        xbmcgui.Dialog().ok("Source Path Error", "Error walking the source path.")
        return
    
    files = set_files['result']['files']
    
    if(files == None):
        return
    
    dirCount += 1
    
    for file in files:
        if file['filetype'] == "directory":
            walk_Path(file["file"], walked_files, progress)
        elif file['filetype'] == "file":
            fileCount += 1
            if file_has_extensions(file["file"], FILE_EXTENSIONS):
                filesFound += 1
                log("WALKER ADDING FILE : " + file["file"])
                walked_files.append(clean_name(file["file"]))

def get_files(path, progress):
    log("get_files(path) called")
    
    walked_files = []
    walk_Path(path, walked_files, progress)
    
    for file in walked_files:
        log("WALKED FILE : " + file)
        
    return walked_files

#############################################################################################
# Utility Functions
#############################################################################################

def parameters_string_to_dict(parameters):
    paramDict = {}
    if parameters:
        paramPairs = parameters[1:].split("&")
        for paramsPair in paramPairs:
            paramSplits = paramsPair.split('=')
            if (len(paramSplits)) == 2:
                log("Param " + paramSplits[0] + "=" + paramSplits[1])
                paramDict[paramSplits[0]] = paramSplits[1]
    return paramDict

def addDirectoryItem(name, isFolder=True, parameters={}, totalItems=1):
    li = xbmcgui.ListItem(name)
    
    commands = []
    #commands.append(( 'runme', 'XBMC.RunPlugin(plugin://video/myplugin)', ))
    #commands.append(( 'runother', 'XBMC.RunPlugin(plugin://video/otherplugin)', ))
    #commands.append(( "Scan", "ActivateWindow(videofiles, Movies)", ))#, '" + name + "')", ))
    li.addContextMenuItems(commands, replaceItems = True)
    
    url = sys.argv[0] + '?' + urllib.urlencode(parameters)

    if not isFolder:
        url = name
        
    log("Adding Directory Item: " + name + " totalItems:" + str(totalItems))
    
    return xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=li, isFolder=isFolder, totalItems=totalItems)

#############################################################################################
# UI Functions
#############################################################################################

def show_root_menu():
    addDirectoryItem(name="Show Source Paths", parameters={ PARAMETER_KEY_MODE: MODE_SHOW_SOURCES }, isFolder=True)
    xbmcplugin.endOfDirectory(handle=handle, succeeded=True)
    
def scan_movie_source(source_path):
    log("scan_movie_source(source_path) : " + source_path)
    
    xbmc.executebuiltin( "Dialog.Close(busydialog)" )
    
    progress = xbmcgui.DialogProgress()
    progress.create("Scan Running", "Scan Started")
    progress.update(10, "Getting Library Movies")
        
    jsonResult = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"properties": ["file"]}, "id": 1}')
    log("VideoLibrary.GetEpisodes results: " + jsonResult)
    result = eval(jsonResult)#json.loads(jsonResult)
    movies = result['result']
    
    movies = movies.get('episodes')
    
    if(movies == None):
        #xbmcgui.Dialog().ok("No Movies Fount", "There are no movies in your library")
        movies = []    

    library_files = []
    missing = []

    # add files from trailers and sets
    for m in movies:
        f = m['file']

        if f.startswith("videodb://"):
            rpcCall = "{\"jsonrpc\": \"2.0\", \"method\": \"Files.GetDirectory\", \"params\": {\"directory\": \"" + f + "\"}, \"id\": 1}"
            rpc_result = xbmc.executeJSONRPC(rpcCall)
            set_files = eval(rpc_result)#json.loads(rpc_result)

            sub_files = []
            sub_trailers =  []

            for item in set_files['result']['files']:
                sub_files.append(clean_name(item['file']))
                #try:
                    #trailer = item['trailer']
                    #if not trailer.startswith('http://'):
                        #library_files.append(clean_name(trailer))
                #except KeyError:
                    #pass

            library_files.extend(sub_files)
            #library_files.extend(sub_trailers)
        elif f.startswith('stack://'):
            f = f.replace('stack://', '')
            parts = f.split(' , ')

            parts = [ clean_name(f) for f in parts ]

            for b in parts:
                library_files.append(b)
        else:
            library_files.append(clean_name(f))
            #try:
                #trailer = m['trailer']
                #if not trailer.startswith('http://'):
                    #library_files.append(clean_name(trailer))
            #except KeyError:
                #pass

    library_files = set(library_files)

    progress.update(20, "Walking Source Path")
    movie_files = set(get_files(source_path, progress))
    progress.close()
    missing_count = 0
    
    if not library_files.issuperset(movie_files):
        log("Adding missing library items to list for souce path: " + source_path)
        missing.extend(list(movie_files.difference(library_files)))

        for movie_file in missing:
            # get the end of the filename without the extension
            if os.path.splitext(movie_file.lower())[0].endswith("trailer"):
                log(movie_file + " is a trailer and will be ignored!") 
            else:
                log("Adding missing item: " + movie_file)
                missing_count += 1
                addDirectoryItem(movie_file, isFolder=False, totalItems=len(missing))

    else:
        addDirectoryItem("No Missing Movies", isFolder=False, totalItems=1)
                
    xbmcplugin.endOfDirectory(handle=handle, succeeded=True)
    
    global dirCount
    global fileCount
    global filesFound
    count_text = "Scanned : " + str(dirCount) + " Directories " + str(fileCount) + "  Files"
    xbmcgui.Dialog().ok("Missing Scan Results", count_text, "Files Found : " + str(filesFound), "Missing From Library : " + str(missing_count))
    
def show_source_list():
    source_paths = get_movie_sources()
    
    for source_path in source_paths:
        source_test = source_path['name'] + " (" + source_path['path'] + ")"
        addDirectoryItem(clean_name(source_test), parameters={ PARAMETER_KEY_MODE: MODE_SCAN_SOURCE, PARAMETER_KEY_SOURCE: source_path['path'] }, isFolder=True, totalItems=len(source_paths))
        
    xbmcplugin.endOfDirectory(handle=handle, succeeded=True)

# set up all the variables
params = parameters_string_to_dict(sys.argv[2])
mode = int(urllib.unquote_plus(params.get(PARAMETER_KEY_MODE, "0")))
source = urllib.unquote_plus(params.get(PARAMETER_KEY_SOURCE, ""))
LOG_ENABLED = xbmcplugin.getSetting(handle, "custom_log_enabled") == "true"
log("Logging : " + str(LOG_ENABLED))
FILE_EXTENSIONS = get_extensions(xbmcplugin.getSetting(handle, "custom_file_extensions"))

# Depending on the mode do stuff
if not sys.argv[2]:
    ok = show_root_menu()
elif mode == MODE_SCAN_SOURCE:
    ok = scan_movie_source(source)
elif mode == MODE_SHOW_SOURCES:
    ok = show_source_list()
