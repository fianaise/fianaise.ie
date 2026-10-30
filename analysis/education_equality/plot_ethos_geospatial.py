import pandas as pd
import folium
from folium.plugins import MarkerCluster
import os
import numpy as np
import hashlib 

# --- Constants & Configuration ---
TARGET_SHEET_NAME = "Mainstream Schools"

# Define the columns used in the sheet
SCHOOL_NAME_COL = 'Official Name'
ETHOS_COL = 'Ethos Description'
LAT_COL = 'School Latitude'
LON_COL = 'School Longitude'

# Address columns (for popup)
ADDRESS_COLS = ['Address (Line 1)', 'Address (Line 2)', 'Address (Line 3)', 'Address (Line 4)', 'County Description', 'Eircode']
DEDUPLICATION_COLS = [SCHOOL_NAME_COL, LAT_COL, LON_COL] 

IRELAND_CENTER = [53.5, -8.0]
MAP_ZOOM = 7

# **New Constant for Responsive Size**
# Radius in meters for the folium.Circle object. Adjust this value (e.g., 50 to 100) 
# to change the size of the dots at a given zoom level.
RESPONSIVE_DOT_RADIUS_METERS = 75 

# Color palette for common Ethos groups (These remain fixed and distinct)
ETHOS_COLORS = {
    'Catholic': '#3366CC',             # Blue
    'Multi-denominational': '#33CC66',     # Green
    'Church of Ireland': '#CC3333',       # Red
    'Interdenominational': '#FF9900',     # Orange
    'Community National School': '#A020F0', # Purple
    'Educate Together': '#009999',        # Teal/Cyan
    'Presbyterian': '#800000',           # Maroon
    'Other': '#778899',
    'Unknown/Missing': '#000000'
}

# Dictionary to cache dynamically generated colors
DYNAMIC_ETHOS_COLORS = {}

def get_ethos_color(ethos: str) -> str:
    """
    Returns a unique color based on the school's ethos.
    """
    ethos = str(ethos).strip()
    
    if pd.isna(ethos) or not ethos:
        return ETHOS_COLORS['Unknown/Missing']
    
    for key, color in ETHOS_COLORS.items():
        if key.lower() in ethos.lower():
            return color
            
    if ethos in DYNAMIC_ETHOS_COLORS:
        return DYNAMIC_ETHOS_COLORS[ethos]

    hash_object = hashlib.sha1(ethos.encode('utf-8'))
    hex_digest = hash_object.hexdigest()
    
    generated_color = '#' + hex_digest[:6] 
    DYNAMIC_ETHOS_COLORS[ethos] = generated_color
    
    return generated_color


def patronage_current_config(INPUT_FILE, OUTPUT_MAP_FILE):
    """
    Loads 'Mainstream Schools' data, cleans it, removes duplicates, and generates an 
    interactive Folium map with individual small circular markers that scale with zoom, 
    organized into toggleable layers by Ethos.
    """
    if not os.path.exists(INPUT_FILE):
        print(f"FATAL ERROR: Input file '{INPUT_FILE}' not found.")
        return

    # --- 1. Data Loading, Cleaning, & Deduplication ---
    try:
        df = pd.read_excel(INPUT_FILE, sheet_name=TARGET_SHEET_NAME, header=1)
        df.columns = df.columns.str.strip()
    except Exception as e:
        print(f"FATAL ERROR: Could not read input file. Error: {e}")
        return

    df[LAT_COL] = pd.to_numeric(df[LAT_COL], errors='coerce')
    df[LON_COL] = pd.to_numeric(df[LON_COL], errors='coerce')
    df.dropna(subset=[LAT_COL, LON_COL], inplace=True) 
    
    initial_count = len(df)
    df.drop_duplicates(subset=DEDUPLICATION_COLS, keep='first', inplace=True)
    
    df['Cleaned Ethos'] = df[ETHOS_COL].fillna('Unknown/Missing').astype(str).str.strip()
    
    # --- 2. Setup Folium Map and Feature Groups ---
    
    m = folium.Map(location=IRELAND_CENTER, zoom_start=MAP_ZOOM, tiles="cartodbpositron",
                   control_scale=True, max_bounds=True)
    
    unique_ethos_types = sorted(list(df['Cleaned Ethos'].unique()))
    most_common_ethos = df['Cleaned Ethos'].value_counts().idxmax()
    ethos_layers = {}
    
    # Create FeatureGroups for toggling
    for ethos in unique_ethos_types:
        is_default_visible = (ethos == most_common_ethos)
        ethos_layers[ethos] = folium.FeatureGroup(
            name=ethos, 
            show=is_default_visible
        ).add_to(m)

    # --- 3. Iterate and Add Responsive Markers (folium.Circle) ---
    
    for idx, row in df.iterrows():
        lat = row[LAT_COL]
        lon = row[LON_COL]
        ethos = row['Cleaned Ethos']
        school_name = row[SCHOOL_NAME_COL]
        
        marker_color = get_ethos_color(ethos) 
        target_layer = ethos_layers[ethos]

        # Create popup content
        address_parts = [str(row[col]).strip() for col in ADDRESS_COLS if col in row and pd.notna(row[col]) and str(row[col]).strip().lower() != 'nan']
        full_address = ', '.join(address_parts)
        popup_html = f"<strong>{school_name}</strong><br><strong>Ethos:</strong> <span style='color: {marker_color};'>{ethos}</span><br><strong>Address:</strong> {full_address}"

        # 🌟 CHANGE: Use folium.Circle with radius in meters for zoom responsiveness
        folium.Circle(
            location=[lat, lon],
            radius=RESPONSIVE_DOT_RADIUS_METERS, # Radius is in meters, so it scales with zoom
            popup=folium.Popup(popup_html, max_width=300),
            color=marker_color,     
            fill=True,
            fill_color=marker_color,
            fill_opacity=0.7,       
            weight=1                
        ).add_to(target_layer)
        
    # --- 4. Add Legend and Layer Control ---

    ethos_legend_html = ''
    for ethos in unique_ethos_types:
        color = get_ethos_color(ethos) 
        ethos_legend_html += f'<li><span style="display:inline-block; width:12px; height:12px; background-color:{color}; border-radius:3px; border: 1px solid #555;"></span> {ethos}</li>'
            
    legend_title = 'School Ethos Colors'
    legend = folium.Element(f"""
        <div style='position: fixed; 
                    bottom: 50px; left: 50px; width: 250px; max-height: 400px; 
                    overflow-y: scroll; border:2px solid grey; z-index:9999; font-size:14px;
                    background-color: white; opacity: 0.9; padding: 5px; border-radius: 5px;'>
            <h4 style='text-align: center; margin-top: 5px;'>{legend_title} ({len(unique_ethos_types)} Types)</h4>
            <ul style='list-style: none; padding-left: 10px; margin-bottom: 5px;'>
                {ethos_legend_html}
            </ul>
        </div>
    """)
    m.get_root().html.add_child(legend)
    
    folium.LayerControl(collapsed=False).add_to(m) 

    # --- 5. Save the Map ---
    output_dir = os.path.dirname(OUTPUT_MAP_FILE)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    m.save(OUTPUT_MAP_FILE)
    print(f"\nSUCCESS: Interactive map saved to '{OUTPUT_MAP_FILE}'. Open this file in your browser.")
    print("The dot size now scales with the zoom level.")


if __name__ == '__main__':
    create_school_map()