import re
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="KiCad PCB to Mouser BOM", page_icon="⚡", layout="centered"
)

st.title("⚡ KiCad PCB Layout to Mouser BOM")
st.markdown(
    "Upload your native KiCad PCB file (`.kicad_pcb`) to automatically extract component references, aggregate quantities by value or footprint, and export a clean CSV for Mouser."
)

uploaded_file = st.file_uploader("Choose a KiCad PCB file", type=["kicad_pcb"])

if uploaded_file is not None:
  try:
    content = uploaded_file.read().decode("utf-8")

    # Parse footprints and their properties from the S-expression .kicad_pcb text
    footprints = re.findall(r"\(footprint\s+(.*?)\n\t\)", content, re.DOTALL)

    components = []

    # Fallback pattern if single-line or multi-line formatting varies
    # Let's search for blocks starting with (footprint ... and parse properties
    # Alternatively, find all footprint blocks more flexibly:
    fp_blocks = content.split("(footprint ")

    for block in fp_blocks[1:]:
      # Extract footprint name (first quoted string)
      fp_match = re.search(r'^"(.*?)"', block)
      fp_name = fp_match.group(1) if fp_match else "Unknown"

      # Extract Reference
      ref_match = re.search(
          r'\(property\s+"Reference"\s+"(.*?)"', block, re.DOTALL
      )
      ref = ref_match.group(1) if ref_match else ""

      # Extract Value
      val_match = re.search(r'\(property\s+"Value"\s+"(.*?)"', block, re.DOTALL)
      val = val_match.group(1) if val_match else ""

      if ref:  # Only add if a component reference exists (e.g., C1, U3, J2)
        components.append({"Reference": ref, "Value": val, "Footprint": fp_name})

    raw_df = pd.DataFrame(components)

    if not raw_df.empty:
      st.success(
          f"Successfully parsed PCB layout! Found {len(raw_df)} components."
      )
      st.write("### Extracted Components Preview:")
      st.dataframe(raw_df.head())

      st.write("---")
      st.write("### Grouping and Mapping")
      st.write(
          "Components are automatically grouped by their schematic **Value** or"
          " type to calculate quantities."
      )

      # Group by Value to calculate quantities
      grouped = (
          raw_df.groupby("Value")
          .size()
          .reset_index(name="Quantity")
          .rename(columns={"Value": "Manufacturer Part Number"})
      )

      # Mouser format: Quantity first, then Part Number
      mouser_df = grouped[["Quantity", "Manufacturer Part Number"]]

      if st.button("Generate Mouser BOM"):
        st.write("---")
        st.write("### Formatted BOM Preview for Mouser:")
        st.dataframe(mouser_df)

        csv_data = mouser_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="📥 Download Formatted CSV for Mouser",
            data=csv_data,
            file_name="mouser_bom_from_pcb.csv",
            mime="text/csv",
        )
    else:
      st.warning(
          "No component references found in this file. Ensure it is a valid"
          " KiCad PCB layout file."
      )

  except Exception as e:
    st.error(f"Error processing KiCad PCB file: {e}")
