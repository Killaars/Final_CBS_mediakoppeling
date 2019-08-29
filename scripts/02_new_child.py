#%%
from pathlib import Path
import argparse
import pickle
import sys

import pandas as pd
import recordlinkage
from recordlinkage.index import Full
import spacy

from final_project_functions import preprocessing_child,\
                                preprocessing_parent,\
                                find_link,\
                                find_id,\
                                find_title,\
                                find_sleutelwoorden_UF,\
                                find_BT_TT,\
                                find_title_no_stop,\
                                find_1st_paragraph_no_stop,\
                                date_comparison,\
                                regex,\
                                find_numbers,\
                                remove_stopwords_from_content,\
                                similarity,\
                                remove_numbers
from project_variables import project_path,\
                              all_parents_location
all_parents_location = 'data/all_parents.csv'
                              
import warnings
warnings.filterwarnings("ignore")

path = Path(project_path)
modelpath = path / 'scripts'

wordvectorpath = path / 'model/nl_vectors_wiki_lg/'
nlp = spacy.load(wordvectorpath)

# Read arguments
my_parser = argparse.ArgumentParser(description='Add new parent to parent database')
my_parser.add_argument('child_id',
                       type=str,
                       help='ID of the new child article')
my_parser.add_argument('nr_matches',
                       type=int,
                       help='Number of matches to return')
args = my_parser.parse_args()
child_id = args.child_id
nr_matches = args.nr_matches

#child_id = '246'
#child_id = '304042'
#nr_matches = 10

#---------------------------#
# Reading and preprocessing #
#---------------------------#
new_child = pd.read_csv(str(path / ('data/c_%s.csv' %(child_id))))#, index_col=0)
new_child = preprocessing_child(new_child)


# Select numbers from children
new_child.loc[:, 'child_numbers'] = new_child.apply(regex, args=('content', ), axis=1)
new_child.loc[:, 'content_no_numbers'] = new_child.apply(remove_numbers, args=('content', ), axis=1)

# Remove stopwords from title and content
new_child.loc[:, 'title_child_no_stop'] = new_child.apply(remove_stopwords_from_content, args=('title', ), axis=1)
new_child.loc[:, 'content_child_no_stop'] = new_child.apply(remove_stopwords_from_content, args=('content_no_numbers', ), axis=1)

# Find CBS link in child article
new_child.loc[:, 'cbs_link'] = new_child.apply(find_link, axis=1)

# Read all parents
parents = pd.read_csv(str(path / all_parents_location), index_col=0)
parents = preprocessing_parent(parents) ####### Moet niet meer ndig zijn op het laatst

# Parents to datetime
parents.loc[:, 'publish_date_date'] = pd.to_datetime(parents.loc[:, 'publish_date_date'])

# Select useful columns
parents = parents[['id',
                   'publish_date_date',
                   'title',
                   'content',
                   'link',
                   'taxonomies',
                   'Gebruik_UF',
                   'BT_TT',
                   'first_paragraph_without_stopwords',
                   'title_without_stopwords',
                   'content_without_stopwords',
                   'parent_numbers',
                   'related_children']]

new_child = new_child[['id',
                       'publish_date_date',
                       'title',
                       'content',
                       'related_parents',
                       'title_child_no_stop',
                       'content_child_no_stop',
                       'child_numbers',
                       'cbs_link']]

#---------------------------------------#
# Feature creation and model prediction #
#---------------------------------------#
# Indexation step
indexer = recordlinkage.Index()
indexer.add(Full())
candidate_links = indexer.index(parents, new_child)

# Comparison step - creation of all possible matches
compare_cl = recordlinkage.Compare()
compare_cl.string('link', 'cbs_link', method='jarowinkler', threshold=0.93, label='feature_link_score')
features = compare_cl.compute(candidate_links, parents, new_child)
features.reset_index(inplace=True)

# Add extra data of parents and new_child to feature table and rename conflicting columns
features.loc[:, 'child_id'] = features.apply(find_id, args=(new_child, 'level_1'), axis=1)
features.loc[:, 'parent_id'] = features.apply(find_id, args=(parents, 'level_0'), axis=1)
features = features.merge(parents, left_on='parent_id', right_on='id', how='left')
features = features.merge(new_child, left_on='child_id', right_on='id', how='left')
features.drop(columns=['level_0', 'level_1', 'id_x', 'id_y'], inplace=True)
features.rename(columns={'title_x': 'title_parent',
                         'content_x': 'content_parent',
                         'publish_date_date_x': 'publish_date_date_parent',
                         'title_y': 'title_child',
                         'content_y': 'content_child',
                         'publish_date_date_y': 'publish_date_date_child'}, inplace=True)

#-------------------------------#
# Rules before the actual model #
#-------------------------------#
# Check if the whole CBS title exists in child article
features['feature_whole_title'] = features.apply(find_title, axis=1)

# If CBS link or whole CBS title is found in child, match_probability = 1
if (features['feature_whole_title'].sum() > 0) | (features['feature_link_score'].sum() > 0):
    features['predicted_match'] = features['feature_whole_title'] + features['feature_link_score']
    # sort results
    features.sort_values(by=['predicted_match'], ascending=False, inplace=True)

    # final DF
    to_return = features[['child_id', 'parent_id', 'predicted_match']]
    to_return['predicted_match'] = to_return['predicted_match'].clip(0, 1)
    to_return.loc[:, 'predicted_match'] = to_return[['predicted_match']].applymap("{0:.4f}".format)

    # save
    to_return[:nr_matches].to_csv(str(path / ('data/c_%s_output.csv' %(child_id))))
    sys.exit("Prediction made based on link and/or title")

#-------------------------------------------------------------#
# No match on pre-model rules? Continue with feature creation #
#-------------------------------------------------------------#
# Check the CBS sleutelwoorden and the Synonyms
features[['sleutelwoorden_jaccard', 'sleutelwoorden_lenmatches', 'sleutelwoorden_matches']] = features.apply(find_sleutelwoorden_UF, axis=1)
features.loc[features['taxonomies'].isnull(), ['sleutelwoorden_jaccard', 'sleutelwoorden_lenmatches']] = 0

# Check the broader terms and top terms
features[['BT_TT_jaccard', 'BT_TT_lenmatches', 'BT_TT_matches']] = features.apply(find_BT_TT, axis=1)
features.loc[features['BT_TT'].isnull(), ['BT_TT_jaccard', 'BT_TT_lenmatches']] = 0

# Check the CBS title without stopwords
features[['title_no_stop_jaccard', 'title_no_stop_lenmatches', 'title_no_stop_matches']] = features.apply(find_title_no_stop, axis=1)

# Check the first paragraph of the CBS content without stopwords
features[['1st_paragraph_no_stop_jaccard', '1st_paragraph_no_stop_lenmatches', '1st_paragraph_no_stop_matches']] = features.apply(find_1st_paragraph_no_stop, axis=1)
features.loc[features['first_paragraph_without_stopwords'].isnull(), ['1st_paragraph_no_stop_jaccard', '1st_paragraph_no_stop_lenmatches']] = 0

# Determine the date score
features['date_diff_days'] = abs(features['publish_date_date_parent']-features['publish_date_date_child']).dt.days.astype(float)
offset = 0
scale = 7
features['date_diff_score'] = features.apply(date_comparison, args=(offset, scale), axis=1)

# Check all the CBS numbers
#features['child_numbers'] = features.apply(regex,args=('content_child',),axis=1)
features[['numbers_jaccard', 'numbers_lenmatches', 'numbers_matches']] = features.apply(find_numbers, axis=1)

# Determine the title and content similarity
features[['title_similarity', 'content_similarity']] = features.apply(similarity, args=(nlp, ), axis=1)

# Sum all jaccard scores
features['jac_total'] = features['sleutelwoorden_jaccard']+\
                 features['BT_TT_jaccard']+\
                 features['title_no_stop_jaccard']+\
                 features['1st_paragraph_no_stop_jaccard']+\
                 features['numbers_jaccard']

# Define date_binary variable
features.loc[features['date_diff_days'] < 2, 'date_binary'] = 1
features.loc[features['date_diff_days'] >= 2, 'date_binary'] = 0

#----------------------------------------------#
# Loading, predicting and writing final output #
#----------------------------------------------#
# load the model from disk
loaded_model = pickle.load(open(str(path / 'model/eindmodel_rf_4depth.pkl'), 'rb'))

# Select relevant columns and predict
feature_cols = ['date_binary',
                'jac_total',
                'title_similarity',
                'content_similarity',
                'sleutelwoorden_lenmatches',
                'BT_TT_lenmatches',
                'title_no_stop_lenmatches',
                '1st_paragraph_no_stop_lenmatches',
                'numbers_lenmatches']

to_predict = features[feature_cols]
to_predict = to_predict.fillna(0)
y_proba = loaded_model.predict_proba(to_predict)

features.loc[:, 'predicted_nomatch'] = y_proba[:, 0]
features.loc[:, 'predicted_match'] = y_proba[:, 1]

# sort results
features.sort_values(by=['predicted_match'], ascending=False, inplace=True)

# final DF
to_return = features[['child_id', 'parent_id', 'predicted_match']]

# save
to_return[:nr_matches].to_csv(str(path / ('data/c_%s_output.csv' %(child_id))),
         index = False, 
         header = ['c','p','%'],
         float_format='%.4f')
