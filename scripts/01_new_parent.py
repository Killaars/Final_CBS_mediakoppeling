#%%
import pandas as pd
from pathlib import Path
import argparse

from project_functions import preprocessing_parent
from project_variables import project_path,\
                              all_parents_location

# Read arguments
my_parser = argparse.ArgumentParser(description='Add new parent to parent database')
my_parser.add_argument('parent_id',
                       type=str,
                       help='ID of the new parent article')
args = my_parser.parse_args()

path = Path(project_path)

# Read all parents
all_parents = pd.read_csv(str(path / all_parents_location), index_col=0)

# Read and process new parent
#parent_id = '203989'
parent_id = args.parent_id
new_parent = pd.read_csv(str(path / ('data/p_%s.csv' %(parent_id))), index_col=0)
new_parent = preprocessing_parent(new_parent)

# Add new parent to older parents if not statline
if len(new_parent[new_parent['title'].str.contains('statline') == False])>0:
    all_parents = pd.concat([all_parents, new_parent])
    all_parents.reset_index(drop=True, inplace=True)

# Write parent database
all_parents.to_csv(str(path / all_parents_location))