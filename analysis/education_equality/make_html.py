import json
import os
from typing import Optional

def generate_embeddable_html(
    json_filepath: str, 
    output_filepath: str = 'final_embed_for_google_sites.html',
    plot_title: Optional[str] = ""
):
    """
    Reads a Vega-Lite/Altair JSON specification file and generates a 
    single, self-contained HTML file suitable for embedding.
    
    This version applies explicit padding to the Vega-Lite specification 
    on both the left (Y-axis fix) and the right (Legend fix) to prevent 
    clipping.
    """
    altair_json_spec = ""
    modified_json_spec = ""
    
    # Define generous padding for the sides
    Y_AXIS_PADDING = 80  # Left padding for Y-axis labels
    LEGEND_PADDING = 50  # Right padding for the legend

    try:
        # 1. Load the Altair JSON specification
        with open(json_filepath, 'r') as f:
            altair_json_spec = f.read().strip()
            
        if not altair_json_spec:
            print(f"Warning: JSON specification loaded from '{json_filepath}' is empty.")
            modified_json_spec = '{"error": "JSON file was empty."}'
        else:
            # 2. Parse the JSON and inject the explicit padding configuration
            spec_dict = json.loads(altair_json_spec)
            
            # --- CRITICAL FIX: Explicitly set padding within the VL spec ---
            # Increase left padding (Y-axis) and right padding (Legend)
            spec_dict['padding'] = {
                'left': Y_AXIS_PADDING,
                'top': 10,
                'right': LEGEND_PADDING,
                'bottom': 10
            }
            # ---------------------------------------------------------------

            # Ensure autosize is set to fit the container or responsive by default
            if 'autosize' not in spec_dict:
                 spec_dict['autosize'] = 'fit'

            modified_json_spec = json.dumps(spec_dict)
            print(f"Successfully loaded and modified JSON specification with padding: Left={Y_AXIS_PADDING}px, Right={LEGEND_PADDING}px.")

    except FileNotFoundError:
        print(f"Error: JSON file not found at {json_filepath}. Creating HTML with error message.")
        modified_json_spec = '{"error": "JSON file not found. Check Python script execution."}'

    except Exception as e:
        print(f"An unexpected error occurred while reading or modifying the JSON file: {e}")
        modified_json_spec = '{"error": "Unknown error during JSON processing."}'


    # 3. Define the HTML template
    # The modified JSON content is INJECTED here.
    html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Embedded Altair Plot</title>
    <!-- Load required libraries from CDNs -->
    <script src="https://cdn.jsdelivr.net/npm/vega@5.21.0/build/vega.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/vega-lite@5.2.0/build/vega-lite.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/vega-embed@6.20.2/build/vega-embed.min.js"></script>
    
    <style>
        /* CSS container provides centering and a safe zone */
        body {{
            font-family: 'Inter', sans-serif;
            margin: 0; 
            padding: 0; 
            background-color: transparent;
            display: flex;
            justify-content: center;
            align-items: flex-start;
            min-height: initial;
        }}
        .chart-container {{
            /* Increased max-width to 800px to give more room for chart and legend */
            max-width: 800px; 
            width: 100%;
            padding: 16px; 
            margin: 0 auto; 
            box-sizing: border-box;
            background-color: transparent;
        }}
        h1 {{
            text-align: center;
            color: #1e3a8a;
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 10px; 
            margin-top: 5px; 
        }}
        #vis {{
            /* Ensure the visualization div is centered within the container */
            width: 100%;
            display: flex;
            justify-content: center;
            align-items: center;
            overflow-x: auto; 
        }}
        .error-message {{
            color: #b91c1c; 
            padding: 10px; 
            border: 1px solid #fca5a5;
            background-color: #fee2e2;
            border-radius: 8px;
            font-weight: 600;
            text-align: center;
        }}
    </style>
</head>
<body>

<div class="chart-container">
    <h1>{plot_title}</h1>
    <div id="vis"></div>
</div>

<script>
    // The Vega-Lite specification (with injected fixed padding) is used here
    const vega_lite_spec_string = `{modified_json_spec}`;

    // Function to render the plot using Vega-Embed
    function renderPlot() {{
        const visContainer = document.getElementById('vis');
        
        if (!window.vegaEmbed) {{
             visContainer.innerHTML = '<div class="error-message">FATAL ERROR: Vega-Embed library failed to load. This usually happens when opening the HTML file locally due to security restrictions. Try embedding it in Google Sites.</div>';
             return;
        }}
        
        if (vega_lite_spec_string.includes('"error"')) {{
             // Display Python-side errors
             visContainer.innerHTML = '<div class="error-message">PLOT DATA ERROR: The Altair JSON file was likely not found or was empty. Please run your plotting script first.</div>';
             return;
        }}
        
        try {{
            const spec = JSON.parse(vega_lite_spec_string);
            
            const options = {{
                actions: false, // Disables the action menu (three dots icon)
                defaultStyle: false 
            }};
            
            // The padding fix is applied in the JSON (spec) itself.
            vegaEmbed("#vis", spec, options)
                .then(result => {{
                    console.log("Vega-Lite plot rendered successfully with explicit left and right padding fix.");
                }})
                .catch(error => {{
                    visContainer.innerHTML = '<div class="error-message">RENDER ERROR: Vega-Embed failed. This can happen if the JSON structure is invalid. Console log: ' + error.message + '</div>';
                    console.error("Error rendering Vega-Lite plot:", error);
                }});
                
        }} catch (e) {{
            // Catch JSON parsing errors
            visContainer.innerHTML = '<div class="error-message">CRITICAL ERROR: Failed to parse the Altair specification JSON string. Please check the JSON file for syntax errors.</div>';
            console.error("Invalid JSON content:", e);
        }}
    }}

    // Call the render function when the window loads
    window.onload = renderPlot;
</script>

</body>
</html>
"""
    # 4. Write the HTML content to the output file
    try:
        with open(output_filepath, 'w') as f:
            f.write(html_template.strip()) 
        print(f"Success! HTML file generated at: {os.path.abspath(output_filepath)}")
        print("\n*** IMPORTANT: If the plot still doesn't show locally, proceed directly to Google Sites embedding. ***")

    except Exception as e:
        print(f"Error writing HTML file: {e}")