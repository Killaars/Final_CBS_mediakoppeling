#%%
from pathlib import Path
import pandas as pd


def process_taxonomie_database():
    '''
    Function to process the cbs taxonomie database of Henk Laloli.
    Input:
        None, but uses the .txt database dump at the specified location
    Output:
        Writes pandas dataframe as csv at specified location. Word is on the index and the other terms in the columns
    '''
    libpath = Path('/Users/rwsla/Lars/CBS_2_mediakoppeling/data/taxonomie/')
    
    f = open(str(libpath / "cbs-taxonomie-alfabetische-lijst.txt"), "r",encoding='utf-8')
    
    lines = [line.rstrip('\n') for line in f]
    lines = lines[8:] #skip header
    lines = filter(None, lines) # remove elements that contain of empty strings
    df = pd.DataFrame()
    for x in lines:
        if not x.startswith('	'): # no tab means word
            index = x
            for column in ['GEBRUIK','TT','UF','BT','RT','CBS English','NT','Historische notitie',
                           'Scope notitie','Code','Eurovoc','DF','EQ']:
                df.loc[index,column] = 999 # empty value to be replaced later
        if x.startswith('	'): # tab means other term of previous word
            column = x.split(':')[0][1:] # skip first two letters '/t'
            value = x.split(':')[1][1:] # second part is the word, starts with space
            if df.loc[index,column] == 999: # if first term for that word
                df.loc[index,column] = value
            else: # second term for that word
                df.loc[index,column] = value+', '+str(df.loc[index,column])
            
    f.close()
    df = df[['GEBRUIK','TT','UF','BT','RT','CBS English','NT','Historische notitie','Scope notitie']]
    df[df==999] = None # replace all empty cells
    df.to_csv(str(libpath / 'taxonomie_df.csv'))
    
    '''
    TT = TopTerm
    UF = Gebruikt voor
    BT = BredereTerm
    RT = RelatedTerm
    NT = NauwereTerm
    '''
process_taxonomie_database()