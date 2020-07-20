import argparse
import json
import sqlite3
import requests
import numpy

with open('config.json', 'r') as json_file:
    config = json.load(json_file)

# Init database
db = sqlite3.connect('skinner.db')
c = db.cursor()
c.execute('''DROP TABLE IF EXISTS unlocked''')
c.execute('''CREATE TABLE unlocked 
             (skinid INTEGER PRIMARY KEY)''')
db.commit()

baseurl = "https://api.guildwars2.com/v2/account/skins"

# Get list of item ids
response = requests.get(baseurl, headers={'Authorization': 'Bearer {}'.format(config['apikey'])})
assert(response.status_code == 200)
ids = response.json()

# Get data for each chunk
c = db.cursor()
ids = [(x,) for x in ids]
c.executemany("INSERT INTO unlocked VALUES (?)", ids)
db.commit()

db.close()
