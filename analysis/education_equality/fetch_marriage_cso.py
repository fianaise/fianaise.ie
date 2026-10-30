import pandas as pd
import requests
import io
import time
import os
import sys

# The PxStat API endpoint for the Census of Population data on Opposite-Sex Marriages by Form of Ceremony.
PXSTAT_API_URL = "https://ws.cso.ie/public/api.restful/PxStat.Data.Cube_API.ReadDataset/VSA44/CSV/1.0/en"

def fetch_cso_marriage_data_agg(url: str, filename: str):
    """
    Fetches Opposite-Sex Marriage data from the CSO PxStat API,
    processes it for visualization, and saves it to a CSV file.

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
            # This handles columns with leading/trailing spaces in the original data
            df.columns = df.columns.str.strip()
            
            # Identify and rename the VALUE column (Count)
            value_col = [col for col in df.columns if 'VALUE' in col.upper()][0]
            df.rename(columns={value_col: 'Number of Marriages'}, inplace=True)

            # 2. Clean and filter the data: keep only 'State' and filter out 'All ceremonies' rows
            df_filtered = df[
                (df['Province County and City'].str.contains('State', case=False)) &
                (~df['Form of Ceremony'].str.contains('All ceremonies', case=False))
            ].copy()
            
            # calculate the percantage of each religion in each year
            df_filtered['Percentage'] = df_filtered.groupby('Year')['Number of Marriages'].transform(lambda x: (x / x.sum()) * 100)

            if df_filtered.empty:
                print("Error: Final marriage data is empty after cleaning and filtering.")
                return

            # 3. Save to CSV
            df_filtered.to_csv(filename, index=False)
            print(f"\nSuccessfully saved census marriage data to {filename}")
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
    OUTPUT_FILE = "ireland_marriage_data_agg.csv"
    OUTPUT_FILEPATH = os.path.join('../data', OUTPUT_FILE)
    fetch_cso_marriage_data_agg(PXSTAT_API_URL, OUTPUT_FILEPATH)