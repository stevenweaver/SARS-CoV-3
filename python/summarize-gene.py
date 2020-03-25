"""
Summarize HyPhy selection analyses for a gene from JSON files

    SLAC (required)
    FEL  (required)
    MEME (required)
    PRIME (optional)

Author:
    Sergei L Kosakovsky Pond (spond@temple.edu)

Version:
    v0.0.1 (2020-03-23)


"""

import argparse
import sys
import json
import re
import datetime
import os
from   os import  path
from   Bio import SeqIO



arguments = argparse.ArgumentParser(description='Summarize selection analysis results.')

arguments.add_argument('-o', '--output', help = 'Write results here', type = argparse.FileType('w'), default = sys.stdout)
arguments.add_argument('-s', '--slac',   help = 'SLAC results file', required = True, type = argparse.FileType('r'))
arguments.add_argument('-f', '--fel',   help = 'FEL results file', required = True, type = argparse.FileType('r'))
arguments.add_argument('-m', '--meme',   help = 'MEME results file', required = True, type = argparse.FileType('r'))
arguments.add_argument('-p', '--prime',  help = 'PRIME results file', required = False, type = argparse.FileType('r'))
arguments.add_argument('-P', '--pvalue',  help = 'p-value', required = False, type = float, default = 0.1)
arguments.add_argument('-c', '--coordinates',  help = 'An alignment with reference sequence (assumed to start with NC)', required = True, type = argparse.FileType('r'))


import_settings = arguments.parse_args()

slac = json.load (import_settings.slac)
fel  = json.load (import_settings.fel)
meme = json.load (import_settings.meme)

if import_settings.prime:
    prime  = json.load (import_settings.prime)
else:
    prime = None
    
ref_seq_map = None
ref_seq_re = re.compile ("^NC")

for seq_record in SeqIO.parse(import_settings.coordinates, "fasta"):
    seq_id   = seq_record.description
    if ref_seq_re.search (seq_id):
        ref_seq = str(seq_record.seq).upper()
        i = 0
        c = 0
        ref_seq_map = []
        while i < len (ref_seq):
            ref_seq_map.append (c)
            if ref_seq[i:i+3] != '---':
                c += 1
            i+=3
        break
        
if ref_seq_map is None:
    raise Exception ("Misssing reference sequence for coordinate mapping")

    
# compile the list of sites that are under selection by either MEME or FEL

site_list = {}
sequences = slac["input"]["number of sequences"]
sites = slac["input"]["number of sites"]
tree = slac["input"]["trees"]["0"]

L = 0
for b,v in slac["tested"]["0"].items():
    if v == "test":
        L += slac["branch attributes"]["0"][b]["Global MG94xREV"]
        
    
for i, row in enumerate (fel["MLE"]["content"]["0"]):
    if row[4] < import_settings.pvalue :
        site_list[i] = {'fel' : row[4], 'kind' : 'positive' if row[1] > row[0] else 'negative'}
    
for i, row in enumerate (meme["MLE"]["content"]["0"]):
    if row[6] < import_settings.pvalue or i in site_list:
        if i in site_list:
            site_list[i]['meme'] = row[6]
            site_list[i]['meme-fraction'] = row[4]
        else:
            site_list[i] = {'meme' : row[6], 'fel' : fel["MLE"]["content"]["0"][i][4], 'meme-fraction' : row[4]}


for site in site_list:
    site_list[site]['meme-branches'] = meme["MLE"]["content"]["0"][site][7]
    site_list[site]['substitutions'] = [slac["MLE"]["content"]["0"]['by-site']['RESOLVED'][site][2],slac["MLE"]["content"]["0"]['by-site']['RESOLVED'][site][3]]
    labels      = {}
    composition = {}
    for node,value in slac["branch attributes"]["0"].items():
        if value["amino-acid"][0][site] not in composition:
            composition[value["amino-acid"][0][site]] = 1
        else:
            composition[value["amino-acid"][0][site]] += 1
            
        labels[node] = [value["amino-acid"][0][site],value["codon"][0][site],value["nonsynonymous substitution count"][0][site],value["synonymous substitution count"][0][site]]
    site_list[site]['composition'] = composition
    site_list[site]['labels'] = labels
    
    if prime:
        site_list[site]['prime'] = []
        prime_row = prime["MLE"]["content"]["0"][site]
        prime_headers = prime["MLE"]["headers"]
        for idx in [5,7,10,13,16,19]:
            if prime_row[idx] <= import_settings.pvalue :
               if idx == 5:
                    site_list[site]['prime'].append (['Overall', prime_row[idx], 0])
               else:
                    site_list[site]['prime'].append ([prime_headers[idx][1].replace ('p-value for non-zero effect of ',''), prime_row[idx], prime_row[idx-1]])
                    
        
json_out = {
    'sequences' : sequences,
    'sites' : sites,
    'tree' : tree,
    'L' : L,
    'p' : import_settings.pvalue,
    'selection' : site_list,
    'map' : ref_seq_map
}

json.dump (json_out, import_settings.output)
    
