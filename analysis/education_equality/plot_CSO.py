import altair as alt

def generate_marriage_chart(DATA_FILE, OUTPUT_FILE):
    """
    Loads Ireland marriage data, creates a line chart showing trends by ceremony type,
    enables interactivity, and saves the specification to a JSON file.
    """
    try:
        # Load the data from the specified path/file
        df = pd.read_csv(DATA_FILE)
    except FileNotFoundError:
        print(f"Error: The data file '{DATA_FILE}' was not found.")
        print("Please ensure your CSV file is available at the specified path.")
        return
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    # Use the full DataFrame as requested
    df_plot = df

    # 1. Define the Chart
    chart = alt.Chart(df_plot).mark_line(point=True).encode(
        # X-Axis: Year (Ordinal 'O' for discrete years)
        x=alt.X('Year:O', title='Year'),
        
        # Y-Axis: Percentage (fixed domain 0-100)
        y=alt.Y('Percentage:Q', title='% of Marriages', scale=alt.Scale(domain=[0, 100])),
        
        # Color (Hue): Differentiate the lines by the Form of Ceremony
        color=alt.Color('Form of Ceremony:N', title='Ceremony Type'),
        
        # Tooltips for interactive data inspection
        tooltip=[
            'Year:O', 
            'Form of Ceremony:N', 
            alt.Tooltip('Percentage', format='.3f', title='% of Marriages')
        ]
    ).properties(
        width=700,
        height=400
    ).interactive() # Enable zooming and panning on this single chart

    # 2. Display the chart (for viewing in VS Code)
    chart.show()
    
    # 3. Save the Vega-Lite JSON specification (for embedding)
    chart.save(OUTPUT_FILE)
    
    print("\n--- Generation Complete ---")
    print(f"Altair chart visualized successfully.")
    print(f"Vega-Lite JSON specification saved to: {OUTPUT_FILE}")

# --- Configuration to disable the Action Menu ---
# This must be run before the charts are shown.
def disable_action_menu():
    """Configures Altair to remove the default action menu (Save, View Source, etc.) 
    when the charts are rendered in the viewer."""
    alt.renderers.set_embed_options(
        # The 'actions' dictionary controls the action menu display
        actions=False 
    )
    print("Action menu disabled for chart rendering.")

def create_religion_chart(df: pd.DataFrame, target_religion: str) -> alt.Chart:
    """
    Creates a single, self-contained Altair line chart for the specified religion.
    """
    # Filter the data for the specific religion
    df_plot = df[
        (df['Religion'] == target_religion)
    ].copy()
    
    # Standardize column name
    if 'Percentage of Population' in df_plot.columns and 'Percentage' not in df_plot.columns:
        df_plot.rename(columns={'Percentage of Population': 'Percentage'}, inplace=True)
    
    # Filter out 'All age groups'
    df_plot = df_plot[~df_plot['Age Group'].str.contains('All age groups', case=False, na=False)]
    
    if df_plot.empty:
        return alt.Chart(pd.DataFrame({'x': [], 'y': []})).mark_text(
            text=f"No data available for religion: {target_religion}", 
            color='red'
        ).properties(title=f"Trend for {target_religion}")

    # Define the chart without any concatenation or interaction logic
    chart = alt.Chart(df_plot).mark_line(point=True).encode(
        # X-Axis: Year - using Ordinal ('O') ensures clean categorical display
        x=alt.X('Year:O', title='Census Year'),
        
        # Y-Axis: Percentage (fixed domain 0-100)
        y=alt.Y('Percentage:Q', title='% of Population', scale=alt.Scale(domain=[0, 100])),
        
        # Color (Hue): Differentiate the lines by Age Group
        color=alt.Color('Age Group:N', title='Age Group'),
        
        # Add tooltips for data inspection
        tooltip=[
            'Year:O', 
            'Age Group:N', 
            alt.Tooltip('Percentage', format='.3f', title='% of Pop.')
        ]
    ).properties(
        title=f"{target_religion}",
        width=500, 
        height=400
    )

    return chart


def plot_separate_trends(DATA_FILE, OUTPUT_FILE_CATHOLIC, OUTPUT_FILE_NONE):
    """
    Loads data, configures rendering, creates two independent charts, and calls .show() on each.
    """
    # 0. Apply the configuration change
    disable_action_menu()
    
    try:
        df = pd.read_csv(DATA_FILE)
    except FileNotFoundError:
        print(f"Error: The data file '{DATA_FILE}' was not found.")
        return
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    print("Generating charts...")

    # 1. Create the chart for Roman Catholic
    chart_rc = create_religion_chart(df, 'Roman Catholic')
    
    # 2. Create the chart for No religion
    chart_none = create_religion_chart(df, 'No religion')
    
    # --- DISPLAY AND SAVE ---
    
    # Show the Roman Catholic chart
    print("\nDisplaying Roman Catholic Chart...")
    chart_rc.show()
    
    # Show the No religion chart
    print("\nDisplaying No Religion Chart...")
    chart_none.show()
    
    # The chart specs are saved without the rendering config, so they are still useful
    chart_rc.save(OUTPUT_FILE_CATHOLIC)
    chart_none.save(OUTPUT_FILE_NONE)
    
    print("\n--- Generation Complete ---")
    print("The charts have been displayed without the action menu buttons.")