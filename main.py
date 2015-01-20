# -*- coding: utf-8 -*-
"""
Created on Mon Jan 19 17:33:36 2015

@author: rafik
"""

import csv
import requests as rq
import cStringIO

import os.path
import shutil

import requests

outdir = 'output'
allresultscsv = 'output/all_results.csv'
claudecsv = 'sw_interesting _objects.csv'

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
    
    outfile = allresultscsv 
    slurl = 'http://mite.physik.uzh.ch/tools/ResultDataTable'
    startid = 115 # because the former are rubbish   
    maxid = 15000 #15000 #currently: 13220
    
    step = 100 # get somany at a time
    
    first = True

    with open(outfile, 'wb') as f:
        writer = csv.writer(f)
    
        for i in range(startid, maxid, step):
    
            print 'working on: %05i - %05i' % (i, i+step-1),
        
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
    
            rows = []    
            filelike = cStringIO.StringIO(rsp.text)
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
    return outfile                        


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

def readClaudesList(fname=claudecsv):
    
    lenses = []

    with open(fname, 'rb') as csvfile:
        csvr = csv.reader(csvfile)
        for row in csvr:
            if row[0].startswith("ASW"):
                lenses.append(row[0])

    D.candidatesNames = lenses



def dictSLresults():
    ''' keep in mind that the field names are somewhat mixed up
    in old spaghettilens: model and result
    corresponds in proper tern: lens (model), model (result)

    idea behind the mess: None; reason:
    lens to be modeled, and a modelling result
    '''

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
                
    
    for key, val in D.lensID_2_modelIDs.items():
        D.getModels[D.lensID_2_lensName[key]] = val

    for modelid in D.modelID_2_lensID.keys():
        root, path = getRoot(modelid,[])
        print root, path
        populateTree(path, D.resultTree)

#
# AND FINALLY DATA PROCESSING
###############################################################################

def mergeLists():
    # get data ready
#    readClaudesList()
#    dictSLresults()
    
    for name in D.candidatesNames:
        try:
            idd = D.lensName_2_lensID[name]
        except KeyError:
            print "no key for",name
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

def getModels():
    '''
    http://mite.physik.uzh.ch/result/012402/input.png
    http://mite.physik.uzh.ch/result/012402/img3_ipol.png
    http://mite.physik.uzh.ch/result/012402/img1.png
    http://mite.physik.uzh.ch/result/012402/img2.png
    http://spacewarps.org/subjects/standard/5183f151e4bb2102190561ab.png
    '''
    
    # get all the results
    for mid in D.cldFlatList:
        for img in ['input.png', 'img3_ipol.png', 'img1.png', 'img2.png']:
            print 'getting', mid, img,
            url = 'http://mite.physik.uzh.ch/result/' + '%06i/' % mid + img
            path = os.path.join(outdir, "%06i_%s" % (mid, img))
            r = requests.get(url, stream=True)
            if r.status_code == 200:
                with open(path, 'wb') as f:
                    for chunk in r.iter_content(1024*4):
                        f.write(chunk)
                print 'done'
            else:
                print 'ERROR'
                
def printTree():
    
    def prT(tree, lvl=0):
        if not tree: return
        for k, v in tree.items():
            print "  "+"| "*lvl + "|-- " + '%05i '%k + '[pxR: %02i; usr: %s]' % (int(D.models[k]['pixrad']), D.models[k]['user'])
            prT(v, lvl+1)
    
    for k, v in D.cldTree.items():
        print '\n'+k
        prT(v, 0)
                        
    

#
# AND THE END
###############################################################################

def main():
    if not os.path.isfile(allresultscsv):
        fetchSLresults()

    dictSLresults()
    readClaudesList()
    mergeLists()

   
if __name__ == "__main__":
    main()
    
