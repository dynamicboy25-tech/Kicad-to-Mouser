import re
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="KiCad PCB to Mouser BOM Exporter", page_icon="⚡", layout="centered"
)

st.title("⚡ KiCad PCB Layout to Mouser BOM")
st.markdown(
    "Upload your native KiCad PCB file (`.kicad_pcb`) to automatically extract"
    " components, aggregate quantities, and generate an import-ready CSV for"
    " Mouser's Rapid BOM tool."
)

uploaded_file = st.file_uploader("Choose a KiCad PCB file", type=["kicad_pcb"])

if uploaded_file is not None:
  try:
    content = uploaded_file.read().decode("utf-8")

    # Split content by footprint blocks
    footprint_blocks = content.split("(footprint ")
    components = []

    for block in footprint_blocks[1:]:
      # Extract Reference (e.g., C60, U3, J2)
      ref_match = re.search(
          r'\(property\s+"Reference"\s+"(.*?)"', block, re.DOTALL
      )
      ref = ref_match.group(1) if ref_match else ""

      # Extract Value (e.g., C_Small, part number, etc.)
      val_match = re.search(r'\(property\s+"Value"\s+"(.*?)"', block, re.DOTALL)
      val = val_match.group(1) if val_match else ""

      # Check for any custom manufacturer part number properties if present
      mfg_match = re.search(
          r'\(property\s+"(?:MFG_PN|Manufacturer Part Number|Mouser)"\s+"(.*?)"',
          block,
          re.DOTALL,
      )
      part_num = mfg_match.group(1) if mfg_match else val

      if ref:
        components.append({
            "Reference": ref,
            "Part Number": part_num,
            "Value": val,
        })

    raw_df = pd.DataFrame(components)

    if not raw_df.empty:
      st.success(
          f"Successfully parsed PCB layout! Found {len(raw_df)} total"
          " components."
      )

      st.write("### Extracted Components Preview:")
      st.dataframe(raw_df.head(10))

      st.write("---")
      st.write("### BOM Aggregation")
      st.write(
          "Identical part numbers/values are automatically grouped and"
          " quantities are summed."
      )

      # Group by Part Number to calculate quantities
      grouped = (
          raw_df.groupby("Part Number")
          .size()
          .reset_index(name="Quantity")
          .rename(columns={"Part Number": "Manufacturer Part Number"})
      )

      # Mouser import format: Quantity first, then Manufacturer Part Number
      mouser_df = grouped[["Quantity", "Manufacturer Part Number"]]

      st.write("### Formatted BOM Preview for Mouser:")
      st.dataframe(mouser_df)

      csv_data = mouser_df.to_csv(index=False).encode("utf-8")

      st.download_button(
          label="📥 Download Formatted CSV for Mouser",
          data=csv_data,
          file_name="mouser_bom_import.csv",
          mime="text/csv",
      )
    else:
      st.warning(
          "No component references found in this file. Please verify it is a"
          " valid KiCad PCB file."
      )

  except Exception as e:
    st.error(f"Error processing KiCad PCB file: {e}")
