# FETCH SPACEWARPS CANDIDATES

This script fetches all the items of claudes space warps candidates list and gets the according models
from spaghettilens.

It downloads all the images, generates additional stuff (make sure glass is available in /glass) and makes a nice output table

## Dependencies

for the first time run, you need `requests` for the web queries:

```
    sudo pip install requests
```

## Usage

It's best used with ipython.


```
$ cd /[reprodir]
$ ipython
In[]: %run main.py
```

If it's the first run, it fetches all the data online and generates all the data. This could take a couple of minutes..

Then all the interessting stuff is in the object D: (You probably want the dicts with prefix `cld` [in honor to the creator of the candidates list with sw username cld])

```
In[]: D.cldTree
In[]: D.cldFlatList
In[]: D.cldList
```

Some useful functions:
```
In[]: printTree()     # print the tree to stdout
In[]: printHTMLTree() # creates an overview html file (tree.html)
```
