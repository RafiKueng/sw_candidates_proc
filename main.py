# -*- coding: utf-8 -*-
"""
Created on Mon Jan 19 17:33:36 2015

@author: rafik
"""

import sys
import re
import csv
import requests as rq
from StringIO import StringIO
from PIL import Image
import json as JSON

from os.path import join, isfile, isdir, islink, split, splitext
from os import symlink, makedirs
from glob import glob


#
# the setup
###############################################################################

outdir = 'output'
imgdirname = 'full_imgs'
imgdir = join(outdir, imgdirname)
thumbdirname = 'thumb_imgs'
thumbdir = join(outdir, thumbdirname)
allresultscsv = join(outdir, 'all_results.csv')
claudecsv = 'sw_interesting _objects.csv'


lensdatadirname = 'lensdata'
lensdatadir = join(outdir, lensdatadirname)
#lensdatacsv = join('lensdata.csv')


#
# the datastructure
###############################################################################

class D(object):
    def __init__(self):
        dictSLresults()
        
    #
    # those lists contain all the stuff from spaghettilens
    #
    lensName_2_lensID = {}
    lensID_2_lensName = {}
    modelID_2_lensID = {}
    modelID_2_lensName = {}
    lensID_2_modelIDs = {}
    
    models = {}     # models[23]['datasource'] all the data from SL!
    lenses = {}
    
    getModels = {}  # ASWname -> models (same as lensID2modelIDs, but with name instead of id)
    getParent = {}  # for each model get it's parent or none
    
    resultTree = {} # models only, tree ordered by relation ship

    #
    # this list contain only data for the candidates cld has selected
    #
    candidatesNames = []  # list of candidates names
    
    cldList = {}     # ASWname -> list of available models
    cldTree = {}     # ASWname -> model-tree
    cldNoModels = [] # a list of ASw names that have no models
    cldFlatList = [] # a list of all results that cover cld's candidates

#
# Init Funcs (only run once on new machine)
###############################################################################

def fetchSLresults():
    '''I abuse the ResultDataTable functinality from SL
    to get all the results, and then filter it, because I'm too lazy
    and aa bit worried to fiddle with sql on the server database...
    
    write the fetched to a csv file
    '''

    print "\nFETCH SL RESULTS:\n"
    
    slurl = 'http://mite.physik.uzh.ch/tools/ResultDataTable'
    startid = 115 # because the former are rubbish   
    maxid = 15000 #15000 #currently: 13220
    
    step = 100 # get somany at a time
    
    first = True
    
    if not isdir(outdir):
        makedirs(outdir)

    with open(allresultscsv, 'wb') as f:
        writer = csv.writer(f)
    
        for i in range(startid, maxid, step):
    
            print 'working on: %05i - %05i' % (i, i+step-1),
            sys.stdout.flush()
        
            data = '?'+'&'.join([
                "%s-%s" % (i, i+step),
                'type=csv',
                'only_final=true',
                'json_str=false'
            ])
            rsp = rq.get(slurl+data)
            #return rsp
            if rsp.status_code != 200:
                print 'skipping'
                continue
            print 'got it!',
            sys.stdout.flush()
    
            rows = []    
            filelike = StringIO(rsp.text)
            csvr = csv.reader(filelike)
            header = csvr.next() # get rid of header

            if first:
                writer.writerow(header)
                first = False

            for row in csvr:
                #print row
                rows.append(row)

            writer.writerows(rows)
            print 'wrote it!'
            
    return


#
# HELPER FUNC
###############################################################################

def getRoot(modelid, path):
    ''' gets the root model and the path to there for each model'''

    path.append(modelid)
    if D.getParent.has_key(modelid) and D.getParent[modelid]:
        root, path = getRoot(D.getParent[modelid], path)
        return root, path
    else:
        return modelid, path

def populateTree(path, loc):
#        print path, '--', loc, '--',
    if len(path)==0:
        return
    e = path.pop()
#        print e
    if loc.has_key(e) and loc[e]:
        populateTree(path, loc[e])
    else:
        loc[e] = {}
        populateTree(path, loc[e])


#
# create the datastructures
###############################################################################

def readClaudesList():
    ''' run after dictSLresults'''

    print "\nPARSE CLAUDES LIST:\n"
    
    lenses = []

    with open(claudecsv, 'rb') as csvfile:
        csvr = csv.reader(csvfile)
        for row in csvr:
            if row[0].startswith("ASW"):
                lenses.append(row[0])

    D.candidatesNames = lenses
    
    for lensname in D.candidatesNames:
        print lensname
        if not lensname in D.lenses.keys():
            
            data = {
                'action':'datasourceApi',
                'src_id':3,
                'do':'createObj',
                'data[]': lensname
                }
            resp = rq.post('http://mite.physik.uzh.ch/api', data=data)
            try:
                json = resp.json()
            except:
                print 'error'
                continue
            #print json, resp.text, resp.status_code
            lensid = json[0]
            D.lenses[lensname] = {'id': lensid}

            D.lensName_2_lensID[lensname] = lensid
            D.lensID_2_lensName[lensid] = lensname

            if not D.lensID_2_modelIDs.has_key(lensid):
                D.lensID_2_modelIDs[lensid] = []


def dictSLresults():
    ''' keep in mind that the field names are somewhat mixed up
    in old spaghettilens: model and result
    corresponds in proper tern: lens (model), model (result)

    idea behind the mess: None; reason:
    lens to be modeled, and a modelling result
    '''
    
    print "\nPARSE SL LIST:\n"

    with open(allresultscsv, 'rb') as csvfile:
        csvr = csv.reader(csvfile)
        header = csvr.next()
        
        csvdr = csv.DictReader(csvfile, fieldnames=header)
        for row in csvdr:
            # mapping to propper names...
            lensname = row['model_name']
            lensid = int(row['model_id'])
            modelid = int(row['result_id'])
            
            
            D.lensName_2_lensID[lensname] = lensid
            D.lensID_2_lensName[lensid] = lensname
            D.modelID_2_lensID[modelid] = lensid
            D.modelID_2_lensName[modelid] = lensname
            
            if D.lensID_2_modelIDs.has_key(lensid):
                D.lensID_2_modelIDs[lensid].append(modelid)
            else:
                D.lensID_2_modelIDs[lensid] = [modelid]
            D.models[modelid] = row
            
            if len(row['parent']) > 0:
                D.getParent[modelid] = int(row['parent'])
            else:
                D.getParent[modelid] = None
                
            D.lenses[lensname] = {'id': lensid}
                
    

#
# AND FINALLY DATA PROCESSING
###############################################################################

def processLists():
    # get data ready
#    readClaudesList()
#    dictSLresults()

    print "\nCREATE DICTS:\n"

    for key, val in D.lensID_2_modelIDs.items():
        D.getModels[D.lensID_2_lensName[key]] = val

    for modelid in D.modelID_2_lensID.keys():
        root, path = getRoot(modelid,[])
        #print root, path
        populateTree(path, D.resultTree)

    
    for name in D.candidatesNames:
        try:
            idd = D.lensName_2_lensID[name]
        except KeyError:
            #print "no key for",name
            D.cldList[name] = None
            D.cldTree[name] = None
            D.cldNoModels.append(name)
            continue

        mids = D.lensID_2_modelIDs[idd]
        rtree = {}

        for mid in mids:
            if mid in D.resultTree.keys():
                rtree[mid] = D.resultTree[mid]
            if not mid in D.cldFlatList:
                D.cldFlatList.append(mid)
        
        D.cldList[name] = mids
        D.cldTree[name] = rtree
    D.cldFlatList.sort()

#
# AND HERE COMES THE GFX STUFF
###############################################################################

def getModelImgs():

    print "\nGET MODEL IMAGES FROM SL:\n"
    
    if not isdir(imgdir):
        makedirs(imgdir)
    
    # get all the results
    for mid in D.cldFlatList:
        for img in ['input.png', 'img3_ipol.png', 'img3.png', 'img1.png', 'img2.png']:
            print 'getting', mid, img,
            sys.stdout.flush()
            url = 'http://mite.physik.uzh.ch/result/' + '%06i/' % mid + img
            path = join(imgdir, "%06i_%s" % (mid, img))

            if isfile(path):
                print 'SKIPPING (already present)'
                continue

            r = rq.get(url, stream=True)
            
            if r.status_code >= 300: # reuqests takes care of redirects!
                print 'ERROR:', r.status_code
                continue

            if 'content-type' in r.headers and 'json' in r.headers['content-type']:
                print 'ERROR: no valid png file (json)' 
                continue

            with open(path, 'w') as f:
                for chunk in r.iter_content(1024*4):
                    f.write(chunk)
            print 'done'

#            r = rq.get(url)
#            if r.status_code == 200:
#                i = Image.open(StringIO(r.content))
#                i.save(path)
#                del i
#                print 'done'
#            else:
#                print 'ERROR'


def getLensJSONData():

    print "\nGET LENS DATA FROM SW:\n"

    ln = len(D.lenses.keys())
    
    if not isdir(lensdatadir):
        makedirs(lensdatadir)
    
    for i, lensname in enumerate(D.lenses.keys()):
        fn = join(lensdatadir, "%s.json"%lensname)
        print "getting data for lens", lensname, '(%3i / %3i)' % (i, ln),

        if isfile(fn):
            print 'file present!'
#            with open(fn) as jsonf:
#                json = JSON.loads(jsonf.read())
        else:
            print "getting online",
            try:
                resp = rq.get("https://api.zooniverse.org/projects/spacewarp/talk/subjects/"+lensname)
                if resp.status_code >= 400 or len(resp.text) ==0:
                    raise ValueError
                json = resp.json()
                print 'ok',
            except:
                print 'error',
                json = {}
            
            with open(fn, 'w') as jsonf:
                jsonf.write(JSON.dumps(json))
                print 'written',
                
        # do something with data? no do in loadJSON..


def loadLensJSONData():

    print "\nLOAD LENS DATA FROM FILE:\n"

    ln = len(D.lenses.keys())
    
    for i, lensname in enumerate(D.lenses.keys()):
        fn = join(lensdatadir, "%s.json"%lensname)
        print "parsing data for lens", lensname, '(%3i / %3i)' % (i, ln),

        with open(fn) as jsonf:
            json = JSON.loads(jsonf.read())

            url = json.get('location',{}).get('standard',"")
            tags = json.get('tags', {})
            comments = json.get('discussion',{}).get('comments',[])
        
            tagsstr = ";".join(['{_id},{count}'.format(**_) for _ in tags])
    
            D.lenses[lensname]['url'] = url
            D.lenses[lensname]['tags'] = tags
            D.lenses[lensname]['tagstr'] = tagsstr
            D.lenses[lensname]['comments'] = comments
            
        print "done"



#def getLensImgs():
#
#    print "\nGET LENS DATA FROM SW:\n"
#
#    if isfile(lensdatacsv):
#        try:
#            print "lensdatacsv already present, skipping and reading from file"
#            with open(lensdatacsv, 'rb') as csvfile:
#                csvr = csv.reader(csvfile)
#                for row in csvr:
#                    if len(row[2])>0:
#                        tags = dict({tuple(_.split(',')) for _ in row[2].split(';')})
#                    else:
#                        tags = {}
#                    D.lenses[row[0]]['url']=row[1]
#                    D.lenses[row[0]]['tags'] = tags
#                    D.lenses[row[0]]['tagstr'] = row[2]
#            return
#        except IndexError:
#            print "Some key not found, refetching all the data"
#            pass
#
#
#    with open(lensdatacsv, 'wb') as csvfile:
#        csvr = csv.writer(csvfile)
#
#        ln = len(D.lenses.keys())
#        for i, lensname in enumerate(D.lenses.keys()):
#            print "getting url for", lensname, '(%3i / %3i)' % (i, ln),
#            try:
#                resp = rq.get("https://api.zooniverse.org/projects/spacewarp/talk/subjects/"+lensname)
#                if resp.status_code >= 400 or len(resp.text) ==0:
#                    raise ValueError
#                json = resp.json()
#                url = json['location']['standard']
#                tags = json['tags']
#            except:
#                print "!! ERROR !!",
#                json = {}
#                url = ""
#                tags = {}
#
#            tagsstr = ";".join(['{_id},{count}'.format(**_) for _ in tags])
#            if len(tagsstr) > 0:
#                tags = dict({tuple(_.split(',')) for _ in tagsstr.split(';')})
#            else: tags = {}
# 
#            D.lenses[lensname]['json'] = json
#            D.lenses[lensname]['url'] = url
#            D.lenses[lensname]['tags'] = tags
#            D.lenses[lensname]['tagstr'] = tagsstr
#            
#            csvr.writerow([lensname, url, tagsstr])
#            print "Done"


def makeThumbs():
    
    newSize = (256,256)
    
    print "\nCREATING THUMBNAILS:\n"

    if not isdir(thumbdir):
        makedirs(thumbdir)
    
    for imgpath in glob(join(imgdir, '*.png')):
        dirr, orgFName = split(imgpath)
        orgName, ext = splitext(orgFName)
        thumbFName = orgName + '' + ext
        thumbPath = join(thumbdir, thumbFName)
        print 'working on:', orgFName,
        sys.stdout.flush()
        
        if isfile(thumbPath):
            print "SKIPPING (already present)"
            continue
        with open(imgpath) as f:
            img = Image.open(f)
            img.thumbnail(newSize, Image.ANTIALIAS)
            img.save(thumbPath)
        print 'done'
        
                
def printTree():
    
    def prT(tree, lvl=0):
        if not tree: return
        for k, v in tree.items():
            print "  "+"| "*lvl + "|-- " + '%05i '%k + '[pxR: %02i; usr: %s]' % (int(D.models[k]['pixrad']), D.models[k]['user'])
            prT(v, lvl+1)
    
    for k, v in D.cldTree.items():
        print '\n'+k
        prT(v, 0)
                        



def createHTMLTree():

    print "\nCREATING HTMLTREE:\n"
    
    html = [
        '<!DOCTYPE HTML>',
        '<html>',
        '<head>',
        '<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />',
        '<title>Your Website</title>',

        '<link href="css/jquery.treetable.css" rel="stylesheet" type="text/css" />',
        '<link href="css/jquery.treetable.theme.default.css" rel="stylesheet" type="text/css" />',
        '<link href="css/lightbox.css" rel="stylesheet" />',
        '<link href="css/screen.css" rel="stylesheet" type="text/css" />',
        '<link href="http://fonts.googleapis.com/css?family=Inconsolata:400,700" rel="stylesheet" type="text/css" />',

        '<script src="js/jquery-1.11.2.min.js"></script>',
        '<script src="js/jquery.treetable.js"></script>',
        '<script src="js/lightbox.min.js"></script>',
        '<style type="text/css">'
        ]
        
    for lvl in range(10):
        color = [
            '#',
            '%02x' % (255-lvl*25),
            '%02x' % (255-lvl*25),
            '%02x' % (255-lvl*25)
            ]
        html.append(
            '.lvl%i { background-color: %s; }' % (lvl, ''.join(color))
        )
        
    html.extend([
        '</style>'
        '</head>',

        '<body>',
        '<h1>HTMLTree</h1>',
    ])
    
    def getImgTag(mid, fname, asw):
        tag = [
            '<a',
            'href="%s/%06i_%s"' % (imgdirname, mid, fname),
            'data-lightbox="%s"' % asw,
            'data-title="Model: %06i (%s)"' % (mid, asw),
            '>',
            '',
            '<img',
            'src="%s/%06i_%s"' % (thumbdirname, mid, fname),
            'style="height:200px"',
            '>',
            '</a>'

        ]        
        return ' '.join(tag)
        

    def getTags(asw):
        tags = D.lenses[asw]["tags"]
        html = '<span class="tags">tags: '
        for t in tags:
            html += '<span>%s (%i)</span>' % (t['_id'], t['count'])
        html += '</span>'
        return html


    def getComments(asw):
        comments = D.lenses[asw]["comments"]
        html = [
            '<span id="box">',
            '<a href="#"> Comments',
            '<span class="childrens">'
            ]
        for c in comments:
            body = re.sub(r'[^\x00-\x7F]+',' ', c['body'])
            usern = re.sub(r'[^\x00-\x7F]+',' ', c['user_name'])
            html.append(
            '<b>%s:</b><br />%s<br />' % (usern, body)
            )
        html.extend([
            '</span>',
            '</a>',
            '</span>'
            ])
        
        return '\n'.join(html)
        
    
    def prT(tree, lvl, html, parent, asw):
        if not tree: return
        for k, v in tree.items():
            if not parent:
                phtml = ''
            else:
                phtml = ' data-tt-parent-id="%06i"' % parent
            idhtml = 'data-tt-id="%06i"' % k
            tr = [
                '<tr %s %s class="lvl%i">' % (phtml, idhtml, lvl),
                '  <td>',
                '    <span class="mod_name">%06i</span>' % k,
                '    <span class="mod_detail">pxrad: %i<br />usr: %s</span>' % (int(D.models[k]['pixrad']), D.models[k]['user']),
                '  </td>',
                '  <td>%s</td>' % getImgTag(k, 'input.png', asw),
                '  <td>%s</td>' % getImgTag(k, 'img1.png', asw),
                '  <td>%s</td>' % getImgTag(k, 'img2.png', asw),
            ]
#            print isfile(join(thumbdir, '%06i_img3_ipol.png'%k)), join(thumbdir, '%06i_img3_ipol.png'%k)
            if isfile(join(thumbdir, '%06i_img3_ipol.png'%k)):
                tr.append('  <td>%s</td>' % getImgTag(k, 'img3_ipol.png', asw))
            else:
                tr.append('  <td>%s</td>' % getImgTag(k, 'img3.png', asw))
            tr.append('</tr>')
            
            html.append('\n'.join(tr))
            prT(v, lvl+1, html, k, asw)
    
    ln = len(D.cldTree.keys())
    for i, itm in enumerate(sorted(D.cldTree.items())):
        k, v = itm
        #print getComments(k)
        try:
            url = D.lenses[k]['url']
        except KeyError:
            url = ""
        if url and len(url)>0:
            a  = '<a href="%s" data-lightbox="%s" data-title="Lens: %s">' % (url, k, k)
            a += k[:-4] + '<span class="subid">%s</span>' % k[-4:]
            a += '</a>'
        else:
            a = k[:-4] + '<span class="subid">%s</span>' % k[-4:]
        html.extend([
            '<h2>',
            a,
            '</h2>',
            '<p class="lensinfo">',
            '(%3i/%3i)' % (i+1, ln),
            '</p>'
            '<p class="lensinfo">',
            '<a href="http://talk.spacewarps.org/#/subjects/%s">SW</a>' % k,
            '</p>',
            '<p class="lensinfo">',
            getComments(k),
            '</p>',
            '<p class="lensinfo">',
            getTags(k),
            '</p>',
            '<table id="%s" class="treetable">' % k
            ])
        prT(v, 0, html, None,k)
        html.extend([
            '</table>',
            '<script>',
            '$(".treetable").treetable("expandAll");',
            '</script>',
        ])

    html.extend([
        '<script>',
        '$("#%s").treetable();',
        '</script>',
        '</body>',
        '</html>'
    ])
    with open(join(outdir, 'tree.html'), 'w') as f:
        f.write('\n'.join(html))
        
    # link assets
    lst = [ split(_1)+(_2,) for _1,_2 in [split(_) for _ in glob('assets/*/*')]]
    for rt, dr, fn in lst:
        if not isdir(join(outdir, dr)):
            makedirs(join(outdir, dr))
        if not isfile(join(outdir, dr, fn)) and not islink(join(outdir, dr, fn)):
            symlink(join('..', '..', rt, dr, fn), join(outdir, dr, fn))


#    if not isdir(join(outdir, 'js')):
#        copytree('assets/js', join(outdir, 'js'))
#    if not isdir(join(outdir, 'css')):
#        copytree('assets/css', join(outdir, 'css'))
#
#
#    for p in [_.split(os.sep) for _ in glob('assets/*/*.*')]:
#        dr, fn = p[-2], p[-1]
#        ndr = join(outdir, dr)
#        makedirs(ndr)
#        
#    glob('assets/*/*.*')
#    
#    for _, dr in map(os.path.split, glob('assets/*')):
#        copytree(join(_, dr), join(outdir, dr))
#    
#    for p in [join(outdir, 'js'), join(outdir, 'css')]:
#        makedirs(p)
#    
#    symlink('assets/js', join(outdir, 'js'))
#    symlink('assets/css', join(outdir, 'css'))


#
# AND THE END
###############################################################################

def main():
    if not isfile(allresultscsv):
        fetchSLresults()
        
    dictSLresults()
    readClaudesList()
    processLists()

    getModelImgs()
#    getLensImgs()
    getLensJSONData()
    loadLensJSONData()
    makeThumbs()
    
    createHTMLTree()

   
if __name__ == "__main__":
    main()
    
