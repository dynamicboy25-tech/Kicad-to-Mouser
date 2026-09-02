import re
import json
import time
import requests
import pandas as pd
import streamlit as st
from io import BytesIO

st.set_page_config(
    page_title="KiCad to Mouser Auto-BOM", page_icon="⚡", layout="wide"
)

st.title("⚡ KiCad PCB to Full Mouser BOM")
st.markdown(
    "Upload your native KiCad PCB file (`.kicad_pcb`) and enter your **Mouser Search API Key**. "
    "The app will extract component part numbers, ping Mouser's database for live pricing, availability, and specs, "
    "and map it exactly to the standard Mouser BOM Excel template."
)

st.info(
    "**Note:** To run this, you need a free [Mouser Search API Key](https://www.mouser.com/en/api-search/)."
)

# Sidebar for inputs
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Mouser Search API Key", type="password")
    uploaded_file = st.file_uploader("Upload .kicad_pcb file", type=["kicad_pcb"])

# API Fetch function
def fetch_mouser_data(part_number, api_key):
    """Hits the Mouser API v2 to retrieve part details."""
    url = f"https://api.mouser.com/api/v2/search/partnumber?apiKey={api_key}"
    payload = {
        "SearchByPartRequest": {
            "mouserPartNumber": str(part_number).strip(),
            "partSearchOptions": "Exact"
        }
    }
    headers = {"Content-Type": "application/json", "accept": "application/json"}
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "SearchResults" in data and "Parts" in data["SearchResults"]:
                parts = data["SearchResults"]["Parts"]
                if parts and len(parts) > 0:
                    return parts[0]  # Return the best exact match
    except Exception as e:
        st.toast(f"Failed to fetch data for {part_number}: {e}")
    return {}


if uploaded_file is not None:
    if not api_key:
        st.warning("⚠️ Please enter your Mouser API key in the sidebar to fetch live data.")
    else:
        try:
            content = uploaded_file.read().decode("utf-8")
            footprint_blocks = content.split("(footprint ")
            components = []

            # 1. Parse the PCB File
            for block in footprint_blocks[1:]:
                ref_match = re.search(r'\(property\s+"Reference"\s+"(.*?)"', block, re.DOTALL)
                ref = ref_match.group(1) if ref_match else ""

                # Look for custom MPN fields first, fallback to standard "Value"
                mfg_match = re.search(r'\(property\s+"(?:MFG_PN|Manufacturer Part Number|Mouser Part Number|Mouser)"\s+"(.*?)"', block, re.DOTALL)
                val_match = re.search(r'\(property\s+"Value"\s+"(.*?)"', block, re.DOTALL)
                
                part_num = ""
                if mfg_match and mfg_match.group(1).strip() not in ["", "~"]:
                    part_num = mfg_match.group(1).strip()
                elif val_match:
                    part_num = val_match.group(1).strip()

                if ref and part_num:
                    components.append({"Reference": ref, "Part Number": part_num})

            raw_df = pd.DataFrame(components)

            if raw_df.empty:
                st.error("No valid component references or part numbers found in this PCB file.")
            else:
                st.success(f"PCB Parsed: Found {len(raw_df)} total components. Grouping duplicates...")

                # 2. Group by Part Number
                grouped = raw_df.groupby("Part Number").size().reset_index(name="Order Quantity")
                
                # 3. Template Columns setup
                template_columns = [
                    "Mfr Part Number (Input)", "Manufacturer Part Number", "Mouser Part Number", 
                    "Manufacturer Name", "Description", "Quantity 1", "Unit Price 1", 
                    "Quantity 2", "Unit Price 2", "Quantity 3", "Unit Price 3", 
                    "Quantity 4", "Unit Price 4", "Quantity 5", "Unit Price 5", 
                    "Order Quantity", "Order Unit Price", "Min./Mult.", "Availability", 
                    "Lead Time in Days", "Lifecycle", "NCNR", "RoHS", "Pb Free", 
                    "Package Type", "Datasheet URL", "Product Image", "Design Risk"
                ]
                bom_data = []

                # Progress bar for API fetching
                progress_text = "Fetching live component data from Mouser..."
                bar = st.progress(0, text=progress_text)
                total_parts = len(grouped)

                # 4. Fetch Live Mouser Data for each unique Part
                for idx, row in grouped.iterrows():
                    part_input = row["Part Number"]
                    order_qty = row["Order Quantity"]
                    
                    # Fetch from Mouser
                    api_data = fetch_mouser_data(part_input, api_key)
                    
                    # Map the returned JSON to the exact column names
                    row_data = {col: "" for col in template_columns}
                    row_data["Mfr Part Number (Input)"] = part_input
                    row_data["Order Quantity"] = order_qty

                    if api_data:
                        row_data["Manufacturer Part Number"] = api_data.get("ManufacturerPartNumber", part_input)
                        row_data["Mouser Part Number"] = api_data.get("MouserPartNumber", "")
                        row_data["Manufacturer Name"] = api_data.get("Manufacturer", "")
                        row_data["Description"] = api_data.get("Description", "")
                        row_data["Availability"] = api_data.get("Availability", "")
                        row_data["Lead Time in Days"] = api_data.get("LeadTime", "")
                        row_data["Lifecycle"] = api_data.get("LifecycleStatus", "")
                        row_data["RoHS"] = api_data.get("ROHSStatus", "")
                        row_data["Datasheet URL"] = api_data.get("DataSheetUrl", "")
                        row_data["Product Image"] = api_data.get("ImagePath", "")
                        
                        min_ord = api_data.get("Min", "")
                        mult = api_data.get("Mult", "")
                        row_data["Min./Mult."] = f"{min_ord} / {mult}".strip(" /")

                        # Extract up to 5 price breaks
                        breaks = api_data.get("PriceBreaks", [])
                        if isinstance(breaks, list):
                            for i, p_break in enumerate(breaks[:5]):
                                row_data[f"Quantity {i+1}"] = p_break.get("Quantity", "")
                                row_data[f"Unit Price {i+1}"] = p_break.get("Price", "")
                    
                    bom_data.append(row_data)
                    
                    # Respect Mouser rate limiting (30 requests/minute)
                    time.sleep(1) 
                    bar.progress((idx + 1) / total_parts, text=f"Fetched {idx + 1} of {total_parts} parts...")

                # 5. Render Final Template
                final_bom_df = pd.DataFrame(bom_data)
                
                st.write("---")
                st.write("### Live Populated BOM Result")
                st.dataframe(final_bom_df)

                # Format to Excel
                @st.cache_data
                def to_excel(df):
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine="openpyxl") as writer:
                        df.to_excel(writer, index=False, sheet_name="Sheet1")
                    return output.getvalue()

                st.download_button(
                    label="📥 Download Filled Excel BOM Template",
                    data=to_excel(final_bom_df),
                    file_name="Mouser_BOM_Filled.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

        except Exception as e:
            st.error(f"Error executing app: {e}")
