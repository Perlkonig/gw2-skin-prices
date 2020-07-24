import argparse
import json
import sqlite3
import requests
import numpy

# print("This will wipe out the existing item database and redownload tens of thousands of records from the API! It will take approximately 15 minutes, depending on your connection. To continue, hit Enter. Otherwise, hit Ctrl+C.")
# input("")

# Init database
db = sqlite3.connect('skinner.db')
c = db.cursor()
c.execute('''DROP TABLE IF EXISTS items''')
c.execute('''CREATE TABLE items 
             (id INTEGER PRIMARY KEY, name STRING, type STRING, subtype STRING, rarity STRING, skin INTEGER, chat STRING, notrade BOOL)''')
c.execute("CREATE INDEX idx_type ON items (type)")             
c.execute("CREATE INDEX idx_rarity ON items (rarity)")
c.execute("CREATE INDEX idx_subtype ON items (subtype)")
c.execute("CREATE INDEX idx_types ON items (type, subtype)")
c.execute("CREATE INDEX idx_notrade ON items (notrade)")
db.commit()

baseurl = "https://api.guildwars2.com/v2/items"

# Get list of item ids
response = requests.get(baseurl)
assert(response.status_code == 200)
ids = response.json()
total = len(ids)

# chunk list so url length does not exceed 2k chars
numchunks = 400
chunks = numpy.array_split(ids, numchunks)

# Get data for each chunk
c = db.cursor()
i = 0
for chunk in chunks:
    i += 1
    param = ','.join([str(x) for x in chunk])
    print("Fetching chunk {} of {} ({} records)".format(i, len(chunks), len(chunk)))
    response = requests.get(baseurl + "?ids=" + param)
    response.raise_for_status()
    assert(response.status_code == 200)
    rec = response.json()
    for r in rec:
        thisid = r["id"]
        thischat = None
        if ("chat_link" in r):
            thischat = r["chat_link"]
        thisname = r["name"]
        thistype = r["type"]
        thisrarity = r["rarity"]
        thisskin = None
        if ("default_skin" in r):
            thisskin = r["default_skin"]
        thissubtype = None
        if ( ("details" in r) and ("type" in r["details"]) ):
            thissubtype = r["details"]["type"]
        thisnotrade = False
        if ( ("AccountBound" in r["flags"]) or ("SoulbindOnAcquire" in r["flags"]) ):
            thisnotrade = True
        c.execute("INSERT INTO items (id, name, type, subtype, rarity, skin, chat, notrade) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (thisid, thisname, thistype, thissubtype, thisrarity, thisskin, thischat, thisnotrade))
db.commit()

db.close()
