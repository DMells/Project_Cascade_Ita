## Using the Italian Module

### Initial Set Up & Familiarisation

1. Clone the repo:
```
git clone https://github.com/DMells/Project_Cascade
```

2. Navigate to project directory:
```
cd Project_Cascade
```

3. Clone dedupe (with slight modifications):
```
git clone "https://github.com/DMells/csvdedupe"
```

4. Install with pipenv and activate virtual environment:
```
pipenv install
pipenv shell
```

OR

Install with virtualenv:

```
virtualenv venv -p python3
source venv/bin/activate
pip install -r requirements.txt
```

5. Place the two raw data files into Raw_Data/

6. Run the module
```
python run.py --registry_raw_name 'registry_data_sample.csv'
```
Or rename the sample file to registry_data.csv, which is the default name used when calling. _If no registry datafile is found, the user will be prompted with the option to download it from the remote database._
```
python run.py
```

The module makes use of argument parsing, with the following arguments:
```
--source_raw_name (default: 'source_data.csv')
--registry_raw_name (default: 'registry_data.csv')
--source_adj_name (default: 'source_data_adj.csv')
--registry_adj_name (default: 'registry_data_adj.csv')
--recycle (No parameters)
--training (No parameters)
--config_review (No parameters)
--terminal_matching (No parameters)
--convert_training (No parameters)
--upload_to_db (No parameters)
```

To amend the names if needed :
```
python run.py --source_raw_name <filename>  # ...etc
```

The `--recycle` flag is used once the module has been run and trained for the first time. When this flag is used, the module will run for a second time, but will incorporate the training data obtained from the manual matching process created in the first 'round', as  kick-start of sorts. See 5. Recycling Matches below for more info.

The default file formats are :

##### Source Data
Filename : source_data.csv
Fields : 'id' (int), 'supplier_name' (str), 'supplier_streetadd' (str)

##### Registry Data
Filename : registry_data.csv
Fields : 'org_name', 'street_address1', 'street_address2', 'street_address3', 'Org_ID'

##### Directory Structure

```
Project_Cascade
|--Config_Files
|--csvdedupe
|--Data_Inputs
    |--Adj_Data
    |--Raw_Data
    |--Training_Files
        |--Manual_&_Backups
        |--process_type **  # I.e. Name_Only, or Name_Address
            |--Clustering
            |--Matching
|--Outputs
    |--process_type **  # I.e. Name_Only, or Name_Address
        |--Confirmed_Matches
        |--Deduped_Data
        |--Extracted_Matches
|--run_files
    |--convert_training.py
    |--data_analysis.py
    |--data_matching.py
    |--db_calls.py
    |--org_suffixes.py
    |--setup.py
|--run.py
|--Pipfile
|--Pipfile.lock
|--README.md
```

_** Subject to change/ depending on naming conventions chosen in config files._
## General Processes

### Data Cleaning 
1. The module takes both datafiles and creates a new column with the org name cleaned up to help the matching process. For example, all company type suffixes (ltd, llp, srl etc) are standardised.
2. In the same new column, punctuation is removed.
3. For the registry data set which has several address columns, these are all merged into one, with related row entries duplicated.  

### Deduplication
4.  The dedupe module comes into play next in two stages. First is the matching phase, which joins together our manual source data to the registry data. It does this using [dedupe](https://github.com/dedupeio/csvdedupe)'s `csvlink` command. Training data has been provided to provide the best quality matches, and so you are required to do nothing here, however if you want to modify the training data just use the `training` flag when calling the module:
```
python run.py --training
```
It is recommended that you study the dedupe documentation before modifying the training data, as experimentation is required to prevent over or under-fitting of the matching process. I have provided some notes at the end of this readme to explain my methods.

5. Second, the module takes this matched data and assigns rows into groups called clusters, in the event that two rows within the source data actually refer to the same company. This outputs both a cluster_ID and a confidence score of how likely that row belongs to that cluster.

### Further Data Manipulation
6. We now have our matched and clustered dataset, which means that our source data is now linked to registry/registry data for verification and it is also grouped into clusters so we don't eg: contact the same company twice.
If any data **within a cluster** hasn't been matched to registry data , then if there is a match anywhere within that cluster, that registry data is applied to the rest of the cluster. This is to increase the number of absolute matches. Quality control comes next.

### Extracting the best matches
7. Because of the many different ways of writing a company name, dedupe's matching/clustering phase can only take us so far.
8. We then introduce a Levenshtein distance ratio to the data, which indicates just how good each match is based on the amount of alteration it would require to make one string the same as the other. The higher the score the better.
9. Note that a short string with a difference of 1 letter between it and another string is much less likely to be a match than a long string with the same difference. Based on this, and a pre-defined config file, we introduce a cascading quality filter, which decreases the minimum levenshtein distance we are willing to accept, as the string length increases.
You can add as many config files as you like to experiment with different combinations of this quality control filter system. 
10. A short stats file is created so the user can see high level results of the different config files.
11. The best config file is automatically chosen (based on the highest average Levenshtein distance) **unless** the `-config_review` flag is used when running the module. If this is done, the user will be prompted review the stats file and then enter their preferred config file in the terminal.
12. The program will then exit, allowing the user to review the matches that have been extracted based on the chosen config file. The next stage is to manually review the 'Manual_Matches_x' file within Outputs/X/Confirmed_Matches and enter Y/N/U in the Manual_Match column. All matches with a Levenshtein distance of 100 (i.e. an exact match) are automatically assigned 'Y'. Note that these matches can be verified in the terminal if the `-terminal_matching` flag is used. In this case, the program will not exit, and instead the user will be prompted to verify the matches using the same Y/N/U responses.
13. If the program has exited, we will then do 2 things. The first is to convert these manual confirmed matches into a json training file to be fed back into the system but using more fields in the dedupe phase (see recycling matches section below). The second is to get these confirmed matches uploaded to the database. Do this by running the command:
```
python run.py --convert_training --upload_to_db
```
The new training files are copied into the relevant training folders ready to be called by dedupe, and the confirmed 'Y' matches are converted to a Confirmed_Matches.csv file and then uploaded to the database. At this point duplicates within the database are sought and removed.
### Re-cycling the matches
14. These quality matches (Y), and poor quality matches (N) which have been converted to a json training file, can then be re-fed back into dedupe as a kick-start to more accurate training but now including the street address field. Once the process has completed for the first time, re-run the module using the `recycle` flag:

```
python run.py --recycle
```

This will run the entire process again but will use the new training data and will attempt to match both the organisation name and the address. Note that the old training data is duplicated here, so you can add to the training data for the recycle phase without impacting the initial phase if you wanted to re-run it. 

### Training Notes
#### 1. Matching
The best way to train the matching data is to have a strategy of sorts prior to entering the dedupe phase. The best approach I found was to use the 'Unsure' option liberally. For example, if the two strings are the same but one is clearly an abbreviated version of the other, hit 'Unsure'. Each decision will impact the rest of the training data and therefore the outcome of the matches. Dedupe cannot apply context to the data, and so being strict prevents any 'rules' being learnt that make no sense.

#### 2. Clustering
Clustering here is important because it will affect how much of the matched data will be copied to unmatched, but closely related source data. 

#### 3. Altering the config files
Once the training has complete, this is where the config files come into play, as we are now attempting to verify the best quality matches factoring in that longer strings can have lower levenshtein ratios and still be good matches compared to shorter strings.

Create a new config file as required (must follow the current naming convention) and experiment with the 'char_counts' and 'min_match_score', making sure to increase one as you decrease the other. The module will automatically register additional files and run the process and output the stats to separate csvs for you to compare. These files will be saved in `Outputs/Extracted_Matches`.