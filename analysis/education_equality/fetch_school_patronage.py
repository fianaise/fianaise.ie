import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import sys
import re

# Configuration
TARGET_URL = "https://www.gov.ie/en/department-of-education/collections/primary-schools-enrolment-figures/"
OUT_DIR = '../data'

# Keywords used for robust column identification
ETHOS_KEYWORDS = ['ethos', 'patronage', 'control', 'model']

def extract_year_from_filename(filename: str) -> int | None:
    """
    Extracts a four-digit year (or the later year in a range) from a filename.
    
    Looks for patterns like YYYY, YYYY-YYYY, or YYYY YYYY in the filename.
    Returns the year as an integer, or None if extraction fails.
    """
    # Regex searches for four digits, optionally followed by a space/hyphen and another four digits
    match = re.search(r'(\d{4}[ -]?\d{4}|\d{4})', filename)
    if not match:
        return None
    
    file_year_str = match.group(1).replace('-', '').replace(' ', '')
    
    if len(file_year_str) == 8 and file_year_str.isdigit():
        # If 8 digits (e.g., 20232024), use the later year (2024)
        try:
            return int(file_year_str[4:])
        except ValueError:
            return None
    elif len(file_year_str) == 4 and file_year_str.isdigit():
        # If 4 digits (e.g., 2023)
        try:
            return int(file_year_str)
        except ValueError:
            return None
    return None

def find_relevant_sheets(all_sheets: dict) -> list[str]:
    """
    Identifies sheets that contain 'Ethos' keywords in any cell within the first 20 rows.
    
    Args:
        all_sheets (dict): Dictionary of DataFrames (sheet_name: DataFrame) read from the Excel file.

    Returns:
        list[str]: A list of sheet names that meet the criterion.
    """
    relevant_sheets = []
    ROW_LIMIT = 20 

    for sheet_name, df_raw in all_sheets.items():
        
        # Check 1: Check column headers first (quick check)
        has_ethos_column = any(
            any(k in str(col).strip().lower() for k in ETHOS_KEYWORDS) for col in df_raw.columns
        )
        
        if has_ethos_column:
            relevant_sheets.append(sheet_name)
            continue
        
        # Check 2: Check any cell in the first 20 rows (robust check)
        is_ethos_present = False
        if not df_raw.empty and len(df_raw) > 0:
            try:
                # Read the first N rows, convert to string, strip, and lowercase for searching
                check_df = df_raw.iloc[:min(ROW_LIMIT, len(df_raw))].astype(str)
                check_df = check_df.apply(lambda x: x.str.strip().str.lower())
                
                # Stack to turn the DataFrame into a single Series of all cell values, then search
                if check_df.stack().str.contains('|'.join(ETHOS_KEYWORDS)).any():
                    is_ethos_present = True
            except Exception:
                pass 

        if is_ethos_present:
            relevant_sheets.append(sheet_name)
            
    return relevant_sheets

def download_and_save_excel_files(url: str, out_dir: str) -> list[str]:
    """
    Scrapes the target URL for Excel file links, downloads them, and saves the 
    original Excel files locally. Skips download if the file already exists OR 
    if the file year is before 1990.
    """
    print(f"--- Starting data collection from: {url} ---")
    
    saved_excel_paths = []

    try:
        # 1. Fetch the main webpage content
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # 2. Find all links ending in .xls or .xlsx
        excel_links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.lower().endswith(('.xls', '.xlsx')):
                full_url = requests.compat.urljoin(url, href) if not href.startswith(('http', 'https')) else href
                filename = os.path.basename(full_url).split('?')[0]
                excel_links.append((full_url, filename))

        if not excel_links:
            print("\n❌ No .xls or .xlsx download links found on the page.")
            return []

        print(f"\n✅ Found {len(excel_links)} potential Excel files to process.")
        
        # 3. Process each found Excel file
        for i, (download_url, excel_filename) in enumerate(excel_links):
            print(f"\n--- Checking File {i + 1}/{len(excel_links)}: {excel_filename} ---")
            
            # --- YEAR FILTERING ---
            year = extract_year_from_filename(excel_filename)
            
            # Use 1990 as the cutoff year
            CUTOFF_YEAR = 1990

            if year is not None and year < CUTOFF_YEAR:
                print(f"   🛑 Skipping! File is from {year}, which is before the {CUTOFF_YEAR} cutoff.")
                continue
            
            if year is None:
                 print(f"   ⚠️ Warning: Could not reliably determine year for filtering. Continuing download/check.")
            else:
                 print(f"   [Detected Year: {year}]")

            # --- END YEAR FILTERING ---
            
            save_path = os.path.join(out_dir, excel_filename)
            
            if os.path.exists(save_path):
                # File already exists, skip download
                print(f"   Skipping download. File already exists locally: {save_path}")
                saved_excel_paths.append(save_path)
                continue
                
            # If file does not exist, proceed with download
            try:
                print(f"   Downloading new file...")
                file_response = requests.get(download_url, timeout=30)
                file_response.raise_for_status()
                
                # Save the binary content
                with open(save_path, 'wb') as f:
                    f.write(file_response.content)
                
                saved_excel_paths.append(save_path)
                print(f"   Success! Original Excel file saved to: {save_path}")
                
            except requests.exceptions.RequestException as e:
                print(f"   ⚠️ Warning: Could not download {excel_filename}. Error: {e}")
            except Exception as e:
                print(f"   ⚠️ Warning: An unexpected error occurred while saving {excel_filename}. Error: {e}", file=sys.stderr)

    except requests.exceptions.RequestException as e:
        print(f"Fatal Error: Failed to access the main URL: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)

    print(f"\n--- Download/Check Summary ---")
    print(f"Total Excel files available for processing: {len(saved_excel_paths)}")
    print("--------------------------")
    
    return saved_excel_paths

def identify_relevant_files(excel_file_paths: list[str]):
    """
    Iterates through the downloaded Excel files, reads all sheets, and flags 
    the files that contain relevant 'Ethos' data.
    """
    print("\n--- Starting Ethos Data Identification Phase ---")
    
    relevant_files = {}

    for i, file_path in enumerate(excel_file_paths):
        base_filename = os.path.basename(file_path)
        print(f"\nProcessing File {i+1}/{len(excel_file_paths)}: {base_filename}")
        
        try:
            # Read all sheets from the Excel file, using header=None to read the raw data
            # This is necessary for the robust search logic in find_relevant_sheets
            all_sheets_raw = pd.read_excel(file_path, sheet_name=None, header=None)
            
            # Use the core logic to check which sheets are relevant
            relevant_sheets = find_relevant_sheets(all_sheets_raw)
            
            if relevant_sheets:
                relevant_files[base_filename] = relevant_sheets
                print(f"   ✅ RELEVANT: Found Ethos data in sheet(s): {', '.join(relevant_sheets)}")
            else:
                print("   ❌ NOT RELEVANT: No Ethos data found in any sheet.")
                
        except ValueError as e:
            print(f"   ⚠️ Warning: Could not read Excel file {base_filename}. It might be corrupted or malformed. Error: {e}")
        except Exception as e:
            print(f"   ⚠️ Warning: An unexpected error occurred while processing {base_filename}. Error: {e}", file=sys.stderr)

    print("\n==============================================")
    print(f"FINAL RELEVANT FILE SUMMARY ({len(relevant_files)}/{len(excel_file_paths)}):")
    print("==============================================")
    if relevant_files:
        for filename, sheets in relevant_files.items():
            print(f"- {filename} (Sheets: {', '.join(sheets)})")
    else:
        print("No relevant files containing 'Ethos' data were identified.")
    print("==============================================")


def run_ethos_checker_workflow(url: str):
    """
    Executes the download/save step, then the file identification step.
    """
    # 1. Ensure the output directory exists
    if not os.path.exists(OUT_DIR):
        print(f"Creating output directory: {OUT_DIR}")
        os.makedirs(OUT_DIR)
        
    # 2. Download or check for existing Excel files (now with year filtering)
    excel_files = download_and_save_excel_files(url, OUT_DIR)
    
    # 3. Identify which downloaded files contain the "Ethos" data
    if excel_files:
        identify_relevant_files(excel_files)
    else:
        print("\nSkipping file identification as no relevant Excel files were downloaded or found.")


if __name__ == '__main__':
    run_ethos_checker_workflow(TARGET_URL)