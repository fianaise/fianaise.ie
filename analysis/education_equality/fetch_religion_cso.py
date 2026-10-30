import pandas as pd
import requests
import io
import time
import sys
import os

# The PxStat API endpoint for the Census of Population data on Religion, Age Group and Sex.
PXSTAT_API_URL = "https://ws.cso.ie/public/api.restful/PxStat.Data.Cube_API.ReadDataset/F5071/CSV/1.0/en"

def fetch_cso_religion_data_agg(url: str, filename: str):
    """
    Fetches Census of Population data on religion from the CSO PxStat API,
    filters for national totals, calculates percentages, and saves it to a CSV file.

    Args:
        url (str): The PxStat API URL for the data (CSV format).
        filename (str): The name of the output CSV file.
    """
    print(f"Attempting to download data from CSO PxStat API: {url}")

    max_retries = 5
    initial_delay = 1
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            print(f"Download successful (Attempt {attempt + 1})")
            
            data = io.StringIO(response.content.decode('utf-8'))
            df = pd.read_csv(data)
            
            # --- Data Processing Steps ---

            # 1. Standardize and Rename key columns
            df.columns = df.columns.str.strip()
            
            year_col_found = False
            for col in df.columns:
                if 'TLIST' in col.upper():
                    df.rename(columns={col: 'Year'}, inplace=True)
                    year_col_found = True
                    break
            
            if not year_col_found and 'Year' not in df.columns:
                print("Error: Could not find 'Year' column (expected 'Year' or a column containing 'TLIST').")
                return

            for col in ['Religion', 'Age Group', 'Sex', 'Year']:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.strip()

            # 2. Filter for National Total (All Age Groups, Both Sexes) and filter out "All religions"
            df_filtered = df[
                (df['Age Group'].str.contains('All ages', case=False)) &
                (df['Sex'].str.contains('Both sexes', case=False)) &
                (df['Religion'] != 'All religions')

            ].copy()
            
            if df_filtered.empty:
                print("Error: After filtering for 'All age groups' and 'Both sexes', the DataFrame is empty.")
                return
            
            # 
            # calculate the percantage of each religion in each year
            df_filtered['Percentage'] = df_filtered.groupby('Census Year')['VALUE'].transform(lambda x: (x / x.sum())*100)

            # 6. Save to CSV
            df_filtered.to_csv(filename, index=False)
            print(f"\nSuccessfully saved census religion data to {filename}")
            return

        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt)
                time.sleep(delay)
            else:
                print(f"Failed to fetch data after {max_retries} attempts.")
                raise
        except Exception as e:
             print(f"An unexpected error occurred during processing: {e}", file=sys.stderr)
             raise
        
def fetch_cso_religion_data_ages(url: str, filename: str):
    """
    Fetches Census of Population data on religion from the CSO PxStat API,
    filters for national totals, calculates percentages, and saves it to a CSV file.

    Args:
        url (str): The PxStat API URL for the data (CSV format).
        filename (str): The name of the output CSV file.
    """
    print(f"Attempting to download data from CSO PxStat API: {url}")

    max_retries = 5
    initial_delay = 1
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            print(f"Download successful (Attempt {attempt + 1})")
            
            data = io.StringIO(response.content.decode('utf-8'))
            df = pd.read_csv(data)
            
            # --- Data Processing Steps ---

            # 1. Standardize and Rename key columns
            df.columns = df.columns.str.strip()
            
            year_col_found = False
            for col in df.columns:
                if 'TLIST' in col.upper():
                    df.rename(columns={col: 'Year'}, inplace=True)
                    year_col_found = True
                    break
            
            if not year_col_found and 'Year' not in df.columns:
                print("Error: Could not find 'Year' column (expected 'Year' or a column containing 'TLIST').")
                return

            for col in ['Religion', 'Age Group', 'Sex', 'Year']:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.strip()

            # 2. Filter for all age groups and sexes
            df_filtered = df[
                (~df['Age Group'].str.contains('All ages', case=False)) &
                (df['Sex'].str.contains('Both sexes', case=False)) &
                (df['Religion'] != 'All religions')

            ].copy()
            
            if df_filtered.empty:
                print("Error: After filtering for 'All age groups' and 'Both sexes', the DataFrame is empty.")
                return
            
            # calculate the percantage of each religion in each year for each age and sex
            df_filtered['Percentage'] = df_filtered.groupby(['Census Year', 'Age Group'])['VALUE'].transform(lambda x: (x / x.sum())*100)

            # 6. Save to CSV
            df_filtered.to_csv(filename, index=False)
            print(f"\nSuccessfully saved census religion data to {filename}")
            return

        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt)
                time.sleep(delay)
            else:
                print(f"Failed to fetch data after {max_retries} attempts.")
                raise
        except Exception as e:
             print(f"An unexpected error occurred during processing: {e}", file=sys.stderr)
             raise
        
def fetch_cso_religion_data_sex(url: str, filename: str):
    """
    Fetches Census of Population data on religion from the CSO PxStat API,
    filters for national totals, calculates percentages, and saves it to a CSV file.

    Args:
        url (str): The PxStat API URL for the data (CSV format).
        filename (str): The name of the output CSV file.
    """
    print(f"Attempting to download data from CSO PxStat API: {url}")

    max_retries = 5
    initial_delay = 1
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            print(f"Download successful (Attempt {attempt + 1})")
            
            data = io.StringIO(response.content.decode('utf-8'))
            df = pd.read_csv(data)
            
            # --- Data Processing Steps ---

            # 1. Standardize and Rename key columns
            df.columns = df.columns.str.strip()
            
            year_col_found = False
            for col in df.columns:
                if 'TLIST' in col.upper():
                    df.rename(columns={col: 'Year'}, inplace=True)
                    year_col_found = True
                    break
            
            if not year_col_found and 'Year' not in df.columns:
                print("Error: Could not find 'Year' column (expected 'Year' or a column containing 'TLIST').")
                return

            for col in ['Religion', 'Age Group', 'Sex', 'Year']:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.strip()

            # 2. Filter for all age groups and sexes
            df_filtered = df[
                (df['Age Group'].str.contains('All ages', case=False)) &
                (~df['Sex'].str.contains('Both sexes', case=False)) &
                (df['Religion'] != 'All religions')

            ].copy()
            
            if df_filtered.empty:
                print("Error: After filtering for 'All age groups' and 'Both sexes', the DataFrame is empty.")
                return
            
            # calculate the percantage of each religion in each year for each age and sex
            df_filtered['Percentage'] = df_filtered.groupby(['Census Year', 'Sex'])['VALUE'].transform(lambda x: (x / x.sum())*100)

            # 6. Save to CSV
            df_filtered.to_csv(filename, index=False)
            print(f"\nSuccessfully saved census religion data to {filename}")
            return

        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt)
                time.sleep(delay)
            else:
                print(f"Failed to fetch data after {max_retries} attempts.")
                raise
        except Exception as e:
             print(f"An unexpected error occurred during processing: {e}", file=sys.stderr)
             raise

if __name__ == '__main__':
    OUTPUT_FILE = "ireland_religion_census_data_agg.csv"
    fetch_cso_religion_data_agg(PXSTAT_API_URL, os.path.join('../data', OUTPUT_FILE))    

    OUTPUT_FILE = "ireland_religion_census_data_ages.csv"
    fetch_cso_religion_data_ages(PXSTAT_API_URL, os.path.join('../data', OUTPUT_FILE))

    OUTPUT_FILE = "ireland_religion_census_data_sex.csv"
    fetch_cso_religion_data_sex(PXSTAT_API_URL, os.path.join('../data', OUTPUT_FILE))
