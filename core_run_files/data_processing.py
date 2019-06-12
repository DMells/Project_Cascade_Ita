import pandas as pd
import os
from fuzzywuzzy import fuzz
from tqdm import tqdm
import numpy as np
from Regions.Italy.Regional_Run_Files import org_suffixes
import string


def clean_source_data(region_dir, directories, in_args):
    """
	Takes the source data file as input, org type suffixes are replaced with abbreviated versions
	and strings reformatted for consistency across the two datasets

	:return df: the amended source datafile
	"""
    raw_data = directories['raw_dir'].format(region_dir) + directories['raw_src_data'].format(in_args.src_raw_name)
    adj_data = directories['adj_dir'].format(region_dir) + directories['adj_src_data'].format(in_args.src_adj_name)

    if not os.path.exists(adj_data):
        df = pd.read_csv(raw_data, usecols=['id', 'source_name', 'source_streetadd'],
                         dtype={'source_name': np.str, 'source_streetadd': np.str})
        df.rename(columns={'source_name': 'src_name', 'source_streetadd': 'src_address'}, inplace=True)
        print("Re-organising source data...")

        # Remove punctuation and double spacing in name
        adj_col = str('src_name_adj')
        orig_col = str('src_name')
        df = remvPunct(df, orig_col, adj_col)

        # Replace organisation suffixes with standardised version
        df[adj_col].replace(org_suffixes.org_suffixes_dict, regex=True, inplace=True)

        # Remove punctuation and double spacing in address
        adj_col = str('src_address_adj')
        orig_col = str('src_address')

        df = remvPunct(df, orig_col, adj_col)
        df = remvStreetNumber(df, adj_col)

        df = joinfields(df, 'src')

        print("...done")
        df.to_csv(adj_data, index=False)
    else:
        # Specify usecols and  dtypes to prevent mixed dtypes error and remove 'unnamed' cols:
        df = pd.read_csv(adj_data, usecols=['id', 'src_name', 'src_name_adj', 'src_address','src_address_adj'],
                         dtype={'id': np.str, 'src_name': np.str, 'src_address': np.str, 'src_name_adj': np.str, 'src_address_adj': np.str, 'srcjoinfields':np.str})
    return df


def clean_registry_data(region_dir, directories, in_args):
    """
	Takes the raw registry data file and splits into chunks.
	Multiple address columns are merged into one column,
	org type suffixes are replaced with abbreviated versions and strings reformatted for consistency across the two datasets

	:return dffullmerge: the registry dataframe adjusted as above
	"""

    raw_data = directories['raw_dir'].format(region_dir) + directories['raw_reg_data'].format(in_args.reg_raw_name)
    adj_data = directories['adj_dir'].format(region_dir) + directories['adj_reg_data'].format(in_args.reg_adj_name)

    if not os.path.exists(adj_data):
        print("Re-organising registry data...")
        df = pd.read_csv(raw_data,
                         usecols={'reg_name', 'street_address1', 'street_address2', 'street_address3', 'reg_id'},
                         dtype={'reg_name': np.str, 'street_address1': np.str, 'street_address2': np.str,
                                'street_address3': np.str, 'reg_id': np.str},
                         chunksize=500000)

        dffullmerge = pd.DataFrame([])
        for chunk in df:

            # Remove punctuation and double spacing
            adj_col = str('reg_name_adj')
            orig_col = str('reg_name')
            chunk = remvPunct(chunk, orig_col, adj_col)

            # Replace organisation suffixes with standardised version
            chunk[adj_col].replace(org_suffixes.org_suffixes_dict, regex=True, inplace=True)

            ls = []
            # Merge multiple address columns into one column
            for idx, row in tqdm(chunk.iterrows()):
                ls.append(tuple([row['reg_id'], row['reg_name'], row['reg_name_adj'], row['street_address1']]))
                for key in ['street_address2', 'street_address3']:
                    if pd.notnull(row[key]):
                        ls.append(tuple([row['reg_id'], row['reg_name'], row['reg_name_adj'], row[key]]))
            labels = ['reg_id', 'reg_name', 'reg_name_adj', 'street_address']

            dfmerge = pd.DataFrame.from_records(ls, columns=labels)

            dfmerge.rename(columns={'street_address': 'reg_address'}, inplace=True)

            # Remove punctuation and double spacing in address
            adj_col = str('reg_address_adj')
            orig_col = str('reg_address')
            dfmerge = remvPunct(dfmerge, orig_col, adj_col)
            dfmerge = remvStreetNumber(dfmerge, adj_col)
            dfmerge = joinfields(dfmerge, 'reg')

            dffullmerge = pd.concat([dffullmerge, dfmerge], ignore_index=True)
        dffullmerge.drop_duplicates(inplace=True)
        print("...done")

        dffullmerge.to_csv(adj_data, index=False)


def joinfields(df, dftype):
    '''
    Join adjusted name and address strings into single column to be able to calculate levenshtein distance and thereby name and address matches
    :param df: dataframe (registry or source)
    :return: df
    '''

    df[''.join([str(dftype),'joinfields'])] = df[''.join([str(dftype),'_name_adj'])] + ' ' + df[''.join([str(dftype),'_address_adj'])]
    return df


def remvPunct(df, orig_col, adj_col):
    """
    :param df: dataframe
    :param orig_col: the original unmodified organisation data strings
    :param adj_col: the orig_col with removed punctuation and standardised org_suffixes
    :return: adjusted dataframe
    """
    df[adj_col] = df[orig_col].str.translate(
        str.maketrans({key: None for key in string.punctuation})).str.replace("  ", " ").str.lower().str.strip()
    return df


def remvStreetNumber(df, adj_col):
    df[adj_col] = df[adj_col].str.replace('\d+', '').str.strip()
    return df


def shorten_name(row):
    """
	Removes the company suffixes according to the org_suffixes.org_suffixes_dict. This helps with the extraction phase
	because it improves the relevance of the levenshtein distances.

	:param row: each row of the dataframe
	:return row: shortened string i.e. from "coding ltd" to "coding"
	"""
    row = str(row).replace('-', ' ').replace("  ", " ").strip()
    rowsplit = str(row).split(" ")
    for i in rowsplit:
        if i in org_suffixes.org_suffixes_dict.values():
            rowadj = row.replace(i, '').replace("  ", " ").strip()
    try:
        return rowadj
    except:
        return row


def assign_reg_data_to_clusters(df, assigned_file=None):
    """
	Unmatched members of a cluster are assigned the registry data of the highest-confidence matched
	row in that cluster. At this stage the amount of confidence is irrelevant as these will be measured
	by the levenshtein distance during the match extraction phase.

	:param df: the main clustered and matched dataframe
	:param assigned_file : file-path to save location
	:return altered df
	"""

    df.sort_values(by=['Cluster ID'], inplace=True, axis=0, ascending=True)
    df.reset_index(drop=True, inplace=True)
    tqdm.pandas()
    print("Assigning close matches within clusters...")
    df = df.groupby(['Cluster ID']).progress_apply(get_max_id)
    df.to_csv(assigned_file, index=False)
    return df


def get_max_id(group):
    """
	Used by assign_reg_data_to_clusters(). Takes one entire cluster,
	finds the row with the best confidence score and applies the registry data of that row
	to the rest of the rows in that cluster which don't already have matches

	:param group: all rows belonging to one particular cluster
	:return group: the amended cluster to be updated into the main df
	"""
    max_conf_idx = group['Confidence Score'].idxmax()
    for index, row in group.iterrows():
        # If the row is unmatched (has no registry reg_id):
        if pd.isnull(row.reg_id):
            group.at[index, 'reg_id'] = group['reg_id'][max_conf_idx]
            group.at[index, 'reg_name_adj'] = group['reg_name_adj'][max_conf_idx]
            group.at[index, 'reg_name'] = group['reg_name'][max_conf_idx]
            group.at[index, 'reg_address'] = group['reg_address'][max_conf_idx]
    return group


def calc_match_ratio(row):
    """
	Used in extractMatches() - use fuzzywuzzy to calculate levenshtein distance

	:return ratio: individual levenshtein distance between the registry and source org string
	"""
    if pd.notnull(row.src_name_short) and pd.notnull(row.reg_name_short):
        if pd.notnull(row.src_address_adj) and pd.notnull(row.reg_address_adj):
            return fuzz.ratio(row.src_name_short, row.reg_name_short), fuzz.ratio(row.srcjoinfields, row.regjoinfields)
    if pd.notnull(row.src_name_short) and pd.notnull(row.reg_name_short):
        return fuzz.ratio(row.src_name_short, row.reg_name_short), 0


def add_lev_dist(clust_df, output_file=None):
    '''
    Adds the levenshtein distance ratio comparing the amount of change required to convert the source org name
    to the registry org name and therefore a measure of the quality of the match

    :param clust_df: the clustered datafile
    :param output_file: clustered file with added levenshtein distance
    :return: clust_df
    '''
    # Remove company suffixes for more relevant levenshtein distance calculation. Otherwise will have exaggerated
    # Distances if i.e. src name has 'srl' suffix but reg name doesn't.
    clust_df['src_name_short'] = clust_df.src_name_adj.apply(shorten_name)

    clust_df['reg_name_short'] = clust_df.reg_name_adj.apply(shorten_name)

    # Add column containing levenshtein distance between the matched registry & source org names
    if 'leven_dist_N' not in clust_df.columns:
        clust_df['leven_dist_N'], clust_df['leven_dist_NA'] = zip(*clust_df.apply(calc_match_ratio, axis=1))

    clust_df.to_csv(output_file, index=False)

    return clust_df
