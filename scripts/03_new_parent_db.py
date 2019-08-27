#%%
import pandas as pd
from pathlib import Path
from datetime import date
import argparse

from project_functions import preprocessing_parent
from project_variables import project_path,\
                              all_parents_location

path = Path(project_path)

# Read arguments
my_parser = argparse.ArgumentParser(description='Remake the parent database based on rawparents. OVERWRITES all_parents.csv')
my_parser.add_argument('filename',
                       type=str,
                       help='Filename of the raw parents csv, relative to the project path specified in project_variables')
args = my_parser.parse_args()
parents_filename = args.filename

#all_parents = pd.read_csv(str(path / 'data/rawparents/rawparents.csv'))
all_parents = pd.read_csv(str(path / parents_filename))

# Remove parents older than 2 years
today = date.today()
year = str(int(today.strftime("%Y"))-2)
d1 = year+today.strftime("-%m-%d")
all_parents = all_parents[all_parents['publish_date_date']>d1]

# For previous parents, keep only the ones with children and where there is content
all_parents.dropna(subset=['related_children'],inplace=True)
all_parents.dropna(subset=['content'],inplace=True)

# Do the preprocessing, find sleutelwoorden and numbers etc
all_parents = preprocessing_parent(all_parents) 

# Remove all statline parents, not matchable yet. 
all_parents = all_parents[all_parents['title'].str.contains('statline') == False]

# Select useful columns
all_parents = all_parents[['id',
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

all_parents.to_csv(str(path / all_parents_location))

print('Done with script. Max parents id = ',all_parents['id'].max())