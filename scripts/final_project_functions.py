#%%
import numpy as np
import pandas as pd
from pathlib import Path
import re

from multiprocessing import  Pool
from functools import partial
from project_variables import project_path

path = Path(project_path)

#%% 
# Variables
upwindow = 7
lowwindow = 2

'''
Preprocessing fuction for both the children as the parents
'''
def preprocessing_parent(parents):
    # Parents
    parents.loc[:,'publish_date_date'] = pd.to_datetime(parents.loc[:,'publish_date_date'])
    parents.loc[:,'title'] = parents.loc[:,'title'].str.lower()
    parents.loc[:,'content'] = parents.loc[:,'content'].str.lower()
    parents.loc[:,'content'] = parents.loc[:,'content'].str.replace('-',' ')
    parents.loc[:,'content'] = parents.loc[:,'content'].str.replace('  ',' ')
    parents['related_children'] = parents['related_children'].str.replace('matches/','').str.split(',')
    
    taxonomie_df = pd.read_csv(str(path /'data/taxonomie_df.csv'),index_col=0)
    taxonomie_df[taxonomie_df=='999'] = None
    taxonomie_df[taxonomie_df=='999.0'] = None
    parents.loc[:,'found_synonyms'] = parents.apply(find_synoniemen, args=(taxonomie_df,),axis=1)
    parents.loc[:,'Gebruik_UF'] = [d[0] for d in parents['found_synonyms']]
    parents.loc[:,'BT_TT'] = [d[1] for d in parents['found_synonyms']]
    parents.drop(['found_synonyms'], axis=1)
    
    # select numbers from parent
    parents.loc[:,'parent_numbers'] = parents.apply(regex,args=('content',),axis=1)
    
    parents.loc[:,'first_paragraph_without_stopwords'] = parents.apply(select_and_prepare_first_paragraph_of_CBS_article,axis=1)
    parents.loc[:,'title_without_stopwords'] = parents.apply(select_and_prepare_title_of_CBS_article,axis=1)
    
    # remove numbers from parent
    parents.loc[:,'content_no_numbers'] = parents.apply(remove_numbers,args=('content',),axis=1)    
    # remove stopwords from content
    parents.loc[:,'content_without_stopwords'] = parents.apply(remove_stopwords_from_content, args=('content_no_numbers',),axis=1)
    return parents

def preprocessing_child(children):    
    # Children
    children.loc[:,'title'] = children.loc[:,'title'].str.lower()
    children.loc[:,'content'] = children.loc[:,'content'].str.lower()
    children['related_parents'] = children['related_parents'].str.replace('matches/','').str.split(',')
    children.loc[:,'publish_date_date'] = pd.to_datetime(children.loc[:,'publish_date_date'])
#    children.loc[:,'content'] = children.loc[:,'content'].str.replace('-',' ') Breaks check_link
#    children.loc[:,'content'] = children.loc[:,'content'].str.replace('  ',' ')
    
    # replace other references to cbs with cbs itself
    children.loc[:,'content'] = children.loc[:,'content'].str.replace('centraal bureau voor de statistiek','cbs')
    children.loc[:,'content'] = children.loc[:,'content'].str.replace('cbs(cbs)','cbs')
    children.loc[:,'content'] = children.loc[:,'content'].str.replace('cbs (cbs)','cbs')
    children.loc[:,'content'] = children.loc[:,'content'].str.replace('cbs ( cbs )','cbs')
    return children

def find_link(row):
    '''
    # Function to check if there is a link to the CBS site
    # children['cbs_link_in_child'] = children.apply(find_link,axis=1)
    
    Input: 
        - row with all data regarding the newsarticle (content is used)
        - dataframe with all parents
    Ouput: id(s) from parent article
    '''
    # select content from row
    link=''
    content = row['content']
    if type(content) != float:
        # some preprocessing of the content
        content = content.replace('- ','-')
        # split the content in words
        splitted = content.split(' ')
        
        
        # check the words for cbs site
        for split in splitted:
            if 'www.cbs.nl/' in split:
                #link.append(split)
                link=split
                if type(link)==str:
                    link = link.translate({ord(i):None for i in '()'})
                    # puts them nicely in a list if any article has multiple links. 
    #                for id in parents[parents['link'].str.contains(link)==True]['id'].values:
    #                    matches_to_return.append(id)
    return link

def find_id(row,df,level):
    '''
    Function to get Id back from the levels generated by the record linkage
    '''
    return df.loc[row[level],'id']

def find_title(row):
    '''
    Check if whole title is in the content of the child article
    '''
    title = row['title_parent']
    
    try:
        if (title in row['content_child'])&(type(title) != float):
            return 1
        else:
            return 0
    except:
        return 0
    
def find_sleutelwoorden_UF(row):
    '''
    Get jaccard score and number of matches based on the sleutelwoorden and highest taxonomy synomyms
    '''
    if type(row['content_child_no_stop']) == float:
        return pd.Series([0,0,{''}])
    content = re.sub(r'[^\w\s]','',row['content_child_no_stop'])                             # Remove punctuation
    if type(row['taxonomies']) == float:
        return pd.Series([0,0,{''}])
    try:
        taxonomies = row['taxonomies'].split(',')
        # extend list of sleutelwoorden, or append, depending on the size of the synonyms. 
        if len(row['Gebruik_UF'].split(' '))>1:
            taxonomies.extend(row['Gebruik_UF'].split(' '))
        else:
            taxonomies.append(row['Gebruik_UF'].split(' '))
        matches = {x for x in taxonomies if x in content}
        jaccard = len(matches)/len(list(set(taxonomies)))
        return pd.Series([jaccard, len(matches),matches])
    except:
        return pd.Series([0,0,{''}])
    
def find_BT_TT(row):
    '''
    Get jaccard score and number of matches based on the Broader Terms and Top Terms of the sleutelwoorden    
    '''
    if type(row['content_child_no_stop']) == float:
        return pd.Series([0,0,{''}])
    content = re.sub(r'[^\w\s]','',row['content_child_no_stop'])                             # Remove punctuation
    if type(row['BT_TT']) == float:
        return pd.Series([0,0,{''}])
    try:
        taxonomies = row['BT_TT'].split(' ')
        matches = {x for x in taxonomies if x in content}
        jaccard = len(matches)/len(list(set(taxonomies)))
        return pd.Series([jaccard, len(matches),matches])
    except:
        return pd.Series([0,0,{''}])

def find_title_no_stop(row):
    '''
    Get jaccard score and number of matches based on the words in the introduction
    '''
    if type(row['content_child_no_stop']) == float:
        return pd.Series([0,0,{''}])
    content = re.sub(r'[^\w\s]','',row['content_child_no_stop'])                             # Remove punctuation
    if type(row['title_without_stopwords']) == float:
        return pd.Series([0,0,{''}])
    try:
        taxonomies = row['title_without_stopwords'].split(' ')
        matches = {x for x in taxonomies if x in content}
        jaccard = len(matches)/len(list(set(taxonomies)))
        return pd.Series([jaccard, len(matches),matches])
    except:
        return pd.Series([0,0,{''}])
    
def find_1st_paragraph_no_stop(row):
    '''
    Get jaccard score and number of matches based on the words in the first paragraph of the parent
    '''
    if type(row['content_child_no_stop']) == float:
        return pd.Series([0,0,{''}])
    content = re.sub(r'[^\w\s]','',row['content_child_no_stop'])                             # Remove punctuation
    content = re.sub(r'cbs','',row['content_child_no_stop'])                             # Remove cbs
    if type(row['first_paragraph_without_stopwords']) == float:
        return pd.Series([0,0,{''}])
    try:
        taxonomies = row['first_paragraph_without_stopwords'].split(' ')
        matches = {x for x in taxonomies if x in content}
        jaccard = len(matches)/len(list(set(taxonomies)))
        return pd.Series([jaccard, len(matches),matches])
    except:
        return pd.Series([0,0,{''}])
    
def determine_matches(row):
    '''
    Check if records are a match
    '''
    if str(row['parent_id']) in row['related_parents']:
        return True
    else:
        return False
    
def date_comparison(row,offset,scale):  
    '''
    Compare the dates and return a score
    '''  
    diff = row['date_diff_days']
    return 2**(-(diff-offset)/scale)

def find_numbers(row):
    '''
    Get jaccard score and number of matches based on the words in the first paragraph of the parent
    '''
    content = ' '.join(row.loc['child_numbers'])                             
    try:
        taxonomies = row['parent_numbers']
        matches = {x for x in taxonomies if x in content}
        jaccard = len(matches)/len(list(set(taxonomies)))
        return pd.Series([jaccard, len(matches),matches])
    except:
        return pd.Series([0,0,{''}])
    
def similarity(row,nlp):
    try:
        title_parent = nlp(row['title_without_stopwords'])
        title_child = nlp(row['title_child_no_stop'])
        content_parent = nlp(row['content_without_stopwords'])
        content_child = nlp(row['content_child_no_stop'])
        
        if (title_parent.vector_norm == 0) | (title_child.vector_norm == 0):
            title_similarity = 0
        else:
            title_similarity = title_parent.similarity(title_child)
        if (content_parent.vector_norm == 0) | (content_child.vector_norm == 0):
            content_similarity = 0
        else:
            content_similarity = content_parent.similarity(content_child)
        return pd.Series([title_similarity, content_similarity])
    except:
        return pd.Series([0, 0])
    
def parallelize(data, func, num_of_processes=8):
    data_split = np.array_split(data, num_of_processes)
    pool = Pool(num_of_processes)
    data = pd.concat(pool.map(func, data_split))
    pool.close()
    pool.join()
    return data

def run_on_subset(func, data_subset):
    return data_subset.apply(func, axis=1)

def parallelize_on_rows(data, func, num_of_processes=8):
    return parallelize(data, partial(run_on_subset, func), num_of_processes)
    
def determine_vrijenieuwsgaring(row):
    '''
    Check if records are a match with vrijenieuwsgaring
    '''
    if '158123' in row['related_parents']:
        return True
    else:
        return False

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
    lines = lines[8:]
    lines = filter(None, lines) # remove elements that contain of empty strings
    df = pd.DataFrame()
    for x in lines:
        if not x.startswith('	'):
            index = x
            for column in ['GEBRUIK','TT','UF','BT','RT','CBS English','NT','Historische notitie',
                           'Scope notitie','Code','Eurovoc','DF','EQ']:
                df.loc[index,column] = 999
        if x.startswith('	'):
            column = x.split(':')[0][1:] # skip first two letters '/t'
            value = x.split(':')[1][1:] # second part is the word, starts with space
            if df.loc[index,column] == 999:
                df.loc[index,column] = value
            else:
                df.loc[index,column] = value+', '+str(df.loc[index,column])
            
    f.close()
    df = df[['GEBRUIK','TT','UF','BT','RT','CBS English','NT','Historische notitie','Scope notitie']]
    df[df==999] = None
    df.to_csv(str(libpath / 'taxonomie_df.csv'))
    
    '''
    TT = TopTerm
    UF = Gebruikt voor
    BT = BredereTerm
    RT = RelatedTerm
    NT = NauwereTerm
    '''
    
def find_synoniemen(row,taxonomie_df):
    '''
    sleutelwoorden(taxonomie) aanvullen met synoniemen op basis van de taxonomie database van Henk Laloli:
        2 kolommen, een met de Gebruik kolom en de UsedFor kolom uit de database en een met de BredereTerm en de TopTerm.
        De resultaten van de laatste kolom moeten in mindere mate meewerken aan matching score. 
    '''
    import nltk
    from nltk.corpus import stopwords
    
    stop_words = set(stopwords.words('dutch'))
    taxonomies = row['taxonomies']
    Gebruik_UF = ''
    BT_TT = ''
    if type(taxonomies) != float:     
        taxonomies = taxonomies.split(',')                                     # Some parents have no content (nan)
        for taxonomie in taxonomies:
            if taxonomie in taxonomie_df.index:
                if taxonomie_df.loc[taxonomie,'GEBRUIK'] != None:
                    Gebruik_UF = Gebruik_UF + ' ' + taxonomie_df.loc[taxonomie,'GEBRUIK']
                if taxonomie_df.loc[taxonomie,'UF'] != None:
                    Gebruik_UF = Gebruik_UF + ' ' + taxonomie_df.loc[taxonomie,'UF']
                if taxonomie_df.loc[taxonomie,'TT'] != None:
                    BT_TT = BT_TT + ' ' + taxonomie_df.loc[taxonomie,'TT']
                if taxonomie_df.loc[taxonomie,'BT'] != None:
                    BT_TT = BT_TT + ' ' + taxonomie_df.loc[taxonomie,'BT']
    
    temp = nltk.tokenize.word_tokenize(Gebruik_UF)
    Gebruik_UF = [w for w in temp if not w in stop_words]
    temp = nltk.tokenize.word_tokenize(BT_TT)
    BT_TT = [w for w in temp if not w in stop_words]
    return (' '.join(Gebruik_UF),' '.join(BT_TT))

def select_and_prepare_first_paragraph_of_CBS_article(row, column = 'content'):
    '''
    Function to find the first paragraph of the CBS article, remove stopwords and return it as a string.
    '''
    import nltk
    from nltk.corpus import stopwords
    import re
    stop_words = set(stopwords.words('dutch'))
    
    filtered_intro = ''                                                 # Set as empty string for rows without content
    content = row[column]
    if type(content) != float:                                          # Some parents have no content (nan)
        intro = content.split('\n')[0]                                  # Select first block of text
        intro = re.sub(r'[^\w\s]','',intro)                             # Remove punctuation
        intro = nltk.tokenize.word_tokenize(intro)
        filtered_intro = [w for w in intro if not w in stop_words]      # Remove stopwords
    return ' '.join(filtered_intro)                                     # Convert from list to space-seperated string

def select_and_prepare_title_of_CBS_article(row, column = 'title'):
    '''
    Function to remove stopwords from the title and return it as a string.
    '''
    import nltk
    from nltk.corpus import stopwords
    import re
    stop_words = set(stopwords.words('dutch'))
    
    filtered_title = ''                                                 # Set as empty string for rows without content
    title = row[column]
    if type(title) != float:                                          # Some parents have no content (nan)
        title = re.sub(r'[^\w\s]','',title)                             # Remove punctuation
        title = nltk.tokenize.word_tokenize(title)
        filtered_title = [w for w in title if not w in stop_words]      # Remove stopwords
    return ' '.join(filtered_title)                                     # Convert from list to space-seperated string

def remove_stopwords_from_content(row, column = 'content'):
    '''
    Function to remove stopwords from the content and return it as a string.
    '''
    import nltk
    from nltk.corpus import stopwords
    import re
    stop_words = set(stopwords.words('dutch'))
    
    filtered_content = ''                                                 # Set as empty string for rows without content
    content = row[column]
    if type(content) != float:                                          # Some parents have no content (nan)
        content = re.sub(r'[^\w\s]','',content)                             # Remove punctuation
        content = nltk.tokenize.word_tokenize(content)
        filtered_content = [w for w in content if not w in stop_words]      # Remove stopwords
    return ' '.join(filtered_content)                                     # Convert from list to space-seperated string

def regex(row, column = 'content'):
    import re
    
    matches_to_return = []
    if type(row[column]) != float:
   
        regex = r"\b(nul)\b|\b([a-zA-Z]*(twin|der|veer|vijf|zes|zeven|acht|negen)tig|[a-zA-Z]*tien|twee|drie|vier|vijf|zes|zeven|acht|negen|elf|twaalf)( )?(honderd|duizend|miljoen|miljard|procent)?\b|\b(honderd|duizend|miljoen|miljard)\b|\b[-+]?[.|,]?[\d]+(?:,\d\d\d)*[\.|,]?\d*([.|,]\d+)*(?:[eE][-+]?\d+)?( )?(honderd|duizend|miljoen|miljard|procent|%)?|half (miljoen|miljard|procent)"
        matches = re.finditer(regex, row[column])
        
        for matchNum, match in enumerate(matches, start=1):
            string = match.group().strip().strip('.')
            string = re.sub('%',' procent',string)
            if re.match(r"(\d{1,3}[.]){1,3}\d{3}",string):
                string= string.replace('.','')
            else:
                string= string.replace(',','.')
            
            if string.endswith(('honderd','duizend','miljoen','miljard','procent')):
                endstring = re.search(r'honderd|duizend|miljoen|miljard|procent',string).group()
                if endstring=='honderd':
                    endstringmultiplier = 100
                elif endstring=='duizend':
                    endstringmultiplier = 1000
                elif endstring=='miljoen':
                    endstringmultiplier = 1000000
                elif endstring=='miljard':
                    endstringmultiplier = 1000000000
                elif endstring=='procent':
                    endstringmultiplier = 1
                else:
                    endstringmultiplier = 1
                
                # remove endstring from string
                string = re.sub('honderd|duizend|miljoen|miljard|procent',  '',string)
                # if empty, only endstring was string, example honderd
                if re.match(r"(\d{1,3}[.]){1,3}\d{3}",string):
                    string= string.replace('.','')
                else:
                    string= string.replace(',','.')
                if string == '':
                    matches_to_return.append(str(endstringmultiplier)) 
                else:
                    try:
                        string = own_word2num(string.strip('.').strip())# strip points and spaces in around match
                        if endstring=='procent':
                            matches_to_return.append(str(string)+' procent')
                        else:
                            matches_to_return.append(str(float(string)*endstringmultiplier)) 
                    except:
                        try:
                            string = string.strip('.').strip()
                            if endstring=='procent':
                                matches_to_return.append(str(string)+' procent')
                            else:
                                matches_to_return.append(str(float(string)*endstringmultiplier))
                        except:
                            pass
            else:
                try:
                    matches_to_return.append(str(own_word2num(string))) 
                except:
                    matches_to_return.append(str(string))
    return list(set(matches_to_return))

def remove_numbers(row, column = 'content'):
    import re
    import numpy as np
    
    if type(row[column]) != float:
        regex = r"\b(nul)\b|\b([a-zA-Z]*(twin|der|veer|vijf|zes|zeven|acht|negen)tig|[a-zA-Z]*tien|twee|drie|vier|vijf|zes|zeven|acht|negen|elf|twaalf)( )?(honderd|duizend|miljoen|miljard|procent)?\b|\b(honderd|duizend|miljoen|miljard)\b|\b[-+]?[.|,]?[\d]+(?:,\d\d\d)*[\.|,]?\d*([.|,]\d+)*(?:[eE][-+]?\d+)?( )?(honderd|duizend|miljoen|miljard|procent|%)?|half (miljoen|miljard|procent)"
        return re.sub(regex,'',row[column])
    else:
        return(np.nan)
        
def own_word2num(string):
    getal_dictionary = {
        'nul': 0,
        'half':0.5,
        'een': 1,
        'twee': 2,
        'drie': 3,
        'vier': 4,
        'vijf': 5,
        'zes': 6,
        'zeven': 7,
        'acht': 8,
        'negen': 9,
        'tien': 10,
        'elf': 11,
        'twaalf': 12,
        'dertien': 13,
        'veertien': 14,
        'vijftien': 15,
        'zestien': 16,
        'zeventien': 17,
        'achttien': 18,
        'negentien': 19,
        'twintig': 20,
        'eenentwintig': 21,
        'tweeentwintig': 22,
        'drieentwintig': 23,
        'vierentwintig': 24,
        'vijfentwintig': 25,
        'zesentwintig': 26,
        'zevenentwintig': 27,
        'achtentwintig': 28,
        'negenentwintig': 29,
        'dertig': 30,
        'eenendertig': 31,
        'tweeendertig': 32,
        'drieendertig': 33,
        'vierendertig': 34,
        'vijfendertig': 35,
        'zesendertig': 36,
        'zevenendertig': 37,
        'achtendertig': 38,
        'negenendertig': 39,
        'veertig': 40,
        'eenenveertig': 41,
        'tweeenveertig': 42,
        'drieenveertig': 43,
        'vierenveertig': 44,
        'vijfenveertig': 45,
        'zesenveertig': 46,
        'zevenenveertig': 47,
        'achtenveertig': 48,
        'negenenveertig': 49,
        'vijftig': 50,
        'eenenvijftig': 51,
        'tweeenvijftig': 52,
        'drieenvijftig': 53,
        'vierenvijftig': 54,
        'vijfenvijftig': 55,
        'zesenvijftig': 56,
        'zevenenvijftig': 57,
        'achtenvijftig': 58,
        'negenenvijftig': 59,
        'zestig': 60,
        'eenenzestig': 61,
        'tweeenzestig': 62,
        'drieenzestig': 63,
        'vierenzestig': 64,
        'vijfenzestig': 65,
        'zesenzestig': 66,
        'zevenenzestig': 67,
        'achtenzestig': 68,
        'negenenzestig': 69,
        'zeventig': 70,
        'eenenzeventig': 71,
        'tweeenzeventig': 72,
        'drieenzeventig': 73,
        'vierenzeventig': 74,
        'vijfenzeventig': 75,
        'zesenzeventig': 76,
        'zevenenzeventig': 77,
        'achtenzeventig': 78,
        'negenenzeventig': 79,
        'tachtig': 80,
        'eenentachtig': 81,
        'tweeentachtig': 82,
        'drieentachtig': 83,
        'vierentachtig': 84,
        'vijfentachtig': 85,
        'zesentachtig': 86,
        'zevenentachtig': 87,
        'achtentachtig': 88,
        'negenentachtig': 89,
        'negentig': 90,
        'eenennegentig': 91,
        'tweeennegentig': 92,
        'drieennegentig': 93,
        'vierennegentig': 94,
        'vijfennegentig': 95,
        'zesennegentig': 96,
        'zevenennegentig': 97,
        'achtennegentig': 98,
        'negenennegentig': 99,
        'honderd': 100,
        'duizend': 1000,
        'miljoen': 1000000,
        'miljard': 1000000000,
        'punt': '.'
    }

    return(getal_dictionary[string])